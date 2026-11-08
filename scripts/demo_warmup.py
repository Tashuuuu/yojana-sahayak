# scripts/demo_warmup.py — rehearse the demo questions BEFORE recording.
# It loads the models once (so the first recording take is not slow), prints each answer,
# and saves the spoken answer audio to assets/demo_audio/ (real text-to-speech, fractions of a credit each).
# Usage (repo root):  python scripts/demo_warmup.py            (with speech)
#                     python scripts/demo_warmup.py --no-speak (answers only, no speech credits)
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from src.pipeline import answer_question  # noqa: E402
from src.voice import speak  # noqa: E402

# EDIT THIS LIST: your exact demo questions. Include one the system should refuse.
DEMO_QUESTIONS = [
    ("पीएम किसान में कौन आवेदन कर सकता है?", "hi"),
    ("What documents are needed for Ayushman Bharat?", "en"),
    ("अगली किस्त कब आएगी?", "hi"),   # should be refused
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-speak", action="store_true")
    args = ap.parse_args()

    print("DRY_RUN =", os.getenv("DRY_RUN", "0"), "(1 means fake answers and silent audio)")
    out_dir = ROOT / "assets" / "demo_audio"
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, (question, lang) in enumerate(DEMO_QUESTIONS, start=1):
        t0 = time.perf_counter()
        r = answer_question(question, lang)
        text_seconds = time.perf_counter() - t0
        print(f"\n[{i}] {question}")
        print(f"    status={r['status']}  groundedness={r['verification']['groundedness']}  "
              f"retrieval={r['retrieval_source']}  text pipeline={text_seconds:.1f}s")
        for s in r["verification"]["sentences"]:
            print(f"    - {s['label']:<12} {s['text']}")
        print(f"    spoken: {r['spoken_text']}")
        if not args.no_speak:
            t0 = time.perf_counter()
            audio = speak(r["spoken_text"], lang)
            (out_dir / f"demo_{i}_{lang}_{r['status']}.wav").write_bytes(audio)
            print(f"    saved audio ({len(audio)} bytes, {time.perf_counter() - t0:.1f}s)")
    print("\nWarm-up done. If any answer looks wrong, fix it BEFORE you record.")


if __name__ == "__main__":
    main()