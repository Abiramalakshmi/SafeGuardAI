# ============================================================
# SafeGuard AI — Main Processing Pipeline
# ============================================================
# Active signal stack:
#   1. Visual violence  — ResNet18 (predict_batch)
#   2. Audio toxicity   — Whisper + DistilBERT
#   3. Speech aggression— Wav2Vec2 binary classifier
#   4. Emotion          — Audio CNN (mel spectrogram)
#
# Face emotion REMOVED — unreliable on arbitrary videos
# ============================================================

import os
import numpy as np
from datetime import datetime

from utils.config import (
    VISUAL_WEIGHT, AUDIO_WEIGHT, FRAME_SAMPLE_RATE,
    VIOLENCE_THRESHOLD, TOXICITY_THRESHOLD, TEMPORAL_WINDOW
)

# Metric 7: Fused Risk uses equal weights Wv=0.5, Wa=0.5 per metric specification.
# Override config values here to ensure formula compliance.
VISUAL_WEIGHT = 0.5
AUDIO_WEIGHT  = 0.5
from preprocessing.video_processing  import extract_frames, temporal_smooth
from preprocessing.audio_processing  import extract_audio_from_video, record_microphone, safe_transcribe
from models.visual_model              import get_visual_model
from models.audio_model               import get_audio_model
from models.emotion_model             import get_emotion_model
from models.aggression_model          import get_aggression_model
from alerts.alert_manager             import compute_fused_score, determine_alert_level, get_alert_manager
from database.db_manager              import insert_incident


