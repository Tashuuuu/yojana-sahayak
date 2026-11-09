"""Create a blind human labelling sheet and private model-prediction file."""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences", default="results/eval_sentences.jsonl")
    parser.add_argument("--n", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    label_path = ROOT / "eval" / "sentence_labels.csv"
    prediction_path = ROOT / "results" / "_private_sentence_predictions.csv"
    if args.n < 1:
        parser.error("--n must be positive")
    if not args.force and (label_path.exists() or prediction_path.exists()):
        parser.error("Label files already exist. Use --force only when you intend to replace them.")

    records = [json.loads(line) for line in (ROOT / args.sentences).read_text(encoding="utf-8-sig").splitlines()
               if line.strip()]
    candidates = []
    for record in records:
        premise = " || ".join(f"[{chunk.get('chunk_id')}] {chunk.get('text')}" for chunk in record.get("chunks", []))
        for sentence in record.get("sentences", []):
            candidates.append({
                "qid": record.get("qid", ""), "sentence": sentence.get("text", ""),
                "premise": premise, "pred": sentence.get("label", ""),
                "entail": sentence.get("entail", 0.0), "contra": sentence.get("contra", 0.0),
            })
    if not candidates:
        raise SystemExit("No generated sentences. Run `python -m eval.run_eval` first.")

    rng = random.Random(args.seed)
    groups: dict[str, list[dict]] = {}
    for candidate in candidates:
        groups.setdefault(candidate["pred"], []).append(candidate)
    for group in groups.values():
        rng.shuffle(group)
    per_label = max(1, args.n // max(1, len(groups)))
    selected = []
    for group in groups.values():
        selected.extend(group[:per_label])
    remainder = [item for group in groups.values() for item in group[per_label:]]
    rng.shuffle(remainder)
    selected.extend(remainder[:max(0, args.n - len(selected))])
    rng.shuffle(selected)
    selected = selected[:args.n]
    for index, item in enumerate(selected, 1):
        item["sid"] = f"s{index:03d}"

    label_path.parent.mkdir(parents=True, exist_ok=True)
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    with label_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sid", "qid", "sentence", "premise", "label", "notes"])
        for item in selected:
            writer.writerow([item["sid"], item["qid"], item["sentence"], item["premise"], "", ""])
    with prediction_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sid", "pred_label", "entail", "contra"])
        for item in selected:
            writer.writerow([item["sid"], item["pred"], item["entail"], item["contra"]])
    print(f"Created {label_path}")
    print(f"Created private predictions at {prediction_path}; do not show these to the labeler.")
    print("Fill label with Supported / Unsupported / Contradicted. Leave unsure cases blank.")


if __name__ == "__main__":
    main()
