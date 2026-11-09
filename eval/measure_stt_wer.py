"""Optional Prisma keyterms WER comparison (20 utterances, 40 real STT calls)."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")
from jiwer import wer  # noqa: E402
from src.pipeline import load_scheme_keyterms  # noqa: E402
from src.voice import transcribe  # noqa: E402


def normalize(text: str) -> str:
    text = (text or "").casefold()
    text = re.sub(r"[^\w\u0900-\u097f\s]", " ", text)
    return " ".join(text.split())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="eval/stt_utterances.csv")
    parser.add_argument("--out", default="results/stt_wer.json")
    args = parser.parse_args()
    source = ROOT / args.input
    if not source.exists():
        raise SystemExit(f"Create {source} from eval/stt_utterances_template.csv first.")
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("audio_path") and row.get("reference_text")]
    if not rows:
        raise SystemExit("No audio_path/reference_text rows were provided.")
    if len(rows) != 20:
        print(f"WARNING: the stretch test calls for 20 utterances; found {len(rows)}.")
    terms = load_scheme_keyterms()
    consent = input(f"This makes {2 * len(rows)} real Prisma API calls. Type YES: ")
    if consent.strip() != "YES":
        print("Cancelled; no API calls made.")
        return

    refs, no_terms, with_terms = [], [], []
    for index, row in enumerate(rows, 1):
        audio_path = ROOT / row["audio_path"]
        if not audio_path.exists():
            raise SystemExit(f"Missing WAV: {audio_path}")
        wav = audio_path.read_bytes()
        result_without = transcribe(wav, keyterms=None)
        result_with = transcribe(wav, keyterms=terms)
        refs.append(normalize(row["reference_text"]))
        no_terms.append(normalize(result_without["text"]))
        with_terms.append(normalize(result_with["text"]))
        print(f"[{index}/{len(rows)}] tested {row['audio_path']}")

    report = {
        "n_files": len(rows),
        "wer_without_keyterms": round(float(wer(refs, no_terms)), 4),
        "wer_with_keyterms": round(float(wer(refs, with_terms)), 4),
        "references": refs,
        "hypotheses_without_keyterms": no_terms,
        "hypotheses_with_keyterms": with_terms,
        "note": "Prisma v3.0 real API calls; lower WER is better. Report measured values even if keyterms do not help.",
    }
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