def analyze_video(video_path: str, source_label: str = "UPLOAD", wav_path_override: str | None = None, clip_path: str = None) -> dict:
    result        = _empty_result(source_label)
    score_history = []

    # ── 1 & 2: Visual ────────────────────────────────────────
    frames = []
    try:
        frames = extract_frames(video_path, sample_fps=FRAME_SAMPLE_RATE)
        if frames:
            visual_model = get_visual_model()
            batch_scores = visual_model.predict_batch(frames, batch_size=16)

            # ── Metric 2: Visual Risk Score Rv = (1/N) Σpᵢ ──────
            mean_score = float(np.mean(batch_scores)) if batch_scores else 0.0

            # ── Metric 3: Fight Ratio = violent_frames / total_frames ──
            # A frame is "violent" if its probability exceeds 0.5
            violent_frames = sum(1 for s in batch_scores if s >= 0.5)
            fight_ratio    = round(violent_frames / len(batch_scores), 4) if batch_scores else 0.0

            result["visual_score"] = round(mean_score, 4)
            result["fight_ratio"]  = fight_ratio
            result["frame_scores"] = [round(s, 4) for s in batch_scores]
            result["frame_count"]  = len(frames)
    except Exception as e:
        result["errors"].append(f"Visual processing: {e}")

    # ── 3, 4, 5: Audio + Transcript + Toxicity ───────────────
    wav_path           = None
    extracted_temp_wav = False
    try:
        if wav_path_override and os.path.isfile(wav_path_override):
            wav_path = wav_path_override
        else:
            wav_path = extract_audio_from_video(video_path)
            extracted_temp_wav = True
        audio_result = get_audio_model().analyze(wav_path)

        # ── Hallucination guard ───────────────────────────────
        # Whisper hallucinates threatening sentences on near-silent or
        # background-noise audio (e.g. archery crowd sounds).
        # safe_transcribe() re-checks via RMS energy + no_speech_prob.
        raw_transcript  = audio_result.get("transcript", "") or ""
        audio_model_obj = get_audio_model()
        whisper_mdl     = getattr(audio_model_obj, "whisper_model", None)

        if whisper_mdl is not None and raw_transcript.strip():
            verified_transcript, speech_conf = safe_transcribe(wav_path, whisper_mdl)
            if not verified_transcript.strip() and speech_conf == 0.0:
                # Whisper hallucinated — wipe the fabricated transcript & toxicity
                audio_result["transcript"]     = ""
                audio_result["toxicity_score"] = 0.0
                audio_result["toxic_phrases"]  = []
                audio_result["toxicity_label"] = "non-toxic"
            else:
                audio_result["transcript"] = verified_transcript

        result["transcript"]     = audio_result["transcript"]
        result["toxicity_score"] = audio_result["toxicity_score"]
        result["toxicity_label"] = audio_result["toxicity_label"]
        result["toxic_phrases"]  = audio_result["toxic_phrases"]
    except Exception as e:
        result["errors"].append(f"Audio processing: {e}")

    # ── 5b: Aggression detection (Wav2Vec2) ───────────────────
    try:
        if wav_path and os.path.isfile(wav_path):
            ag = get_aggression_model().predict(wav_path)
            result["aggression_score"]     = ag["aggression_score"]
            result["is_speech_aggressive"] = ag["is_aggressive"]
    except Exception as e:
        result["errors"].append(f"Aggression detection: {e}")

    # ── 6: Emotion ────────────────────────────────────────────
    try:
        emotion_model = get_emotion_model()
        emo_audio     = None

        if wav_path and os.path.isfile(wav_path):
            emo_audio = emotion_model.predict_from_wav(wav_path)

        emo_transcript = emotion_model.predict_from_transcript(
            result["transcript"], result["toxicity_score"]
        )
        result["transcript_emotion"]      = emo_transcript.get("emotion", "neutral")
        result["transcript_emotion_conf"] = float(emo_transcript.get("confidence", 0.0) or 0.0)

        no_speech  = not (result.get("transcript") or "").strip()
        # FIX: "A-A-A-A-A" is non-empty but is NOT real speech — it's a Whisper hallucination.
        # Apply the same repetition-ratio test here before trusting the transcript for emotion.
        raw_transcript = (result.get("transcript") or "").strip()
        _t_words = raw_transcript.split()
        _unique_ratio = (len(set(w.lower() for w in _t_words)) / len(_t_words)) if len(_t_words) >= 3 else 1.0
        has_speech = (
            len(raw_transcript) >= 12 and
            len(_t_words) >= 3 and
            _unique_ratio >= 0.30   # rejects "A-A-A-A-A" type hallucinations
        )
        no_speech = not has_speech
        if no_speech and float(result.get("toxicity_score", 0.0) or 0.0) == 0.0:
            emo_audio = None

        chosen = None
        source = "transcript"

        if has_speech:
            chosen = emo_transcript
            source = "transcript"
        elif emo_audio is not None and not getattr(emotion_model, "demo_mode", True):
            if float(emo_audio.get("confidence", 0.0) or 0.0) >= 0.45:
                chosen = emo_audio
                source = "audio"

        if chosen is None:
            chosen = emo_transcript
            source = "transcript"

        result["emotion"]        = chosen.get("emotion", "neutral")
        result["emotion_conf"]   = float(chosen.get("confidence", 0.0) or 0.0)
        result["emotion_probs"]  = chosen.get("probabilities", {}) or {}
        result["is_aggressive"]  = bool(chosen.get("is_aggressive", False))
        result["emotion_source"] = source
    except Exception as e:
        result["errors"].append(f"Emotion detection: {e}")

    if extracted_temp_wav and wav_path and os.path.isfile(wav_path):
        try: os.remove(wav_path)
        except: pass

    return _finalize(result, source_label, score_history, clip_path=clip_path)


