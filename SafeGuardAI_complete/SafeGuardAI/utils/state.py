"""
utils_ui/state.py
Central session-state initialisation. Import and call init_state() once at app startup.
"""
import streamlit as st
from pathlib import Path
import os

BASE_DIR       = Path(os.path.dirname(os.path.abspath(__file__))).parent
UPLOADS_DIR    = BASE_DIR / "SafeGuardAI" / "uploads"
RECORDINGS_DIR = BASE_DIR / "SafeGuardAI" / "recordings"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULTS = {
    # Auth
    "authenticated":      False,
    "current_user":       None,
    # Navigation
    "page":               "dashboard",
    # Analysis results
    "last_result":        None,
    "last_video_path":    None,
    "last_video_source":  "",
    "last_audio_path":    None,
    # Recording
    "rec_duration":       10,
    # Tracking
    "last_analysis_time": None,
    "analysis_count":     0,
}

def init_state():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
