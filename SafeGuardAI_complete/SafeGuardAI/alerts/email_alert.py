# ============================================================
# SafeGuard AI — Gmail SMTP Email Alert Module
# File: alerts/email_alert.py
#
# Setup:
#   1. Add credentials to .streamlit/secrets.toml (see template)
#   2. Enable "Email Alerts" toggle in Settings page
#   3. Alerts fire automatically when UNSAFE (or REVIEW) is detected
# ============================================================

import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── Config loader ─────────────────────────────────────────────
def _get_email_config() -> dict | None:
    """
    Load email config from st.secrets (preferred) or environment variables.
    Returns None if credentials are not configured.
    """
    try:
        import streamlit as st
        cfg = st.secrets.get("email", {})
        if cfg.get("sender_address") and cfg.get("app_password"):
            return {
                "sender":    cfg["sender_address"],
                "password":  cfg["app_password"],
                "recipient": cfg["recipient_address"],
                "smtp_host": cfg.get("smtp_host", "smtp.gmail.com"),
                "smtp_port": int(cfg.get("smtp_port", 587)),
                # Which alert levels trigger an email: "UNSAFE" only, or also "REVIEW"
                "trigger_on": cfg.get("trigger_on_levels", "UNSAFE,REVIEW").split(","),
            }
    except Exception:
        pass

    # Fallback: environment variables
    import os
    sender = os.environ.get("SG_EMAIL_SENDER", "")
    password = os.environ.get("SG_EMAIL_PASSWORD", "")
    recipient = os.environ.get("SG_EMAIL_RECIPIENT", "")
    if sender and password and recipient:
        return {
            "sender":    sender,
            "password":  password,
            "recipient": recipient,
            "smtp_host": os.environ.get("SG_SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("SG_SMTP_PORT", 587)),
            "trigger_on": os.environ.get("SG_EMAIL_TRIGGER_ON", "UNSAFE,REVIEW").split(","),
        }

    return None


# ── Email builder ─────────────────────────────────────────────
def _build_email(cfg: dict, alert_level: str, payload: dict) -> MIMEMultipart:
    """Compose a clean HTML + plain-text email for the incident."""
    violence   = payload.get("violence_score", 0.0) * 100
    toxicity   = payload.get("toxicity_score", 0.0) * 100
    aggression = payload.get("aggression_score", 0.0) * 100
    transcript = (payload.get("transcript", "") or "")[:400] or "No speech detected."
    phrases    = payload.get("toxic_phrases", [])
    if isinstance(phrases, str):
        phrases = [phrases] if phrases else []
    phrases_str = ", ".join(phrases[:6]) if phrases else "None"
    ts          = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # FIX: Use the pipeline's computed final_confidence directly so the email matches
    # the dashboard display. The old formula (average of risk scores) was a different
    # calculation that produced a different number (e.g. 77.7% vs 37% on the dashboard).
    raw_conf   = payload.get("final_confidence", 0.0)
    confidence = min(round(float(raw_conf) * 100, 1), 100.0)

    # Fallback: if final_confidence was not passed (e.g. older callers), revert to
    # the weighted average of whichever risk scores are non-zero.
    if confidence == 0.0:
        active_scores = [s for s in [violence, toxicity, aggression] if s > 0]
        confidence    = sum(active_scores) / len(active_scores) if active_scores else max(violence, toxicity, aggression)
        confidence    = min(round(confidence, 1), 100.0)

    level_color = {"UNSAFE": "#f75d5d", "REVIEW": "#f7b955"}.get(alert_level, "#4af2a1")
    level_icon  = {"UNSAFE": "🔴", "REVIEW": "🟡"}.get(alert_level, "🟢")

    subject = f"{level_icon} SafeGuard AI — {alert_level} Incident Detected [{ts}]"

    # ── Plain-text body ───────────────────────────────────────
    plain = f"""
SafeGuard AI Security Alert
============================
Level      : {alert_level}
Time       : {ts}
Confidence : {confidence:.1f}%

SCORES
------
Visual Threat     : {violence:.1f}%
Audio Toxicity    : {toxicity:.1f}%
Speech Aggression : {aggression:.1f}%

TOXIC PHRASES
-------------
{phrases_str}

TRANSCRIPT (excerpt)
--------------------
{transcript}

--
This alert was generated automatically by SafeGuard AI v3.1.
Log in to the dashboard to review and resolve this incident.
"""

    # ── HTML body ─────────────────────────────────────────────
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0b0e14; color: #eef2ff; margin: 0; padding: 0; }}
    .wrap {{ max-width: 600px; margin: 32px auto; background: #161b27; border-radius: 12px;
             border: 1px solid rgba(255,255,255,0.06); overflow: hidden; }}
    .header {{ background: {level_color}18; border-top: 3px solid {level_color};
               padding: 24px 28px 20px; }}
    .badge {{ display: inline-block; background: {level_color}22; border: 1px solid {level_color}55;
              color: {level_color}; padding: 4px 14px; border-radius: 20px; font-size: 12px;
              font-weight: 700; font-family: monospace; letter-spacing: 1px; }}
    .title {{ font-size: 20px; font-weight: 800; color: #eef2ff; margin: 10px 0 4px; }}
    .subtitle {{ font-size: 11px; color: #8892aa; font-family: monospace; }}
    .body {{ padding: 24px 28px; }}
    .row {{ display: flex; justify-content: space-between; padding: 9px 0;
             border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 13px; }}
    .row:last-child {{ border-bottom: none; }}
    .label {{ color: #8892aa; font-family: monospace; font-size: 11px; }}
    .value {{ font-family: monospace; font-weight: 600; color: #eef2ff; }}
    .section {{ margin-top: 20px; }}
    .section-title {{ font-size: 10px; letter-spacing: 1.5px; font-weight: 700;
                      color: #4a5568; text-transform: uppercase; margin-bottom: 10px; }}
    .phrase {{ display: inline-block; background: rgba(247,93,93,0.1);
               border: 1px solid rgba(247,93,93,0.25); color: #f75d5d;
               border-radius: 4px; padding: 2px 8px; font-family: monospace;
               font-size: 11px; margin: 2px 3px 2px 0; }}
    .transcript {{ background: #111520; border: 1px solid rgba(255,255,255,0.06);
                   border-radius: 8px; padding: 14px 16px; font-family: monospace;
                   font-size: 12px; color: #8892aa; line-height: 1.8; }}
    .footer {{ padding: 16px 28px; border-top: 1px solid rgba(255,255,255,0.05);
               font-size: 11px; color: #4a5568; text-align: center; }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <span class="badge">{level_icon} {alert_level}</span>
    <div class="title">Incident Detected</div>
    <div class="subtitle">SafeGuard AI v3.1 &nbsp;·&nbsp; {ts}</div>
  </div>
  <div class="body">
    <div class="row">
      <span class="label">TIME</span>
      <span class="value">{ts}</span>
    </div>
    <div class="row">
      <span class="label">CONFIDENCE</span>
      <span class="value" style="color:{'#f75d5d' if confidence >= 65 else '#f7b955' if confidence >= 45 else '#4af2a1'}">{confidence:.1f}%</span>
    </div>
    <div class="row">
      <span class="label">VISUAL THREAT</span>
      <span class="value" style="color:{'#f75d5d' if violence >= 65 else '#f7b955' if violence >= 50 else '#4af2a1'}">{violence:.1f}%</span>
    </div>
    <div class="row">
      <span class="label">AUDIO TOXICITY</span>
      <span class="value" style="color:{'#f75d5d' if toxicity >= 65 else '#f7b955' if toxicity >= 50 else '#4af2a1'}">{toxicity:.1f}%</span>
    </div>
    <div class="row">
      <span class="label">SPEECH AGGRESSION</span>
      <span class="value" style="color:{'#f75d5d' if aggression >= 75 else '#f7b955' if aggression >= 55 else '#4af2a1'}">{aggression:.1f}%</span>
    </div>

    {'<div class="section"><div class="section-title">Toxic Phrases</div><div>' +
     "".join(f'<span class="phrase">{p}</span>' for p in phrases[:6]) +
     '</div></div>' if phrases else ''}

    <div class="section">
      <div class="section-title">Speech Transcript</div>
      <div class="transcript">{transcript}</div>
    </div>
  </div>
  <div class="footer">
    This alert was generated automatically by SafeGuard AI.<br>
    Log in to the dashboard to review and resolve this incident.
  </div>
</div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"SafeGuard AI <{cfg['sender']}>"
    msg["To"]      = cfg["recipient"]
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))
    return msg


# ── Public API ────────────────────────────────────────────────
def send_alert_email(alert_level: str, payload: dict) -> bool:
    """
    Send a Gmail SMTP alert email for a detected incident.

    Args:
        alert_level: "UNSAFE" or "REVIEW"
        payload: dict with keys from _finalize() result
                 (violence_score, toxicity_score, aggression_score,
                  emotion, source, transcript, toxic_phrases, incident_id)

    Returns:
        True if email sent successfully, False otherwise.
    """
    # ── NEW: Check if email alerts are enabled in DB settings ────────────────
    try:
        from database.db_manager import get_all_settings
        db_settings = get_all_settings()
        if db_settings.get("alert_email_enabled", "true") == "false":
            logger.debug("Email alerts disabled in dashboard settings — skipping.")
            return False
        # Override trigger levels from DB setting if present
        db_min_level = db_settings.get("alert_min_level", "").strip().upper()
        if db_min_level == "UNSAFE" and alert_level.upper() == "REVIEW":
            logger.debug("Alert level REVIEW suppressed by dashboard setting (UNSAFE only).")
            return False
    except Exception as e:
        logger.debug(f"Could not read DB settings for email check: {e}")
        # Fall through — secrets.toml trigger_on still applies below

    cfg = _get_email_config()
    if cfg is None:
        logger.debug("Email alerts not configured — skipping.")
        return False

    # Only send for configured trigger levels
    trigger_on = [lvl.strip().upper() for lvl in cfg["trigger_on"]]
    if alert_level.upper() not in trigger_on:
        logger.debug(f"Alert level {alert_level} not in trigger_on={trigger_on} — skipping email.")
        return False

    try:
        msg = _build_email(cfg, alert_level, payload)
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["sender"], cfg["password"])
            server.sendmail(cfg["sender"], cfg["recipient"], msg.as_string())
        logger.info(f"Email alert sent → {cfg['recipient']} (level={alert_level})")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Email auth failed — check sender_address and app_password in secrets.toml")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending alert email: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending alert email: {e}")
    return False
