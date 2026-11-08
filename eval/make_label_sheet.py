# eval/make_label_sheet.py — pick ~60 answer sentences for Bhawna to label BLIND (without seeing the model's label).
# Usage (repo root):  python eval/make_label_sheet.py --n 60
import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentences", default="results/eval_sentences.jsonl")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    items = []
    for rec in load_jsonl(ROOT / args.sentences):
        premise = " || ".join(f"[{c['chunk_id']}] {c['text']}" for c in rec["chunks"])
        for s in rec["sentences"]:
            items.append({"qid": rec["qid"], "sentence": s["text"], "premise": premise,
                          "pred": s["label"], "entail": s["entail"], "contra": s["contra"]})
    if not items:
        sys.exit("No sentences found. Run eval/run_eval.py first (with DRY_RUN=0 and real retrieval).")

    rng = random.Random(args.seed)
    groups = {}
    for it in items:
        groups.setdefault(it["pred"], []).append(it)
    for g in groups.values():
        rng.shuffle(g)

    quota = max(1, args.n // max(1, len(groups)))
    chosen = []
    for g in groups.values():
        chosen += g[:quota]
    rest = [it for g in groups.values() for it in g[quota:]]
    rng.shuffle(rest)
    chosen += rest[: max(0, args.n - len(chosen))]
    rng.shuffle(chosen)  # so the order does not reveal the predicted label
    chosen = chosen[: args.n]

    for i, it in enumerate(chosen, start=1):
        it["sid"] = f"s{i:03d}"

    template = ROOT / "eval" / "sentence_labels_template.csv"
    with open(template, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["sid", "qid", "sentence", "premise", "label", "notes"])
        for it in chosen:
            w.writerow([it["sid"], it["qid"], it["sentence"], it["premise"], "", ""])

    private = ROOT / "results" / "_private_sentence_predictions.csv"
    with open(private, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["sid", "pred_label", "entail", "contra"])
        for it in chosen:
            w.writerow([it["sid"], it["pred"], it["entail"], it["contra"]])

    counts = {k: sum(1 for it in chosen if it["pred"] == k) for k in groups}
    print(f"Wrote {len(chosen)} sentences to {template}")
    print(f"Predictions (keep private until labelling is finished): {private}")
    print("Sampled by predicted label:", counts)


if __name__ == "__main__":
    main()