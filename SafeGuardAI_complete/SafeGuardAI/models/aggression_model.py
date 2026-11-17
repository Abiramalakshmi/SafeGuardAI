import os
import torch
import torch.nn as nn

class AggressionModel(nn.Module):
    def __init__(self):
        super().__init__()
        from transformers import Wav2Vec2Model
        self.encoder = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")
        for param in self.encoder.parameters():
            param.requires_grad = False
        self.classifier = nn.Linear(self.encoder.config.hidden_size, 2)

    def forward(self, input_values):
        outputs = self.encoder(input_values)
        hidden_states = outputs.last_hidden_state
        pooled = torch.mean(hidden_states, dim=1)
        return self.classifier(pooled)


def _find_aggression_weights():
    candidates = [
        os.environ.get("SAFEGUARD_AGGRESSION_WEIGHTS", ""),
        "aggression_model.pth",
        os.path.join("models", "aggression_model.pth"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "aggression_model.pth"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "aggression_model.pth"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            if os.path.getsize(p) > 1_000_000:
                return p
    return None


class AggressionModelWrapper:
    def __init__(self):
        self.weights_loaded = False
        self.demo_mode = True
        self._model = None
        self._processor = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        weights_path = _find_aggression_weights()
        if weights_path:
            self._load(weights_path)
        else:
            print("[AggressionModel] No weights found — running in demo mode (score always 0.0).")
            print("  Copy aggression_model.pth to models/ or project root.")

    def _load(self, weights_path):
        try:
            from transformers import Wav2Vec2Processor
            print(f"[AggressionModel] Loading weights from: {weights_path}")
            self._processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base")
            model = AggressionModel()

            # FIX BUG: Use a try/except around weights_only=True so older PyTorch
            # versions and legacy checkpoint formats don't silently fall into demo mode.
            # weights_only=True was added in PyTorch 1.13 and can raise errors on
            # checkpoints saved before PyTorch 2.x. We try the safe form first, then
            # fall back to the legacy form, logging clearly either way.
            try:
                state = torch.load(weights_path, map_location=self._device, weights_only=True)
            except (TypeError, RuntimeError) as e:
                print(f"[AggressionModel] weights_only=True failed ({e}), retrying without it.")
                state = torch.load(weights_path, map_location=self._device)

            model.load_state_dict(state)
            model.eval()
            model.to(self._device)
            self._model = model
            self.weights_loaded = True
            self.demo_mode = False
            print("[AggressionModel] Loaded successfully.")
        except Exception as e:
            print(f"[AggressionModel] Load failed: {e} — falling back to demo mode.")

    def predict(self, wav_path):
        # FIX BUG: Warn on every demo-mode call, not just at init.
        # Previously demo mode returned {"label": "demo"} silently. If downstream
        # code only checks `is_aggressive` (which is always False in demo mode),
        # it will treat every audio clip as safe — wrong default for a safety system.
        if self.demo_mode or self._model is None:
            print("[AggressionModel] WARNING: Running in demo mode — "
                  "aggression_score is always 0.0 and does NOT reflect the actual audio.")
            return {"aggression_score": 0.0, "is_aggressive": False, "label": "demo"}

        try:
            import soundfile as sf
            import numpy as np

            audio, sr = sf.read(wav_path, dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            if sr != 16000:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
                sr = 16000

            inputs = self._processor(
                audio, sampling_rate=sr, return_tensors="pt", padding=True
            )
            input_values = inputs.input_values.to(self._device)

            with torch.no_grad():
                logits = self._model(input_values)
                probs  = torch.softmax(logits, dim=-1)
                score  = float(probs[0, 1])

            return {
                "aggression_score": round(score, 4),
                "is_aggressive":    score >= 0.60,
                "label":            "aggressive" if score >= 0.60 else "normal",
            }
        except Exception as e:
            print(f"[AggressionModel] predict() error: {e}")
            return {"aggression_score": 0.0, "is_aggressive": False, "label": "error"}


_instance = None

def get_aggression_model():
    global _instance
    if _instance is None:
        _instance = AggressionModelWrapper()
    return _instance
