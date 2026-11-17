# ============================================================
# SafeGuard AI — Audio Preprocessing
# ============================================================

import os
import subprocess
import tempfile
import numpy as np
from utils.config import AUDIO_SAMPLE_RATE


def extract_audio_from_video(video_path: str, output_wav: str = None) -> str:
    """
    Extract audio track from video using ffmpeg.
    Returns path to WAV file.
    """
    if output_wav is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output_wav = tmp.name
        tmp.close()

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", "1",
        output_wav
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Try with moviepy as fallback
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(video_path)
            if clip.audio is not None:
                clip.audio.write_audiofile(
                    output_wav,
                    fps=AUDIO_SAMPLE_RATE,
                    nbytes=2,
                    logger=None
                )
                clip.close()
            else:
                # No audio track — write silence
                _write_silence(output_wav)
        except Exception:
            _write_silence(output_wav)

    return output_wav


def _write_silence(wav_path: str, duration: float = 1.0):
    """Write a short silent WAV file as a placeholder."""
    import wave, struct
    n_samples = int(AUDIO_SAMPLE_RATE * duration)
    with wave.open(wav_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(struct.pack('<' + 'h' * n_samples, *([0] * n_samples)))


def load_wav(wav_path: str) -> np.ndarray:
    """
    Load WAV file into float32 numpy array [-1, 1].
    Falls back to zeros on error.
    """
    try:
        import wave, struct
        with wave.open(wav_path, 'r') as wf:
            n_frames  = wf.getnframes()
            raw       = wf.readframes(n_frames)
            n_channels = wf.getnchannels()
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        samples /= 32768.0
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1)
        return samples
    except Exception:
        return np.zeros(AUDIO_SAMPLE_RATE, dtype=np.float32)


def compute_mel_spectrogram(audio: np.ndarray,
                              sr: int = AUDIO_SAMPLE_RATE,
                              n_mels: int = 64,
                              n_fft: int = 1024,
                              hop_length: int = 512) -> np.ndarray:
    """
    Compute a mel spectrogram from raw audio.
    Returns numpy array (n_mels, time_frames).
    Pure numpy — no librosa dependency required.
    """
    if len(audio) == 0:
        return np.zeros((n_mels, 32), dtype=np.float32)

    # STFT
    window = np.hanning(n_fft)
    n_frames = 1 + (len(audio) - n_fft) // hop_length
    if n_frames <= 0:
        audio = np.pad(audio, (0, n_fft))
        n_frames = 1

    stft = np.zeros((n_fft // 2 + 1, max(1, n_frames)), dtype=np.float32)
    for i in range(max(1, n_frames)):
        start = i * hop_length
        end   = start + n_fft
        chunk = audio[start:end] if end <= len(audio) else np.pad(audio[start:], (0, end - len(audio)))
        spectrum = np.abs(np.fft.rfft(chunk * window))
        stft[:, i] = spectrum

    # Mel filterbank
    mel_filters = _mel_filterbank(sr, n_fft, n_mels)
    mel_spec = np.dot(mel_filters, stft)
    mel_spec = np.log1p(mel_spec).astype(np.float32)
    return mel_spec


def _mel_filterbank(sr: int, n_fft: int, n_mels: int) -> np.ndarray:
    """Build triangular mel filterbank matrix."""
    f_min, f_max = 0.0, sr / 2.0
    def hz_to_mel(f): return 2595 * np.log10(1 + f / 700)
    def mel_to_hz(m): return 700 * (10 ** (m / 2595) - 1)

    mel_min = hz_to_mel(f_min)
    mel_max = hz_to_mel(f_max)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points  = mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    filters = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(1, n_mels + 1):
        f_m_minus = bin_points[m - 1]
        f_m       = bin_points[m]
        f_m_plus  = bin_points[m + 1]
        for k in range(f_m_minus, f_m):
            if f_m - f_m_minus > 0:
                filters[m - 1, k] = (k - f_m_minus) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            if f_m_plus - f_m > 0:
                filters[m - 1, k] = (f_m_plus - k) / (f_m_plus - f_m)
    return filters


def safe_transcribe(wav_path: str, whisper_model) -> tuple:
    """
    Transcribe audio with Whisper hallucination protection.

    Returns (transcript: str, speech_confidence: float).
    Returns ("", 0.0) when audio is silent or Whisper is not confident.

    Hallucination causes:
      - Near-silent audio  → Whisper invents plausible sentences
      - Short clips (<1 s) → insufficient signal, high no_speech_prob
      - Background noise   → misread as speech

    Fixes applied:
      1. RMS energy gate   — skip transcription if audio is near-silent
      2. temperature=0     — greedy decoding, no creative sampling
      3. condition_on_previous_text=False — stops hallucination chaining
      4. no_speech_prob    — discard segments where Whisper itself is unsure
      5. avg_no_speech     — discard entire result if mostly no-speech
    """
    import numpy as np

    # ── 1. Energy gate ────────────────────────────────────────
    try:
        audio = load_wav(wav_path)
        rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) else 0.0
        if rms < 0.005:          # near-silent — nothing to transcribe (0.005 = ~-46 dBFS)
            return "", 0.0
    except Exception:
        pass                     # if load fails, still attempt transcription

    # ── 2. Transcribe with hallucination-reducing settings ───
    try:
        result = whisper_model.transcribe(
            wav_path,
            language="en",                     # FIX: force English — without this Whisper auto-detects
                                               # language and transcribes noisy/unclear audio as Korean, Arabic, etc.
            condition_on_previous_text=False,  # prevents hallucination chaining
            temperature=0.0,                   # greedy — no creative sampling
            fp16=False,                        # avoid precision issues on CPU
        )
    except Exception as e:
        print(f"[safe_transcribe] Whisper error: {e}")
        return "", 0.0

    segments = result.get("segments", [])
    if not segments:
        return "", 0.0

    # ── 3. Filter per-segment by no_speech_prob ──────────────
    good_segments = [
        seg["text"] for seg in segments
        if seg.get("no_speech_prob", 0.0) < 0.80
    ]

    # ── 4. Discard if overall no-speech probability is high ──
    avg_no_speech = float(np.mean([
        seg.get("no_speech_prob", 0.0) for seg in segments
    ]))
    if avg_no_speech >= 0.75:
        return "", 0.0

    transcript = " ".join(good_segments).strip()
    speech_confidence = round(1.0 - avg_no_speech, 4)
    return transcript, speech_confidence


def record_microphone(duration: int = 5, sr: int = AUDIO_SAMPLE_RATE) -> str:
    """
    Record from the default microphone for `duration` seconds.
    Returns path to a temporary WAV file.
    Requires: sounddevice + soundfile, or pyaudio.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = tmp.name
    tmp.close()

    try:
        import sounddevice as sd
        import soundfile as sf
        audio = sd.rec(int(duration * sr), samplerate=sr,
                       channels=1, dtype='int16')
        sd.wait()
        sf.write(wav_path, audio, sr)
    except Exception:
        # Fallback: write silence so pipeline doesn't crash
        _write_silence(wav_path, duration)

    return wav_path
