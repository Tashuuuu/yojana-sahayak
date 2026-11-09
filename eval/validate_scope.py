"""Check whether the local scheme corpus and evaluation set meet the stated synopsis targets."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "schemes.jsonl"
QUESTIONS = ROOT / "eval" / "eval_questions.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mvs", action="store_true", help="check the synopsis minimum viable scope of at least 12 schemes")
    args = parser.parse_args()
    records = read_jsonl(DATA)
    questions = read_jsonl(QUESTIONS)
    languages: dict[str, set[str]] = defaultdict(set)
    for record in records:
        languages[str(record.get("scheme_id", ""))].add(str(record.get("lang", "")).lower()[:2])
    schemes = {key for key in languages if key}
    fully_bilingual = {key for key, values in languages.items() if {"en", "hi"} <= values}
    answerable = [item for item in questions if item.get("answerable") is True]
    unanswerable = [item for item in questions if item.get("answerable") is False]
    required_schemes = 12 if args.mvs else 20
    checks = [
        (len(schemes) >= required_schemes, f"unique schemes: {len(schemes)} (required {required_schemes})"),
        (len(fully_bilingual) >= required_schemes,
         f"bilingual schemes: {len(fully_bilingual)} (required {required_schemes})"),
        (len(questions) == 40, f"evaluation questions: {len(questions)} (required 40)"),
        (len(answerable) == 30, f"answerable questions: {len(answerable)} (required 30)"),
        (len(unanswerable) == 10, f"unanswerable questions: {len(unanswerable)} (required 10)"),
        (all(item.get("gold_scheme_id") and item.get("gold_section") and item.get("reference_answer")
             for item in answerable), "every answerable question has gold_scheme_id, gold_section and reference_answer"),
    ]
    print("Yojana Sahayak scope validation")
    for passed, description in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {description}")
    if not records:
        print("FAIL: data/schemes.jsonl is missing or empty")
    print(f"\nUnique schemes present: {', '.join(sorted(schemes)) or 'none'}")
    print(f"Bilingual schemes present: {', '.join(sorted(fully_bilingual)) or 'none'}")
    if not all(passed for passed, _ in checks) or not records:
        raise SystemExit(1)
    print("\nAll requested data/evaluation scope checks passed.")


if __name__ == "__main__":
    main()
