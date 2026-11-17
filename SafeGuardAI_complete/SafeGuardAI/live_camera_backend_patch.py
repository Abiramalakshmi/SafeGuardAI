# ============================================================
# PATCH — add this block to api.py
# Place it right after the existing /analyze-recording endpoint
# ============================================================

import base64
import cv2
import numpy as np

@app.post("/analyze-live-frames")
async def analyze_live_frames_endpoint(request: Request):
    """
    Accepts a JSON body:
      { "frames": ["<base64-jpeg>", ...] }

    Each string is a base64-encoded JPEG captured by the browser webcam.
    Runs the visual pipeline on the frames and returns the standard result dict.
    No audio analysis (browser captures video-only frames).
    """
    from models.visual_model import get_visual_model
    from alerts.alert_manager import compute_fused_score, determine_alert_level
    from preprocessing.video_processing import preprocess_frame

    body = await request.json()
    b64_frames = body.get("frames", [])

    if not b64_frames:
        raise HTTPException(400, "No frames provided")

    # Decode base64 JPEGs → numpy BGR frames
    frames = []
    for b64 in b64_frames:
        try:
            # Strip data-URL prefix if present (data:image/jpeg;base64,...)
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            img_bytes = base64.b64decode(b64)
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None:
                frames.append(frame)
        except Exception:
            pass  # skip corrupt frames

    if not frames:
        raise HTTPException(400, "Could not decode any frames")

    result = {
        "source": "LIVE_CAMERA",
        "visual_score": 0.0,
        "fight_ratio": 0.0,
        "frame_scores": [],
        "frame_count": len(frames),
        "toxicity_score": 0.0,
        "toxicity_label": "n/a",
        "toxic_phrases": [],
        "transcript": "",
        "aggression_score": 0.0,
        "audio_aggression_score": 0.0,
        "is_speech_aggressive": False,
        "is_aggressive": False,
        "fused_score": 0.0,
        "alert_level": "SAFE",
        "final_confidence": None,
        "errors": [],
    }

    try:
        visual_model = get_visual_model()
        batch_scores = visual_model.predict_batch(frames, batch_size=16)

        mean_score = float(np.mean(batch_scores)) if batch_scores else 0.0
        violent_frames = sum(1 for s in batch_scores if s >= 0.5)
        fight_ratio = round(violent_frames / len(batch_scores), 4) if batch_scores else 0.0

        result["visual_score"] = round(mean_score, 4)
        result["fight_ratio"] = fight_ratio
        result["frame_scores"] = [round(s, 4) for s in batch_scores]
    except Exception as e:
        result["errors"].append(f"Visual processing: {e}")

    # Fuse (visual only — no audio from browser frames)
    fused = round(result["visual_score"], 4)
    result["fused_score"] = fused
    result["alert_level"] = determine_alert_level(fused, result["toxicity_score"])

    log_action("system", "Live camera analysis", f"{len(frames)} frames", "incident", _client_ip(request))
    return result
