# 🛡️ SafeGuard AI — Multimodal Workplace Safety Monitoring System

A complete AI-powered system that detects violent incidents in workplaces by
analyzing **video behavior** and **speech/audio cues** in real time.

---

## 🚀 Quick Start

### 1. Install Python 3.9+
Download from https://www.python.org/downloads/

### 2. Create a Virtual Environment (recommended)
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note on ffmpeg** (required for audio extraction):
> - **Windows**: Download from https://ffmpeg.org/download.html and add to PATH
> - **Mac**: `brew install ffmpeg`
> - **Linux**: `sudo apt install ffmpeg`

### 4. Run the App
```bash
streamlit run app.py
```

Open your browser at: **http://localhost:8501**

---

## 🔌 Optional: Run the API (FastAPI)

If you want a backend API (for a separate frontend), you can run:

```bash
python api.py
```

API will be available at **http://localhost:8000** (OpenAPI docs at `/docs`).

### 5. Login
- **Username**: `admin`
- **Password**: `admin123`

---

## 📁 Project Structure

```
SafeGuardAI/
├── app.py                        ← Streamlit UI (main entry point)
├── pipeline.py                   ← Main AI processing pipeline
├── requirements.txt
├── README.md
│
├── models/
│   ├── visual_model.py           ← ResNet18 violence detection
│   ├── audio_model.py            ← Whisper ASR + DistilBERT toxicity
│   └── emotion_model.py          ← CNN acoustic emotion recognition
│
├── preprocessing/
│   ├── video_processing.py       ← OpenCV frame extraction
│   └── audio_processing.py       ← ffmpeg audio extraction + mel spectrogram
│
├── alerts/
│   └── alert_manager.py          ← Alert logic, fusion, sound
│
├── database/
│   ├── db_manager.py             ← SQLite CRUD operations
│   └── safeguard.db              ← Created automatically on first run
│
├── utils/
│   └── config.py                 ← All thresholds and settings
│
└── uploads/                      ← Temp storage for uploaded files
```

---

## 🤖 AI Models Used

| Model | Purpose | Notes |
|-------|---------|-------|
| **ResNet18** (PyTorch) | Visual violence detection | Runs in demo mode without weights |
| **OpenAI Whisper** | Speech-to-text transcription | Downloads automatically on first use |
| **DistilBERT** (HuggingFace) | Toxic language detection | Downloads automatically on first use |
| **Custom CNN** | Acoustic emotion recognition | Runs in demo mode without weights |

---

## ⚙️ Demo Mode vs Production Mode

The system runs in **Demo Mode** by default — all AI models work and
produce realistic scores without needing pre-trained violence weights.

To use real trained weights:
1. Set the environment variable before running:
   ```bash
   export SAFEGUARD_VISUAL_WEIGHTS=/path/to/violence_resnet18.pth
   export SAFEGUARD_EMOTION_WEIGHTS=/path/to/emotion_cnn.pth
   ```

---

## 🖥️ Features

### 📊 Dashboard
- Real-time KPI metrics (threats, reviews, resolved)
- Violence trend chart
- Camera feed grid
- Emotion distribution

### 📹 Live Monitor
- Webcam + microphone capture
- Configurable capture duration (3–30 seconds)
- Live risk scores
- Speech transcript display
- Flagged incident history

### 📁 Video Analysis
- Upload MP4, AVI, MOV, MKV, WAV, MP3
- Full pipeline with animated progress bars
- Violence probability, emotion, toxicity scores
- Transcript + toxic phrase extraction

### 🚨 Alert Center
- Filterable incident list (ALL / UNSAFE / REVIEW / SAFE)
- One-click resolve incidents
- Clear all (admin only)

### 📋 Incident Log
- Complete history table
- Sortable by all fields

### ⚙️ Settings
- Violence & toxicity thresholds
- Fusion weights (visual vs audio)
- Alert sound toggle
- Whisper model size selection

---

## 🔒 Authentication

Default admin account:
- Username: `admin`
- Password: `admin123`

Passwords are stored as SHA-256 hashes in SQLite.

---

## 🧠 Detection Logic

```
final_score = (0.70 × visual_score) + (0.30 × audio_score)

UNSAFE  → violence >= 0.65
        OR (toxicity >= 0.60 AND emotion == anger/fear)

REVIEW  → 0.50 <= violence < 0.65
        OR toxicity >= 0.60

SAFE    → everything else
        (emotion == happy/excited AND toxicity low → always SAFE)
```

---

## 📦 Minimum System Requirements

- Python 3.9+
- 4GB RAM (8GB recommended for Whisper medium/large)
- Webcam (for live monitoring)
- Microphone (for audio analysis)
- ffmpeg installed on system PATH

---

## 🛠️ Troubleshooting

**Webcam not working?**
→ Check camera permissions in your OS settings
→ Try changing `WEBCAM_INDEX = 1` in `utils/config.py`

**Whisper takes too long?**
→ Switch to `WHISPER_MODEL = "tiny"` in settings

**Audio extraction fails?**
→ Make sure ffmpeg is installed and in your PATH

**DistilBERT download fails?**
→ Check internet connection on first run (model downloads ~260MB)

---

## 🧰 Dataset utility (optional)

`preprocessing/extract_frames.py` is a helper to extract training frames from the
Real Life Violence Dataset directory structure (expects `Violence/` and `NonViolence/`).

Example:

```bash
python -m preprocessing.extract_frames --dataset "D:\datasets\Real Life Violence Dataset"
```
