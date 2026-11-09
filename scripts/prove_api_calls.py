"""Proves the app really reaches Gnani + Groq. Run: python scripts/prove_api_calls.py
Spends ~1 STT call + ~1 TTS call (a few credits)."""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

print("DRY_RUN =", repr(os.getenv("DRY_RUN")), "(must be '0')")
if os.getenv("DRY_RUN", "0").strip() == "1":
    sys.exit("FAIL: DRY_RUN is 1. Open .env, set DRY_RUN=0, save, rerun.")
for k in ("GNANI_STT_API_KEY", "GNANI_TTS_API_KEY", "GROQ_API_KEY"):
    v = os.getenv(k, "")
    print(f"{k}:", "OK" if v and "your_" not in v else "MISSING / still placeholder")

from src.voice import speak, transcribe, read_call_log
wav = ROOT / "assets" / "test_hi.wav"
print("\n1) Prisma STT ...")
r = transcribe(wav.read_bytes(), keyterms=["PM-KISAN", "पीएम किसान"])
print("   transcript:", r["text"], "| request_id:", r["request_id"])
print("2) Timbre TTS (cache bypassed) ...")
audio = speak("पीएम किसान योजना में किसानों को सालाना छह हजार रुपये मिलते हैं।", "hi", use_cache=False)
(ROOT / "assets" / "test_out.wav").write_bytes(audio)
print("   wrote assets/test_out.wav", len(audio), "bytes")
print("3) Groq LLM ...")
from src.generate import _ask
print("   ", _ask("Reply with one short word.", "Say OK")[:40])
print("\nLogged real Gnani calls:", *read_call_log(), sep="\n  ")
print("\nNow check your Gnani dashboard: credits must have dropped.")
