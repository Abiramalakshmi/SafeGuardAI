# ============================================================
# SafeGuard AI — Emotion Detection Model
# ============================================================
# PROBLEM: No emotion weights file exists → always DEMO mode
# DEMO mode (random dirichlet) is unreliable for production.
#
# FIX: When no weights exist, use transcript-based heuristic
# as PRIMARY method (not fallback). It's deterministic and
# correlates properly with the audio toxicity analysis.
# Random demo is now only used as absolute last resort.
# ============================================================

import os
import re
import numpy as np
from utils.config import AGGRESSIVE_EMOTIONS, SAFE_EMOTIONS

EMOTION_LABELS = ["anger", "fear", "happiness", "excitement", "sadness", "neutral"]

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    _torch_version = tuple(int(x) for x in torch.__version__.split(".")[:2])
    TORCH_AVAILABLE = True
    TORCH_SUFFICIENT = _torch_version >= (2, 4)
except ImportError:
    TORCH_AVAILABLE = False
    TORCH_SUFFICIENT = False


class EmotionCNN(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self):
        if not TORCH_AVAILABLE:
            return
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1), nn.ReLU(), nn.BatchNorm2d(32),
            nn.Conv2d(32, 32, kernel_size=3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2, 2), nn.Dropout2d(0.25),
            nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.ReLU(), nn.BatchNorm2d(64),
            nn.Conv2d(64, 64, kernel_size=3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2, 2), nn.Dropout2d(0.25),
            nn.Conv2d(64, 128, kernel_size=3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(256, len(EMOTION_LABELS))
        )

    def forward(self, x):
        return self.classifier(self.features(x))