def analyze_webcam(duration: int = 5, cam_index: int = 0) -> dict:
    from preprocessing.video_processing import capture_webcam_frames
    result        = _empty_result("LIVE")
    score_history = []
    frames        = []
    wav_path      = None

    try:
        import threading
        mic_result = {}

        def capture_audio():
            try:
                path = record_microphone(duration)
                mic_result["path"] = path
            except Exception as e:
                mic_result["error"] = str(e)

        audio_thread = threading.Thread(target=capture_audio, daemon=True)
        audio_thread.start()
        frames = capture_webcam_frames(duration, cam_index, FRAME_SAMPLE_RATE)
        audio_thread.join(timeout=duration + 5)
        wav_path = mic_result.get("path")
    except Exception as e:
        result["errors"].append(f"Capture: {e}")

    if frames:
        try:
            visual_model = get_visual_model()
            batch_scores = visual_model.predict_batch(frames, batch_size=16)
            violent_frames = sum(1 for s in batch_scores if s >= 0.5)
            fight_ratio    = round(violent_frames / len(batch_scores), 4) if batch_scores else 0.0
            result["visual_score"] = round(float(np.mean(batch_scores)), 4)
            result["fight_ratio"]  = fight_ratio
            result["frame_scores"] = [round(s, 4) for s in batch_scores]
            result["frame_count"]  = len(frames)
        except Exception as e:
            result["errors"].append(f"Visual: {e}")

    if wav_path and os.path.isfile(wav_path):
        try:
            audio_result    = get_audio_model().analyze(wav_path)
            raw_transcript  = audio_result.get("transcript", "") or ""
            audio_model_obj = get_audio_model()
            whisper_mdl     = getattr(audio_model_obj, "whisper_model", None)

            # FIX: hallucination guard was present in analyze_video but missing here.
            if whisper_mdl is not None and raw_transcript.strip():
                verified_transcript, speech_conf = safe_transcribe(wav_path, whisper_mdl)
                if not verified_transcript.strip() and speech_conf == 0.0:
                    audio_result["transcript"]     = ""
                    audio_result["toxicity_score"] = 0.0
                    audio_result["toxic_phrases"]  = []
                    audio_result["toxicity_label"] = "non-toxic"
                else:
                    audio_result["transcript"] = verified_transcript

            result["transcript"]     = audio_result["transcript"]
            result["toxicity_score"] = audio_result["toxicity_score"]
            result["toxic_phrases"]  = audio_result["toxic_phrases"]
        except Exception as e:
            result["errors"].append(f"Audio: {e}")

    if wav_path and os.path.isfile(wav_path):
        try:
            ag = get_aggression_model().predict(wav_path)
            result["aggression_score"]     = ag["aggression_score"]
            result["is_speech_aggressive"] = ag["is_aggressive"]
        except Exception as e:
            result["errors"].append(f"Aggression: {e}")

    try:
        emotion_model = get_emotion_model()
        emo_result    = None
        if wav_path and os.path.isfile(wav_path):
            emo_result = emotion_model.predict_from_wav(wav_path)
        if emo_result is None:
            emo_result = emotion_model.predict_from_transcript(
                result["transcript"], result["toxicity_score"]
            )
        result["emotion"]       = emo_result["emotion"]
        result["emotion_conf"]  = emo_result["confidence"]
        result["emotion_probs"] = emo_result["probabilities"]
        result["is_aggressive"] = emo_result["is_aggressive"]
    except Exception as e:
        result["errors"].append(f"Emotion: {e}")

    if wav_path and os.path.isfile(wav_path):
        try: os.remove(wav_path)
        except: pass

    return _finalize(result, "LIVE", score_history)


# ── FIX 2: Added clip_path parameter to analyze_audio_only ──
def analyze_audio_only(wav_path: str, source_label: str = "UPLOAD", clip_path: str = None) -> dict:
    result        = _empty_result(source_label)
    score_history = []   # FIX: was undefined — caused NameError in _finalize()

    try:
        audio_result = get_audio_model().analyze(wav_path)

        # FIX: Hallucination guard was missing here (present in analyze_video but not
        # analyze_audio_only).  Without this, Whisper's fabricated transcripts on
        # near-silent or noisy audio were passed through unchecked.
        raw_transcript  = audio_result.get("transcript", "") or ""
        audio_model_obj = get_audio_model()
        whisper_mdl     = getattr(audio_model_obj, "whisper_model", None)

        if whisper_mdl is not None and raw_transcript.strip():
            verified_transcript, speech_conf = safe_transcribe(wav_path, whisper_mdl)
            if not verified_transcript.strip() and speech_conf == 0.0:
                # Whisper hallucinated — discard fabricated transcript and toxicity
                audio_result["transcript"]     = ""
                audio_result["toxicity_score"] = 0.0
                audio_result["toxic_phrases"]  = []
                audio_result["toxicity_label"] = "non-toxic"
            else:
                audio_result["transcript"] = verified_transcript

        result["transcript"]     = audio_result["transcript"]
        result["toxicity_score"] = audio_result["toxicity_score"]
        result["toxicity_label"] = audio_result["toxicity_label"]
        result["toxic_phrases"]  = audio_result["toxic_phrases"]
    except Exception as e:
        result["errors"].append(str(e))

    try:
        ag = get_aggression_model().predict(wav_path)
        result["aggression_score"]     = ag["aggression_score"]
        result["is_speech_aggressive"] = ag["is_aggressive"]
    except Exception as e:
        result["errors"].append(f"Aggression: {e}")

    try:
        emotion_model = get_emotion_model()
        emo_result    = emotion_model.predict_from_wav(wav_path)
        if emo_result is None:
            emo_result = emotion_model.predict_from_transcript(
                result["transcript"], result["toxicity_score"]
            )
        result["emotion"]       = emo_result["emotion"]
        result["emotion_conf"]  = emo_result["confidence"]
        result["emotion_probs"] = emo_result["probabilities"]
        result["is_aggressive"] = emo_result["is_aggressive"]
    except Exception as e:
        result["errors"].append(str(e))

    # ── FIX 2: pass clip_path through to _finalize so it gets saved to DB ──
    return _finalize(result, source_label, score_history=[], clip_path=clip_path)


