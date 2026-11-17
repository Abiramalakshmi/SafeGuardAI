import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Test 1: Check which audio_model.py is actually loaded ──
import models.audio_model as am_module
print("audio_model.py path:", am_module.__file__)

# Check if the fix is present
with open(am_module.__file__, encoding="utf-8") as f:
    src = f.read()
    has_fix = "condition_on_previous_text" in src
    print("Hallucination fix present:", has_fix)

# ── Test 2: Transcribe a test file ──
import glob
wav_files = glob.glob("uploads/*.wav") + glob.glob("uploads/*.mp4") + \
            glob.glob("recordings/*.wav") + glob.glob("recordings/*.mp4")

if not wav_files:
    print("\nNo audio files found in uploads/ or recordings/")
    print("Please upload a file first, then re-run this script")
    sys.exit(0)

print(f"\nFound test files: {wav_files[:3]}")
test_file = wav_files[0]
print(f"Testing with: {test_file}")

from models.audio_model import get_audio_model
am = get_audio_model()

print("\n── Raw Whisper result ──")
import torch
use_fp16 = torch.cuda.is_available()
result = am.whisper_model.transcribe(
    test_file,
    language="en",
    fp16=use_fp16,
    verbose=True,
    temperature=0,
    no_speech_threshold=0.6,
    logprob_threshold=-1.0,
    compression_ratio_threshold=2.4,
    condition_on_previous_text=False,
)
print("Text:", result.get("text",""))
segs = result.get("segments", [])
for s in segs:
    print(f"  [{s.get('start',0):.1f}s-{s.get('end',0):.1f}s] "
          f"logprob={s.get('avg_logprob',0):.3f} "
          f"no_speech={s.get('no_speech_prob',0):.3f} "
          f"text='{s.get('text','').strip()}'")

print("\n── Full analyze() result ──")
r = am.analyze(test_file)
print("Transcript   :", r["transcript"])
print("Toxicity     :", r["toxicity_score"])
print("Toxic phrases:", r["toxic_phrases"])