class EmotionModel:
    def __init__(self, weights_path: str = None):
        self.model     = None
        self.device    = None
        self.demo_mode = True

        if not TORCH_AVAILABLE:
            print("[EmotionModel] PyTorch not available — using transcript heuristic.")
            return

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = EmotionCNN().to(self.device)
        self.model.eval()

        wp = weights_path or os.environ.get("SAFEGUARD_EMOTION_WEIGHTS", "")
        if wp and os.path.isfile(wp):
            try:
                self.model.load_state_dict(torch.load(wp, map_location=self.device))
                self.demo_mode = False
                print(f"[EmotionModel] Loaded weights: {wp}")
            except Exception as e:
                print(f"[EmotionModel] Weight load failed: {e} — using transcript heuristic.")
        else:
            print("[EmotionModel] No weights — using transcript heuristic (more reliable than random demo).")

    def predict_from_mel(self, mel_spec: np.ndarray) -> dict:
        """Use CNN if weights loaded, else fall through to heuristic."""
        if not TORCH_AVAILABLE or self.model is None or self.demo_mode:
            return None  # Signal to caller to use heuristic instead

        mel_min = float(np.min(mel_spec)) if mel_spec.size else 0.0
        mel_max = float(np.max(mel_spec)) if mel_spec.size else 1.0
        if mel_max > mel_min:
            mel_spec = (mel_spec - mel_min) / (mel_max - mel_min + 1e-8)

        target_w = 128
        if mel_spec.shape[1] < target_w:
            mel_spec = np.pad(mel_spec, ((0, 0), (0, target_w - mel_spec.shape[1])))
        else:
            mel_spec = mel_spec[:, :target_w]

        tensor = torch.FloatTensor(mel_spec).unsqueeze(0).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            temperature = 2.0
            probs  = torch.softmax(logits / temperature, dim=1).cpu().numpy()[0]

        idx   = int(np.argmax(probs))
        label = EMOTION_LABELS[idx]
        return {
            "emotion":       label,
            "confidence":    round(float(probs[idx]), 4),
            "probabilities": {e: round(float(p), 4) for e, p in zip(EMOTION_LABELS, probs)},
            "is_aggressive": label in AGGRESSIVE_EMOTIONS,
            "is_safe":       label in SAFE_EMOTIONS,
        }

    def predict_from_wav(self, wav_path: str) -> dict:
        """
        Try mel-based CNN first. If demo mode or no weights,
        use acoustic energy heuristic (anger = loud + high energy).
        """
        from preprocessing.audio_processing import load_wav, compute_mel_spectrogram
        try:
            used_librosa_path = False

            if LIBROSA_AVAILABLE and TORCH_AVAILABLE and self.model is not None and not self.demo_mode:
                y, sr = librosa.load(wav_path, sr=22050, mono=True)

                # FIX BUG 4: Use a sample-rate-aware silence threshold.
                # RMS values differ between 22050 Hz and 16k audio for the same clip.
                # Scale the threshold proportionally so both paths use an equivalent gate.
                # At 22050 Hz, energy is slightly higher due to more samples per second,
                # so we raise the threshold slightly compared to the 16k path (0.005).
                rms = float(np.sqrt(np.mean(y ** 2))) if y is not None and len(y) else 0.0
                silence_threshold_22k = 0.006   # adjusted for 22050 Hz (was same 0.005 as 16k — incorrect)
                if rms < silence_threshold_22k:
                    return {
                        "emotion": "neutral",
                        "confidence": 0.0,
                        "probabilities": {e: round(1.0 / len(EMOTION_LABELS), 4) for e in EMOTION_LABELS},
                        "is_aggressive": False,
                        "is_safe": False,
                        "silence": True,
                    }
                mel = librosa.feature.melspectrogram(
                    y=y, sr=sr, n_fft=1024, hop_length=512, n_mels=64, fmax=8000
                )
                mel_db = librosa.power_to_db(mel, ref=np.max)
                if mel_db.shape[1] < 128:
                    mel_db = np.pad(mel_db, ((0, 0), (0, 128 - mel_db.shape[1])),
                                    mode="constant", constant_values=-80)
                else:
                    mel_db = mel_db[:, :128]
                mel_spec = mel_db.astype(np.float32)
                used_librosa_path = True
                # Keep `y` as `audio` for heuristic fallback below — avoids double load.
                audio = y

            else:
                audio    = load_wav(wav_path)
                # FIX BUG 4: 16k path keeps its original threshold (0.005 is correct here).
                rms = float(np.sqrt(np.mean(audio ** 2))) if audio is not None and len(audio) else 0.0
                if rms < 0.005:
                    return {
                        "emotion": "neutral",
                        "confidence": 0.0,
                        "probabilities": {e: round(1.0 / len(EMOTION_LABELS), 4) for e in EMOTION_LABELS},
                        "is_aggressive": False,
                        "is_safe": False,
                        "silence": True,
                    }
                mel_spec = compute_mel_spectrogram(audio)

            # Try real model first
            result = self.predict_from_mel(mel_spec)
            if result is not None:
                return result

            # FIX BUG 3: REMOVED `audio = locals().get("audio", load_wav(wav_path))`.
            # That line caused load_wav() to be called a second time whenever the
            # librosa path was taken (because `audio` wasn't in locals() there).
            # Now `audio` is always set explicitly in both branches above, so it is
            # always available here without a redundant disk read.

            # Acoustic energy heuristic — much better than random demo.
            # Loud + high-frequency energy correlates with anger/agitation.
            energy     = float(np.sqrt(np.mean(audio ** 2)))
            zcr        = float(np.mean(np.abs(np.diff(np.sign(audio)))) / 2)
            mel_energy = float(np.mean(mel_spec[32:, :]))

            anger_score = min(1.0, energy * 8.0 + mel_energy * 2.0)
            fear_score  = min(1.0, zcr * 3.0)
            happy_score = min(1.0, max(0, 0.3 - energy * 2.0) + mel_energy * 0.5)
            neutral_score = max(0.1, 1.0 - anger_score - fear_score)

            raw = {
                "anger":      anger_score * 0.4,
                "fear":       fear_score  * 0.2,
                "happiness":  happy_score * 0.2,
                "excitement": mel_energy  * 0.1,
                "sadness":    max(0, 0.2 - energy * 2.0),
                "neutral":    neutral_score * 0.5,
            }
            total = sum(raw.values()) or 1.0
            probs_dict = {k: round(v / total, 4) for k, v in raw.items()}
            label = max(probs_dict, key=probs_dict.get)

            return {
                "emotion":       label,
                "confidence":    probs_dict[label],
                "probabilities": probs_dict,
                "is_aggressive": label in AGGRESSIVE_EMOTIONS,
                "is_safe":       label in SAFE_EMOTIONS,
            }
        except Exception as e:
            print(f"[EmotionModel] predict_from_wav error: {e}")
            return self.predict_from_transcript("", 0.0)

    def predict_from_transcript(self, transcript: str, toxicity_score: float = 0.0) -> dict:
        """
        Deterministic heuristic from transcript text + toxicity score.
        Used as primary method when no model weights exist.
        This is MORE reliable than random demo — it correlates with
        actual detected toxicity from the audio pipeline.
        """
        text = (transcript or "").lower()

        _words = text.split()
        if len(_words) >= 3:
            _unique_ratio = len(set(_words)) / len(_words)
            if _unique_ratio < 0.30:
                return {
                    "emotion":       "neutral",
                    "confidence":    0.0,
                    "probabilities": {e: round(1.0 / len(EMOTION_LABELS), 4) for e in EMOTION_LABELS},
                    "is_aggressive": False,
                    "is_safe":       False,
                }

        anger_words   = {"hit", "kill", "hurt", "fight", "dead", "attack",
                         "punch", "destroy", "hate", "murder", "stab", "shoot"}
        fear_words    = {"help", "scared", "afraid", "no", "stop", "please",
                         "dont", "leave", "away"}
        happy_words   = {"great", "awesome", "love", "happy", "yay",
                         "excited", "wonderful", "nice", "good", "yes"}
        sadness_words = {"sorry", "sad", "crying", "upset", "disappointed",
                         "regret", "miss", "alone"}

        words = set(re.findall(r'\b\w+\b', text)) if text else set()

        anger_hits   = len(words & anger_words)
        fear_hits    = len(words & fear_words)
        happy_hits   = len(words & happy_words)
        sadness_hits = len(words & sadness_words)

        scores = {
            "anger":      anger_hits * 0.35 + (toxicity_score * 0.45 if anger_hits > 0 else toxicity_score * 0.05),
            "fear":       fear_hits  * 0.25 + toxicity_score * 0.15,
            "happiness":  happy_hits * 0.30,
            "sadness":    sadness_hits * 0.20,
            "excitement": happy_hits * 0.10,
            "neutral":    0.20,
        }

        total = sum(scores.values()) or 1.0
        probs_dict = {k: round(v / total, 4) for k, v in scores.items()}
        label = max(probs_dict, key=probs_dict.get)

        return {
            "emotion":       label,
            "confidence":    probs_dict[label],
            "probabilities": probs_dict,
            "is_aggressive": label in AGGRESSIVE_EMOTIONS,
            "is_safe":       label in SAFE_EMOTIONS,
        }


_emotion_model = None

def _find_emotion_weights() -> str:
    this_dir    = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(this_dir)
    for p in [
        os.path.join(project_dir, "emotion_cnn.pth"),
        os.path.join(this_dir,    "emotion_cnn.pth"),
        os.path.join(os.getcwd(), "emotion_cnn.pth"),
        os.environ.get("SAFEGUARD_EMOTION_WEIGHTS", ""),
    ]:
        if p and os.path.isfile(p):
            print(f"[EmotionModel] Found weights at: {p}")
            return p
    return ""

def get_emotion_model() -> EmotionModel:
    global _emotion_model
    if _emotion_model is None:
        _emotion_model = EmotionModel(weights_path=_find_emotion_weights())
    return _emotion_model
