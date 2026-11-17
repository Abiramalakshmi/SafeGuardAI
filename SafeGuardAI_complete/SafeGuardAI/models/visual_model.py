# ============================================================
# SafeGuard AI — Visual Violence Model (ResNet18 / PyTorch)
# ============================================================

import os
import numpy as np
from utils.config import FRAME_SIZE, VIOLENCE_CLASSES

try:
    import torch
    import torch.nn as nn
    import torchvision.models as tv_models
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class VisualViolenceModel:
    def __init__(self, weights_path: str = None):
        self.device         = None
        self.model          = None
        self.transform      = None
        self.demo_mode      = True
        self.weights_loaded = False

        if not TORCH_AVAILABLE:
            print("[VisualModel] PyTorch not available — running in DEMO mode.")
            return

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = self._build_model()
        self.model.to(self.device)
        self.model.eval()
        self.transform = self._build_transform()

        wp = weights_path or os.environ.get("SAFEGUARD_VISUAL_WEIGHTS", "")
        if wp and os.path.isfile(wp):
            try:
                state = torch.load(wp, map_location=self.device)
                state = self._remap_fc_keys(state)
                self.model.load_state_dict(state)
                self.demo_mode      = False
                self.weights_loaded = True
                print(f"[VisualModel] Loaded weights: {wp}")
            except Exception as e:
                print(f"[VisualModel] Could not load weights ({e}) — DEMO mode.")
        else:
            print("[VisualModel] No weights found — DEMO mode.")

    def _remap_fc_keys(self, state_dict: dict) -> dict:
        remapped = {}
        for k, v in state_dict.items():
            if k == "fc.1.weight":  remapped["fc.weight"] = v
            elif k == "fc.1.bias":  remapped["fc.bias"]   = v
            else:                   remapped[k]            = v
        return remapped

    def _build_model(self):
        model = tv_models.resnet18(weights=None)
        model.fc = nn.Linear(model.fc.in_features, 2)
        return model

    def _build_transform(self):
        return transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(FRAME_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std =[0.229, 0.224, 0.225])
        ])

    def predict_frame(self, frame_bgr) -> float:
        if not TORCH_AVAILABLE or self.model is None:
            return 0.10
        import cv2
        tensor = self.transform(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).unsqueeze(0).to(self.device)
        with torch.no_grad():
            prob = torch.softmax(self.model(tensor), dim=1)[0, 1].item()
        return float(np.clip(prob, 0.0, 0.45)) if self.demo_mode else float(prob)

    def predict_frames(self, frames: list) -> dict:
        if not frames:
            return {"scores": [], "mean_score": 0.0, "max_score": 0.0,
                    "violence_detected": False, "frame_count": 0}
        scores = [self.predict_frame(f) for f in frames]
        mean_s = float(np.mean(scores))
        return {"scores": scores, "mean_score": round(mean_s, 4),
                "max_score": round(float(np.max(scores)), 4),
                "violence_detected": mean_s >= 0.65, "frame_count": len(frames)}

    def predict_batch(self, frames: list, batch_size: int = 16) -> list:
        if not TORCH_AVAILABLE or self.model is None:
            return [0.10 for _ in frames]
        import cv2
        all_scores = []
        for i in range(0, len(frames), batch_size):
            tensors = [self.transform(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
                       for f in frames[i:i + batch_size]]
            with torch.no_grad():
                probs = torch.softmax(self.model(torch.stack(tensors).to(self.device)), dim=1)
                all_scores.extend(probs[:, 1].cpu().numpy().tolist())
        return all_scores


# ── Singleton ─────────────────────────────────────────────
_visual_model = None

def _find_weights() -> str:
    this_dir    = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(this_dir)
    for p in [
        os.path.join(project_dir, "violence_resnet18_rlvs.pth"),  # project root ← most likely
        os.path.join(this_dir,    "violence_resnet18_rlvs.pth"),  # inside models/
        os.path.join(os.getcwd(), "violence_resnet18_rlvs.pth"),  # cwd
        os.environ.get("SAFEGUARD_VISUAL_WEIGHTS", ""),           # env override
    ]:
        if p and os.path.isfile(p):
            print(f"[VisualModel] Found weights at: {p}")
            return p
    return ""

def get_visual_model() -> VisualViolenceModel:
    global _visual_model
    if _visual_model is None:
        _visual_model = VisualViolenceModel(weights_path=_find_weights())
    return _visual_model