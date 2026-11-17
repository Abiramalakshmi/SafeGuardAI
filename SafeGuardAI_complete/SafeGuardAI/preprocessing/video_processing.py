# ============================================================
# SafeGuard AI — Video Preprocessing
# ============================================================

import cv2
import numpy as np
from utils.config import FRAME_SAMPLE_RATE, FRAME_SIZE


def extract_frames(video_path: str, sample_fps: int = FRAME_SAMPLE_RATE) -> list:
    """
    Extract frames from a video file at a given sample rate.
    Returns list of numpy arrays (BGR, uint8).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval  = max(1, int(video_fps / sample_fps))

    frames = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval == 0:
            frames.append(frame.copy())
        frame_idx += 1

    cap.release()
    return frames


def preprocess_frame(frame: np.ndarray, size: tuple = FRAME_SIZE) -> np.ndarray:
    """
    Resize and normalize a BGR frame for model input.
    Returns float32 array shaped (3, H, W) in [0,1], RGB.
    """
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized   = cv2.resize(frame_rgb, size)
    normalized = resized.astype(np.float32) / 255.0

    # ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (normalized - mean) / std

    # HWC → CHW
    return np.transpose(normalized, (2, 0, 1))


def preprocess_frames_batch(frames: list, size: tuple = FRAME_SIZE) -> np.ndarray:
    """
    Preprocess a list of frames into a batch tensor (N, 3, H, W).
    """
    batch = [preprocess_frame(f, size) for f in frames]
    return np.stack(batch, axis=0)


def capture_webcam_frames(duration_seconds: int = 5,
                           cam_index: int = 0,
                           sample_fps: int = FRAME_SAMPLE_RATE) -> list:
    """
    Capture frames from the webcam for `duration_seconds`.
    Returns list of BGR numpy arrays.
    """
    import time
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise RuntimeError("Cannot access webcam. Check camera permissions.")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    interval  = max(1, int(video_fps / sample_fps))

    frames = []
    frame_idx = 0
    start_time = time.time()

    while time.time() - start_time < duration_seconds:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval == 0:
            frames.append(frame.copy())
        frame_idx += 1

    cap.release()
    return frames


def frames_to_jpeg_bytes(frames: list, max_frames: int = 6) -> list:
    """
    Convert a sample of frames to JPEG bytes for display in Streamlit.
    """
    step = max(1, len(frames) // max_frames)
    selected = frames[::step][:max_frames]
    jpegs = []
    for f in selected:
        _, buf = cv2.imencode(".jpg", f)
        jpegs.append(buf.tobytes())
    return jpegs


def temporal_smooth(scores: list, window: int = 5) -> float:
    """
    Average the last `window` scores to reduce noise spikes.
    """
    if not scores:
        return 0.0
    recent = scores[-window:]
    return float(np.mean(recent))