# ── Helpers ───────────────────────────────────────────────────

def _empty_result(source: str) -> dict:
    return {
        "source":                  source,
        "timestamp":               datetime.now().isoformat(),
        "visual_score":            0.0,
        "fight_ratio":             0.0,   # Metric: violent_frames / total_frames
        "audio_aggression_score":  0.0,   # Metric: Ra = 0.5*p_tox + 0.5*p_emo
        "toxicity_score":          0.0,
        "toxicity_label":          "non-toxic",
        "fused_score":             0.0,
        "alert_level":             "SAFE",
        "emotion":                 "neutral",
        "emotion_conf":            0.0,
        "emotion_probs":           {},
        "emotion_source":          "transcript",
        "transcript_emotion":      "neutral",
        "transcript_emotion_conf": 0.0,
        "is_aggressive":           False,
        "transcript":              "",
        "toxic_phrases":           [],
        "frame_scores":            [],
        "frame_count":             0,
        "aggression_score":        0.0,
        "is_speech_aggressive":    False,
        "video_confidence":        0.0,   # Metric: 0.6*frame_factor + 0.4*extremeness
        "audio_confidence":        0.0,   # Metric: 0.5*duration_factor + 0.5*signal_factor
        "final_confidence":        0.0,   # Metric: (vc^wv) * (ac^wa) * certainty_adj
        "errors":                  [],
        "incident_id":             None,
    }


