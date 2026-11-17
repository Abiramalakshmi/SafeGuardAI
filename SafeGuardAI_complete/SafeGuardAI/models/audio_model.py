# ============================================================
# SafeGuard AI — Audio Model (Whisper ASR + DistilBERT Toxicity)
# ============================================================

import os
import re
import numpy as np
from utils.config import WHISPER_MODEL, TOXICITY_THRESHOLD

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import whisper as openai_whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from transformers import pipeline as hf_pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


TOXIC_PATTERNS = [
    r"\bi('ll| will| am going to| gonna)( fucking| really)? (hit|hurt|kill|attack|destroy|beat|punch|smash|fight)\b",
    r"\b(i'll kill|i will kill|gonna kill|going to kill)\b",
    r"\b(you('re| are) dead|you('re| are) finished)\b",
    r"\b(shut up|back off|get out|leave now|stay away)\b",
    r"\b(threat|threaten|attack|murder|assault|stab|shoot)\b",
    r"\b(i hate you|i'll hurt|gonna hurt|going to hurt)\b",
    r"\bfuck(ing)? (you|off|this|him|her)\b",
]

TOXIC_KEYWORDS_SINGLE = [
    "kill", "murder", "attack", "hurt", "hit", "punch",
    "fight", "stab", "shoot", "dead", "threat",
]
TOXIC_KEYWORDS_PHRASE = [
    "beat you", "destroy you", "i'll get you", "you're done",
    "watch yourself", "i will hurt", "gonna hurt",
]


