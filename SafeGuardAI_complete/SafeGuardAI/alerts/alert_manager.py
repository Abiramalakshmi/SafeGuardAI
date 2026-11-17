# ============================================================
# SafeGuard AI — Alert Manager
# ============================================================

import os
import time
import threading
from datetime import datetime
from utils.config import ALERT_UNSAFE, ALERT_REVIEW, ALERT_SAFE, VIOLENCE_THRESHOLD


def determine_alert_level(violence_score: float,
                           toxicity_score: float = 0.0,
                           emotion: str = "neutral",
                           aggression_score: float = 0.0,
                           audio_aggression_score: float = 0.0,  # Ra = 0.5*p_tox + 0.5*p_emo
                           fused_score: float = 0.0) -> str:      # Rf = wv*Rv + wa*Ra
    """
    Determine alert level from multimodal scores.

    Metric 8 — Risk Thresholds applied to Rf:
      Rf >= 0.70  → UNSAFE
      Rf >= 0.40  → REVIEW
      Rf <  0.40  → SAFE

    Additional single-modality overrides (Metric 9 — θ_single):
      violence_score >= VIOLENCE_THRESHOLD        → always UNSAFE
      toxicity >= threshold AND emotion aggressive → UNSAFE
      aggression >= 0.75 AND corroborated         → UNSAFE (needs backup signal)
    """
    from utils.config import TOXICITY_THRESHOLD, AGGRESSIVE_EMOTIONS, SAFE_EMOTIONS

    emotion_lower = (emotion or "neutral").lower()
    is_aggressive = emotion_lower in AGGRESSIVE_EMOTIONS
    is_safe_emo   = emotion_lower in SAFE_EMOTIONS

    AGGRESSION_UNSAFE = 0.75

    # ── Step 1: Fused Risk Score primary threshold (Metric 8) ────────────────
    # This is the main classification path — Rf drives the decision.
    if fused_score >= 0.70:
        return ALERT_UNSAFE
    if fused_score >= 0.40:
        # Don't return REVIEW yet — check if single-modality overrides push to UNSAFE
        pass

    # ── Step 2: Single-modality UNSAFE overrides (Metric 9 — θ_single) ──────
    # Violence score alone is always the strongest signal
    if violence_score >= VIOLENCE_THRESHOLD:
        return ALERT_UNSAFE

    # High toxicity + aggressive emotion → UNSAFE
    if toxicity_score >= TOXICITY_THRESHOLD and is_aggressive:
        return ALERT_UNSAFE

    # Wav2Vec2 aggression → UNSAFE only with corroboration
    # (crowd cheering scores high on aggression but has zero toxicity/visual)
    if aggression_score >= AGGRESSION_UNSAFE:
        has_corroboration = (toxicity_score >= 0.30 or violence_score >= 0.30)
        if has_corroboration:
            return ALERT_UNSAFE

    # ── Step 3: Apply fused REVIEW band ──────────────────────────────────────
    if fused_score >= 0.40:
        # Safe emotion with low toxicity can suppress REVIEW
        if is_safe_emo and toxicity_score < 0.4 and violence_score < 0.4:
            return ALERT_SAFE
        return ALERT_REVIEW

    # ── Step 4: Individual signal REVIEW fallback ─────────────────────────────
    if violence_score >= 0.50 or toxicity_score >= TOXICITY_THRESHOLD:
        return ALERT_REVIEW

    if audio_aggression_score >= 0.40:   # Ra >= 0.40 with no visual
        return ALERT_REVIEW

    return ALERT_SAFE


def compute_fused_score(visual_score: float,
                         audio_score: float,
                         visual_weight: float = 0.50,
                         audio_weight: float  = 0.50) -> float:
    """
    Metric 7 — Multimodal Fusion: Rf = (Wv × Rv) + (Wa × Ra)
    Default weights: Wv = 0.5, Wa = 0.5 (equal contribution)
    audio_score here should be Ra (= 0.5*p_tox + 0.5*p_emo), NOT raw toxicity.
    """
    fused = (visual_weight * visual_score) + (audio_weight * audio_score)
    return round(float(fused), 4)


