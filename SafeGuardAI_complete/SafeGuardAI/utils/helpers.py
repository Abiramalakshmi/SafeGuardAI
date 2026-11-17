"""
utils_ui/helpers.py
Pure UI helpers — no Streamlit page logic, no backend calls.
Import wherever you need badges, chips, progress bars, etc.
"""
import os
import subprocess
import streamlit as st
from pathlib import Path


# ── Color resolution ────────────────────────────────────────
def score_color(s: float) -> str:
    """Return hex color for a 0-1 risk score."""
    if s >= 0.65: return "#ea4335"
    if s >= 0.50: return "#e37400"
    return "#34a853"

def score_variant(s: float) -> str:
    """Return CSS variant name for a score."""
    if s >= 0.65: return "red"
    if s >= 0.50: return "amber"
    return "green"

def level_to_variant(level: str) -> str:
    return {"UNSAFE": "red", "REVIEW": "amber", "SAFE": "green"}.get(level, "blue")


# ── Section header ───────────────────────────────────────────
def section(text: str, color: str = "#1a73e8"):
    st.markdown(
        f"<div class='sg-sec'>"
        f"<span style='color:{color};font-size:14px'>●</span>"
        f"<span>{text}</span>"
        f"<span class='sg-sec-line'></span></div>",
        unsafe_allow_html=True,
    )


# ── Stat chip ────────────────────────────────────────────────
def stat_chip(label: str, value, sub: str = "", variant: str = "blue"):
    st.markdown(f"""
    <div class='sg-chip chip-{variant}'>
      <div class='sg-chip-label'>{label}</div>
      <div class='sg-chip-value'>{value}</div>
      <div class='sg-chip-sub'>{sub}</div>
    </div>""", unsafe_allow_html=True)


# ── Badge HTML (returns string, does NOT call st.markdown) ──
def badge_html(level: str) -> str:
    cls   = {"UNSAFE":"sg-badge-red","REVIEW":"sg-badge-amber","SAFE":"sg-badge-green"}.get(level, "sg-badge-blue")
    icons = {"UNSAFE":"⛔","REVIEW":"⚠️","SAFE":"✅"}
    return f"<span class='sg-badge {cls}'>{icons.get(level,'●')} {level}</span>"


# ── Linear progress bar ──────────────────────────────────────
def progress_bar(value: float, color: str):
    pct = min(max(value * 100, 0), 100)
    st.markdown(f"""
    <div class='sg-prog-wrap'>
      <div class='sg-prog-track'>
        <div class='sg-prog-fill' style='width:{pct:.1f}%;background:{color}'></div>
      </div>
    </div>""", unsafe_allow_html=True)


# ── Video player ─────────────────────────────────────────────
def video_player(path: str, label: str = ""):
    """Render a persistent video from disk using st.video()."""
    if path and os.path.exists(path):
        kb = os.path.getsize(path) // 1024
        if label:
            st.markdown(
                f"<div style='font-size:12px;color:var(--on-surm);margin-bottom:6px'>"
                f"📁 {label}  ·  {kb} KB</div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div class='sg-video-wrap'>", unsafe_allow_html=True)
        st.video(path)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='sg-await' style='padding:24px'>
          <div style='font-size:24px;margin-bottom:8px'>📹</div>
          <div style='font-size:13px;color:var(--on-surm)'>Video not available on disk.</div>
        </div>""", unsafe_allow_html=True)


# ── Result banner ────────────────────────────────────────────
def result_banner(level: str):
    cfg = {
        "UNSAFE": ("sg-banner-unsafe", "⛔", "THREAT DETECTED"),
        "REVIEW": ("sg-banner-review", "⚠️", "FLAGGED FOR REVIEW"),
        "SAFE":   ("sg-banner-safe",   "✅", "CONTENT SAFE"),
    }
    cls, icon, text = cfg.get(level, ("sg-banner-safe", "✅", level))
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"""
    <div class='sg-banner {cls}'>
      <span style='font-size:26px'>{icon}</span>
      <div>
        <div>{text}</div>
        <div style='font-size:12px;font-weight:400;opacity:.75;margin-top:2px'>
          Analysis complete · {ts}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


# ── Audio extraction ─────────────────────────────────────────
def extract_audio(video_path: str) -> str | None:
    """
    Extract 16-kHz mono WAV from a video file.
    Tries moviepy first, then ffmpeg subprocess.
    Returns WAV path or None if both fail.
    """
    wav_path = str(Path(video_path).with_suffix(".wav"))
    # 1. moviepy
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(video_path)
        if clip.audio is not None:
            clip.audio.write_audiofile(wav_path, fps=16000, logger=None)
            clip.close()
            return wav_path
        clip.close()
    except Exception:
        pass
    # 2. ffmpeg
    try:
        res = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path,
             "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, timeout=60,
        )
        if res.returncode == 0 and os.path.exists(wav_path):
            return wav_path
    except Exception:
        pass
    return None


# ── Await placeholder ────────────────────────────────────────
def await_placeholder(icon: str = "🛡️", title: str = "Awaiting Analysis",
                      subtitle: str = "Upload or record media to begin"):
    st.markdown(f"""
    <div class='sg-await'>
      <div style='font-size:40px;margin-bottom:16px'>{icon}</div>
      <div style='font-size:15px;font-weight:600;color:var(--on-sur);margin-bottom:6px'>{title}</div>
      <div style='font-size:13px;color:var(--on-surm)'>{subtitle}</div>
    </div>""", unsafe_allow_html=True)