def _compute_confidence(result: dict) -> tuple:
    """
    Compute video confidence, audio confidence, and final confidence.

    Confidence answers: "How CERTAIN are we about this classification?"
    It measures prediction decisiveness — NOT threat strength.
    A clear SAFE result should produce HIGH confidence, not low.

    Metric 10 — Video Confidence:
        Measures how much evidence the visual model had and how decisive it was.
        frame_factor  = min(frame_count / 30, 1.0)   — saturates at 30 frames
        extremeness   = mean(|pᵢ - 0.5| * 2)         — how far each frame is from
                                                         the 0.5 decision boundary
                                                         (0%=certain safe, 100%=certain fight)
        video_confidence = 0.6 * frame_factor + 0.4 * extremeness

    Metric 11 — Audio Confidence:
        Measures how much audio evidence was available and how decisive it was.
        coverage_factor  = 1.0 if no speech detected (absence is decisive),
                           else min(word_count / 20, 1.0)
        decisiveness     = |Ra - 0.5| * 2  — distance of audio aggression from the
                                              0.5 boundary; near-zero Ra is decisive,
                                              mid-range Ra is uncertain
        audio_confidence = 0.5 * coverage_factor + 0.5 * decisiveness

    Metric 12 — Final Confidence:
        Geometric weighted mean of both modalities.
        final_confidence = (video_conf ^ wv) * (audio_conf ^ wa)

    Metric 13 — Certainty Adjustment:
        Scales by how far the fused score is from the 0.5 uncertainty midpoint.
        certainty = 0.5 + 0.5 * |Rf - 0.5| * 2
        — fused ≈ 0.5 (ambiguous) → certainty ≈ 0.5 (dampens confidence)
        — fused ≈ 0.0 or 1.0 (decisive) → certainty ≈ 1.0 (full confidence)
    """
    frame_scores = result.get("frame_scores", [])
    frame_count  = result.get("frame_count", 0)
    fused        = result.get("fused_score", 0.0)
    ra           = result.get("audio_aggression_score", 0.0)
    transcript   = result.get("transcript", "") or ""

    # ── Video confidence ─────────────────────────────────────
    # Measures: do we have enough frames, and are per-frame predictions decisive?
    # A video with 18 frames all scoring ~0% fight probability is very decisive.
    if frame_scores and frame_count > 0:
        frame_factor = min(frame_count / 30.0, 1.0)
        # extremeness: distance from 0.5 boundary — 0% fight → extremeness = 1.0 (certain safe)
        extremeness  = float(np.mean([abs(p - 0.5) * 2 for p in frame_scores]))
        video_conf   = round(0.6 * frame_factor + 0.4 * extremeness, 4)
    else:
        video_conf = 0.0

    # ── Audio confidence ─────────────────────────────────────
    # KEY FIX: signal_factor previously used Ra directly (min(Ra*2, 1.0)), which
    # meant zero aggression → zero signal → zero audio confidence.
    # Corrected: use DECISIVENESS = distance of Ra from the 0.5 boundary.
    # Ra = 0.0 (no aggression at all) is just as decisive as Ra = 1.0 (full aggression).
    # Ra = 0.5 (borderline) is the only genuinely uncertain state.
    word_count = len(transcript.split()) if transcript.strip() else 0
    if word_count == 0:
        # No speech detected — this is a decisive result (absence of threat is clear)
        coverage_factor = 1.0
    else:
        coverage_factor = min(word_count / 20.0, 1.0)
    decisiveness = abs(ra - 0.5) * 2.0          # 0.0 Ra → 1.0 decisive, 0.5 Ra → 0.0 decisive
    audio_conf   = round(0.5 * coverage_factor + 0.5 * decisiveness, 4)

    # ── Final confidence (geometric weighted mean) ────────────
    wv = VISUAL_WEIGHT   # 0.5
    wa = AUDIO_WEIGHT    # 0.5
    if video_conf > 0.0 and audio_conf > 0.0:
        raw_conf = (video_conf ** wv) * (audio_conf ** wa)
    elif video_conf > 0.0:
        raw_conf = video_conf
    elif audio_conf > 0.0:
        raw_conf = audio_conf
    else:
        raw_conf = 0.0

    # ── Certainty adjustment ──────────────────────────────────
    # Wider range than before (0.5–1.0 instead of 0.6–1.0) so ambiguous fused
    # scores near 0.5 are more meaningfully penalised.
    certainty  = 0.5 + 0.5 * abs(fused - 0.5) * 2.0
    final_conf = round(float(np.clip(raw_conf * certainty, 0.0, 1.0)), 4)

    return video_conf, audio_conf, final_conf