class AlertManager:
    """
    Manages alert history, deduplication, and sound playback.
    """

    def __init__(self, sound_enabled: bool = True):
        self._history       = []
        self._last_alert_ts = 0.0
        self._cooldown      = 10.0
        self.sound_enabled  = sound_enabled

    def trigger(self, violence_score: float, emotion: str,
                toxicity_score: float, toxic_phrases: list,
                source: str, transcript: str = "",
                aggression_score: float = 0.0,
                audio_aggression_score: float = 0.0,
                fused_score: float = 0.0,
                final_confidence: float = 0.0) -> dict | None:  # FIX: accept pipeline-computed confidence
        """
        Evaluate scores and trigger an alert if warranted.
        Returns the alert dict or None if suppressed.
        """
        alert_level = determine_alert_level(
            violence_score,
            toxicity_score,
            emotion,
            aggression_score=aggression_score,
            audio_aggression_score=audio_aggression_score,
            fused_score=fused_score,
        )

        if alert_level == ALERT_SAFE:
            return None

        now = time.time()
        if now - self._last_alert_ts < self._cooldown:
            return None

        self._last_alert_ts = now

        alert = {
            "timestamp":        datetime.now().isoformat(),
            "alert_level":      alert_level,
            "violence_score":   round(violence_score, 4),
            "toxicity_score":   round(toxicity_score, 4),
            "aggression_score": round(aggression_score, 4),
            "emotion":          emotion,
            "toxic_phrases":    toxic_phrases or [],
            "source":           source,
            "transcript":       transcript,
            "final_confidence": round(final_confidence, 4),  # FIX: carry through so email_alert uses the same value as the dashboard
            "message":          self._format_message(
                                    alert_level, violence_score,
                                    emotion, toxic_phrases, aggression_score
                                ),
        }

        self._history.append(alert)

        if self.sound_enabled:
            threading.Thread(target=self._play_sound, daemon=True).start()

        # ── NEW: Fire email alert in background thread ────────────────────────
        threading.Thread(
            target=self._send_email_alert,
            args=(alert_level, alert),
            daemon=True,
        ).start()

        return alert

    def _send_email_alert(self, alert_level: str, alert: dict):
        """Send email alert in a background thread so it never blocks analysis."""
        try:
            from alerts.email_alert import send_alert_email
            send_alert_email(alert_level, alert)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Email alert failed: {e}")

    def _format_message(self, level: str, v_score: float,
                         emotion: str, phrases: list,
                         aggression_score: float = 0.0) -> str:
        emoji = "🚨" if level == ALERT_UNSAFE else "⚠️"
        msg   = f"{emoji} {level} INCIDENT DETECTED\n"
        msg  += f"Violence Score: {v_score*100:.1f}% | Emotion: {emotion.upper()}"
        if aggression_score > 0.0:
            msg += f" | Aggression: {aggression_score*100:.1f}%"
        msg  += "\n"
        if phrases:
            msg += f"Toxic Phrases: {', '.join(phrases[:3])}"
        return msg

    def _play_sound(self):
        try:
            import playsound
            beep_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "static", "alert.wav"
            )
            if os.path.isfile(beep_path):
                playsound.playsound(beep_path, block=False)
                return
        except ImportError:
            pass

        try:
            import subprocess
            subprocess.run(["paplay", "/usr/share/sounds/alsa/Front_Left.wav"],
                           capture_output=True, timeout=2)
        except Exception:
            pass

        try:
            print("\a", end="", flush=True)
        except Exception:
            pass

    def get_history(self, n: int = 50) -> list:
        return self._history[-n:]

    def clear_history(self):
        self._history.clear()

    def set_cooldown(self, seconds: float):
        self._cooldown = max(0.0, seconds)


# Singleton
_alert_manager = None

def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
