# ============================================================
# SafeGuard AI — Configuration
# ============================================================

import os

# ── Paths ────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR  = os.path.join(BASE_DIR, "uploads")
DB_PATH     = os.path.join(BASE_DIR, "database", "safeguard.db")
STATIC_DIR  = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ── Detection Thresholds ─────────────────────────────────────
VIOLENCE_THRESHOLD  = 0.65   # ResNet18 violence score
TOXICITY_THRESHOLD  = 0.60   # DistilBERT toxicity score
EMOTION_CONF_MIN    = 0.50   # Minimum emotion confidence

# ── Fusion Weights ───────────────────────────────────────────
VISUAL_WEIGHT = 0.70
AUDIO_WEIGHT  = 0.30

# ── Alert Levels ─────────────────────────────────────────────
ALERT_UNSAFE  = "UNSAFE"    # violence_score >= VIOLENCE_THRESHOLD
ALERT_REVIEW  = "REVIEW"    # 0.50 <= violence_score < VIOLENCE_THRESHOLD
ALERT_SAFE    = "SAFE"      # violence_score < 0.50

# ── Video Processing ─────────────────────────────────────────
FRAME_SAMPLE_RATE   = 5     # frames per second to sample
FRAME_SIZE          = (224, 224)
TEMPORAL_WINDOW     = 5     # frames for smoothing

# ── Audio Processing ─────────────────────────────────────────
AUDIO_SAMPLE_RATE   = 16000
AUDIO_CHUNK_SECONDS = 30    # Whisper chunk size

# ── Webcam ───────────────────────────────────────────────────
WEBCAM_INDEX        = 0
CAPTURE_DURATION    = 5     # seconds per live capture window

# ── Whisper Model ────────────────────────────────────────────
# Options: "tiny", "base", "small", "medium", "large"
WHISPER_MODEL       = "base"

# ── Emotions that indicate aggression ───────────────────────
AGGRESSIVE_EMOTIONS = {"anger", "fear"}
SAFE_EMOTIONS       = {"happiness", "happy", "excited", "excitement"}

# ── Violence classes (for ResNet18 output mapping) ───────────
VIOLENCE_CLASSES = ["non_violence", "violence"]

# ── Alert Sound ──────────────────────────────────────────────
ALERT_SOUND_ENABLED = True