def _finalize(result: dict, source: str, score_history: list, clip_path: str = None) -> dict:
    score_history.append(result["visual_score"])
    smoothed_visual = temporal_smooth(score_history, TEMPORAL_WINDOW)

    # ── Metric 6: Audio Aggression Score Ra = 0.5*p_tox + 0.5*p_emo ──────────
    # p_tox = toxicity probability (DistilBERT)
    # p_emo = acoustic aggression probability (Wav2Vec2)
    p_tox = float(result.get("toxicity_score",   0.0) or 0.0)
    p_emo = float(result.get("aggression_score", 0.0) or 0.0)
    ra    = round(0.5 * p_tox + 0.5 * p_emo, 4)
    result["audio_aggression_score"] = ra   # Ra — the proper combined audio signal

    # ── Metric 7: Fused Risk Score Rf = wv*Rv + wa*Ra ────────────────────────
    # wv = 0.5, wa = 0.5  (equal weight as per the metric specification)
    visual = smoothed_visual
    fused  = 0.0 if (visual == 0.0 and ra == 0.0) else \
             compute_fused_score(visual, ra, VISUAL_WEIGHT, AUDIO_WEIGHT)

    result["visual_score"] = round(smoothed_visual, 4)
    result["fused_score"]  = round(fused, 4)

    # ── Metric 8: Threshold-based classification ──────────────────────────────
    # Uses Rf (fused score) as primary signal, with modality overrides
    alert_level = determine_alert_level(
        smoothed_visual,
        result["toxicity_score"],
        result["emotion"],
        aggression_score=result.get("aggression_score", 0.0),
        audio_aggression_score=ra,          # pass Ra for fused-threshold check
        fused_score=fused,                  # pass Rf directly
    )
    result["alert_level"] = alert_level

    # ── Metrics 10–14: Confidence scores ─────────────────────────────────────
    video_conf, audio_conf, final_conf = _compute_confidence(result)
    result["video_confidence"] = video_conf
    result["audio_confidence"] = audio_conf
    result["final_confidence"] = final_conf

    try:
        iid = insert_incident(
            violence_score   = smoothed_visual,
            emotion_detected = result["emotion"],
            toxicity_score   = result["toxicity_score"],
            transcript       = result["transcript"],
            toxic_phrases    = result["toxic_phrases"],
            video_source     = source,
            alert_level      = alert_level,
            aggression_score = result.get("aggression_score", 0.0),
            clip_path        = clip_path,
        )
        result["incident_id"] = iid
    except Exception as e:
        result["errors"].append(f"DB insert: {e}")

    if alert_level != "SAFE":
        get_alert_manager().trigger(
            violence_score         = smoothed_visual,
            emotion                = result["emotion"],
            toxicity_score         = result["toxicity_score"],
            toxic_phrases          = result["toxic_phrases"],
            source                 = source,
            transcript             = result["transcript"],
            aggression_score       = result.get("aggression_score", 0.0),
            audio_aggression_score = ra,
            fused_score            = fused,
            final_confidence       = result["final_confidence"],
        )

    return result


# ════════════════════════════════════════════════════════════
# RECORD + ANALYZE
# ════════════════════════════════════════════════════════════
def record_and_analyze(duration: int, save_path: str) -> dict:
    import threading, time as _time
    wav_path = save_path.replace(".mp4", ".wav")
    rh       = {}

    def _capture():
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cam_fps = cap.get(cv2.CAP_PROP_FPS) or 20
            cam_fps = max(10.0, min(float(cam_fps), 30.0))
            fourcc  = cv2.VideoWriter_fourcc(*"mp4v")
            writer  = cv2.VideoWriter(save_path, fourcc, cam_fps, (640, 480))

            has_audio = False
            audio_buf = []
            try:
                import sounddevice as sd
                sr = 16000
                def _cb(indata, frames, t, status):
                    audio_buf.extend(indata[:, 0].tolist())
                stream = sd.InputStream(samplerate=sr, channels=1, callback=_cb)
                stream.start()
                has_audio = True
            except Exception as ae:
                rh["audio_warn"] = str(ae)

            t0 = _time.time()
            while _time.time() - t0 < duration:
                ret, frame = cap.read()
                if ret:
                    writer.write(frame)

            cap.release()
            writer.release()

            if has_audio:
                stream.stop(); stream.close()
                import numpy as np_i, scipy.io.wavfile as wio
                a   = np_i.array(audio_buf, dtype=np_i.float32)
                a   = np_i.clip(a, -1.0, 1.0)
                a16 = (a * 32767.0).astype(np_i.int16)
                wio.write(wav_path, sr, a16)
                rh["wav"] = wav_path

            rh["ok"] = True
        except Exception as e:
            rh["error"] = str(e)

    t = threading.Thread(target=_capture, daemon=True)
    t.start()
    t.join(timeout=duration + 15)

    if "error" in rh:
        raise RuntimeError(f"Recording failed: {rh['error']}")
    if not rh.get("ok"):
        raise RuntimeError("Recording timed out.")

    return analyze_video(save_path, "LIVE_RECORD")