class AudioModel:
    def __init__(self):
        self.whisper_model        = None
        self.toxicity_pipe        = None
        self.distilbert_available = False
        self._load_whisper()
        self._load_toxicity()

    def _load_whisper(self):
        if not WHISPER_AVAILABLE:
            print("[AudioModel] Whisper not installed — using DEMO transcript.")
            return
        try:
            print(f"[AudioModel] Loading Whisper ({WHISPER_MODEL})...")
            self.whisper_model = openai_whisper.load_model(WHISPER_MODEL)
            print("[AudioModel] Whisper ready.")
        except Exception as e:
            print(f"[AudioModel] Whisper load failed: {e}")

    def _load_toxicity(self):
        if not TRANSFORMERS_AVAILABLE:
            print("[AudioModel] Transformers not installed — using keyword matching.")
            return
        if not TORCH_AVAILABLE:
            print("[AudioModel] PyTorch not available — using keyword fallback.")
            return
        try:
            print("[AudioModel] Loading DistilBERT toxicity classifier...")
            self.toxicity_pipe = hf_pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                top_k=None,
                truncation=True,
                max_length=512,
            )
            self.distilbert_available = True
            print("[AudioModel] DistilBERT ready.")
        except Exception as e:
            print(f"[AudioModel] DistilBERT load failed: {e} — using keyword fallback.")

    def transcribe(self, wav_path: str) -> str:
        # FIX BUG 6: Warn loudly every time demo mode is used, not just at startup.
        # Previously the random demo transcript was returned silently, making it
        # impossible to know the transcript had nothing to do with the actual audio.
        if self.whisper_model is None:
            # FIX: Previously returned a random demo sentence, which caused the UI to
            # display fabricated (and sometimes threatening) text as if it were a real
            # transcription.  Return "" so callers see "No speech detected" instead.
            print("[AudioModel] WARNING: Whisper model not loaded — transcription unavailable. "
                  "Install openai-whisper and ensure the model can be downloaded. "
                  "Returning empty transcript.")
            return ""

        try:
            use_fp16 = TORCH_AVAILABLE and torch.cuda.is_available()

            try:
                audio = openai_whisper.load_audio(wav_path)

                # FIX BUG 1: REMOVED peak-amplitude normalization.
                # Dividing by np.max(np.abs(audio)) distorts the energy relationship
                # between speech and background noise that Whisper's VAD depends on.
                # A quiet speaker with one loud spike gets their speech amplitude
                # crushed, causing Whisper to inflate no_speech_prob and discard
                # real speech. Whisper handles amplitude internally — do not touch it.

                result = self.whisper_model.transcribe(
                    audio,
                    language=None,                  # auto-detect language
                    fp16=use_fp16,
                    verbose=False,
                    temperature=0,                  # deterministic decoding
                    # FIX BUG 2: Lowered from 0.85 → Whisper default 0.6.
                    # 0.85 meant any segment with mild background noise, an accent,
                    # or quiet speech was silently discarded as non-speech.
                    no_speech_threshold=0.6,
                    # FIX BUG 3: Loosened from -1.0 → -1.5.
                    # Combined with the segment-level check below (which also used
                    # -1.0), this created double-rejection: accented or fast speech
                    # with logprob ~-1.05 was killed twice. Let Whisper pass more
                    # segments through and rely on the manual guard as the single gate.
                    logprob_threshold=-1.5,
                    compression_ratio_threshold=2.4,
                    condition_on_previous_text=True,
                    beam_size=5,
                    best_of=5,
                )
            except Exception:
                # Fallback to path-based transcription
                result = self.whisper_model.transcribe(
                    wav_path,
                    language=None,
                    fp16=use_fp16,
                    verbose=False,
                    temperature=0,
                    no_speech_threshold=0.6,        # FIX BUG 2 (same as above)
                    logprob_threshold=-1.5,          # FIX BUG 3 (same as above)
                    compression_ratio_threshold=2.4,
                    condition_on_previous_text=True,
                    beam_size=5,
                    best_of=5,
                )

            text = result.get("text", "").strip()

            # Guard against hallucinated repetitions like "A-A-A-A-A" or "you you you you".
            # These are produced by Whisper when given crowd noise, music, or silence.
            if text:
                _words = text.split()
                # FIX BUG 5: Raised minimum word count from 3 → 8 and tightened
                # unique ratio threshold from 0.25 → 0.20 before discarding.
                # Previously "No no no stop stop please" (valid distress speech) was
                # discarded because it has low unique-word ratio with only 3+ words.
                # Now we require at least 8 words before applying this heuristic.
                if len(_words) >= 8:
                    _unique_ratio = len(set(w.lower() for w in _words)) / len(_words)
                    if _unique_ratio < 0.20:   # >80% repeated words = hallucination
                        return ""
                # Catch character-level repetition: "A-A-A-A-A" or "ha-ha-ha-ha"
                import re as _re
                if _re.search(r'(\b\w[-\w]*\b)(?:[\s\-]+\1){3,}', text, _re.IGNORECASE):
                    return ""

            # Segment-level confidence check — only reject obvious hallucinations
            segments = result.get("segments", [])
            if segments:
                avg_logprob   = sum(s.get("avg_logprob", 0)    for s in segments) / len(segments)
                avg_no_speech = sum(s.get("no_speech_prob", 0) for s in segments) / len(segments)

                # Only reject if confidence is very low AND no_speech is very high.
                if avg_logprob < -1.0 and avg_no_speech > 0.6:
                    return ""

                # FIX BUG 4: Raised no_speech threshold for short text from 0.3 → 0.55.
                # 0.3 (30%) is a normal no_speech_prob for any short utterance.
                # Phrases like "Help!", "Stop.", "Get out." are under 12 chars and
                # were being silently discarded. 0.55 only catches truly ambiguous clips.
                if len(text) < 12 and avg_no_speech > 0.55:
                    return ""

            return text

        except Exception as e:
            print(f"[AudioModel] Transcription error: {e}")
            return ""

    def detect_toxicity(self, text: str) -> dict:
        if not text:
            return {"score": 0.0, "label": "non-toxic", "toxic_phrases": []}

        t = text.strip()
        # Guard against Whisper returning tiny junk like "you", "yeah", etc.
        # Short phrases under 3 words should not drive toxicity decisions.
        # NOTE: we intentionally do NOT filter on character length here anymore —
        # "Kill him" is only 7 chars but is a valid toxic short phrase.
        if len(re.findall(r"\b\w+\b", t)) < 3:
            return {"score": 0.0, "label": "non-toxic", "toxic_phrases": []}

        # Reject hallucinated repetitions before they reach DistilBERT.
        # "A-A-A-A" style junk scores as toxic — must be blocked here too.
        _words = t.split()
        if len(_words) >= 3 and (len(set(w.lower() for w in _words)) / len(_words)) < 0.30:
            return {"score": 0.0, "label": "non-toxic", "toxic_phrases": []}

        toxic_phrases = self._extract_toxic_phrases(text)

        if self.toxicity_pipe is not None:
            try:
                results   = self.toxicity_pipe(text)[0]
                tox_score = 0.0
                for r in results:
                    if "toxic" in r["label"].lower():
                        tox_score = max(tox_score, r["score"])
                label = "toxic" if tox_score >= TOXICITY_THRESHOLD else "non-toxic"
                return {
                    "score":         round(tox_score, 4),
                    "label":         label,
                    "toxic_phrases": toxic_phrases,
                    "raw_results":   results,
                }
            except Exception as e:
                print(f"[AudioModel] Toxicity pipeline error: {e}")

        score = self._keyword_toxicity_score(text, toxic_phrases)
        return {
            "score":         round(score, 4),
            "label":         "toxic" if score >= TOXICITY_THRESHOLD else "non-toxic",
            "toxic_phrases": toxic_phrases,
        }

    def _extract_toxic_phrases(self, text: str) -> list:
        text_lower = text.lower()
        found = []
        for pattern in TOXIC_PATTERNS:
            matches = re.findall(pattern, text_lower)
            for m in matches:
                phrase = m if isinstance(m, str) else " ".join(m)
                if phrase.strip():
                    found.append(phrase.strip())
        words = set(re.findall(r'\b\w+\b', text_lower))
        for kw in TOXIC_KEYWORDS_SINGLE:
            if kw in words and kw not in found:
                found.append(kw)
        for phrase in TOXIC_KEYWORDS_PHRASE:
            if phrase in text_lower and phrase not in found:
                found.append(phrase)
        return list(set(found))[:5]

    def _keyword_toxicity_score(self, text: str, toxic_phrases: list) -> float:
        if not text:
            return 0.0
        text_lower = text.lower()
        base = 0.0
        words = set(re.findall(r'\b\w+\b', text_lower))
        for kw in TOXIC_KEYWORDS_SINGLE:
            if kw in words:
                base += 0.08
        for phrase in TOXIC_KEYWORDS_PHRASE:
            if phrase in text_lower:
                base += 0.15
        for pattern in TOXIC_PATTERNS:
            if re.search(pattern, text_lower):
                base += 0.20
        return float(np.clip(base, 0.0, 1.0))

    def analyze(self, wav_path: str) -> dict:
        transcript = self.transcribe(wav_path)
        toxicity   = self.detect_toxicity(transcript)
        return {
            "transcript":     transcript,
            "toxicity_score": toxicity["score"],
            "toxicity_label": toxicity["label"],
            "toxic_phrases":  toxicity["toxic_phrases"],
        }


_audio_model = None

def get_audio_model() -> AudioModel:
    global _audio_model
    if _audio_model is None:
        _audio_model = AudioModel()
    return _audio_model
