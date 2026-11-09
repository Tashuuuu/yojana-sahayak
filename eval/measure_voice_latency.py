"""Measure real Prisma/STT, retrieval, generation, NLI and Timbre/TTS latency."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")
from src.pipeline import answer_audio  # noqa: E402
from src.voice import speak  # noqa: E402


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 3) if values else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", default="assets/test_hi.wav")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--out", default="results/voice_latency.json")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    audio_path = ROOT / args.audio
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")
    wav_bytes = audio_path.read_bytes()
    consent = input(f"This runs {args.runs} real Prisma calls and {args.runs} Timbre calls. Type YES: ")
    if consent.strip() != "YES":
        print("Cancelled; no API calls made.")
        return

    keys = ("stt", "retrieve", "generate", "verify", "tts", "end_to_end_voice")
    measurements: dict[str, list[float]] = {key: [] for key in keys}
    for run_number in range(1, args.runs + 1):
        total_start = time.perf_counter()
        result = answer_audio(wav_bytes, make_audio=False)
        tts_start = time.perf_counter()
        speak(result["spoken_text"], result["lang"], use_cache=False)
        tts_seconds = time.perf_counter() - tts_start
        for key in ("stt", "retrieve", "generate", "verify"):
            if key in result["latency"]:
                measurements[key].append(float(result["latency"][key]))
        measurements["tts"].append(tts_seconds)
        measurements["end_to_end_voice"].append(time.perf_counter() - total_start)
        print(f"[{run_number}/{args.runs}] {result['status']} — {measurements['end_to_end_voice'][-1]:.2f}s")

    report = {
        "runs": args.runs,
        "audio_file": str(audio_path.relative_to(ROOT)),
        "stt_model": "Gnani Prisma v3.0 (Prisma v2.5 fallback only if v3 model is unavailable)",
        "tts_model": "Gnani Timbre v2.5",
        "median_seconds": {key: median(values) for key, values in measurements.items()},
        "raw_seconds": measurements,
        "note": "Real API calls; TTS cache bypassed for latency measurement.",
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