# ════════════════════════════════════════════════════════════
# SYSTEM STATUS
# ════════════════════════════════════════════════════════════
def get_system_status() -> dict:
    results = {}

    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ok  = cap.isOpened(); cap.release()
        results["camera"] = {"status":"ok" if ok else "err",
            "message":"Connected" if ok else "Not detected","detail":"Webcam / IP Camera"}
    except ImportError:
        results["camera"] = {"status":"warn","message":"opencv-python not installed","detail":"pip install opencv-python"}

    try:
        import sounddevice as sd
        inp = [d for d in sd.query_devices() if d["max_input_channels"] > 0]
        results["audio"] = {"status":"ok","message":f"{len(inp)} input device(s) found","detail":"Microphone / Audio Input"}
    except ImportError:
        results["audio"] = {"status":"warn","message":"sounddevice not installed","detail":"pip install sounddevice"}

    try:
        vm = get_visual_model()
        loaded = getattr(vm, "weights_loaded", False)
        results["visual"] = {"status":"ok" if loaded else "warn",
            "message":"ResNet18 weights loaded" if loaded else "Demo mode — no weights",
            "detail":"Violence Detection Model"}
    except Exception as e:
        results["visual"] = {"status":"err","message":str(e)[:80],"detail":"Violence Detection Model"}

    try:
        am = get_audio_model()
        db = getattr(am, "distilbert_available", False)
        wh = getattr(am, "whisper_model", None) is not None
        results["audio_model"] = {"status":"ok" if wh else "warn",
            "message":"DistilBERT + Whisper ready" if (db and wh) else ("Whisper ready" if wh else "Models not loaded"),
            "detail":"ASR + Toxicity Model"}
    except Exception as e:
        results["audio_model"] = {"status":"err","message":str(e)[:80],"detail":"ASR + Toxicity Model"}

    try:
        em = get_emotion_model()
        hw = getattr(em, "weights_loaded", False)
        results["emotion"] = {"status":"ok" if hw else "warn",
            "message":"CNN weights loaded" if hw else "Acoustic heuristic mode",
            "detail":"Emotion Detection Model"}
    except Exception as e:
        results["emotion"] = {"status":"err","message":str(e)[:80],"detail":"Emotion Detection Model"}

    try:
        ag = get_aggression_model()
        loaded = getattr(ag, "weights_loaded", False)
        results["aggression"] = {"status":"ok" if loaded else "warn",
            "message":"Wav2Vec2 aggression model loaded" if loaded else "Demo mode — place aggression_model.pth in models/",
            "detail":"Speech Aggression Detector (Wav2Vec2)"}
    except Exception as e:
        results["aggression"] = {"status":"err","message":str(e)[:80],"detail":"Speech Aggression Detector"}

    try:
        from database.db_manager import get_stats
        s = get_stats()
        results["database"] = {"status":"ok","message":f"SQLite connected — {s['total']} records","detail":"Incident Database"}
    except Exception as e:
        results["database"] = {"status":"err","message":str(e)[:80],"detail":"SQLite Database"}

    try:
        import torch
        cuda = torch.cuda.is_available()
        results["torch"] = {"status":"ok",
            "message":f"PyTorch {torch.__version__}  ·  {'GPU: '+torch.cuda.get_device_name(0) if cuda else 'CPU only'}",
            "detail":"Deep Learning Runtime"}
    except ImportError:
        results["torch"] = {"status":"err","message":"PyTorch not installed","detail":"Deep Learning Runtime"}

    try:
        rec_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
        files   = [f for f in os.listdir(rec_dir) if f.endswith(".mp4")] if os.path.isdir(rec_dir) else []
        size_mb = sum(os.path.getsize(os.path.join(rec_dir, f)) for f in files) // 1024 // 1024
        results["storage"] = {"status":"ok","message":f"{len(files)} recording(s)  ·  {size_mb} MB used","detail":f"Folder: {rec_dir}"}
    except Exception as e:
        results["storage"] = {"status":"warn","message":str(e),"detail":"Recordings Storage"}

    return results
