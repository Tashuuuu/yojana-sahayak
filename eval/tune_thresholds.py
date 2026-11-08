# eval/tune_thresholds.py — choose the verifier thresholds on DEV labels only, then score TEST once.
# Usage (repo root):
#   python eval/tune_thresholds.py tune     # uses the dev half only
#   python eval/tune_thresholds.py test     # scores the test half ONCE (writes a lock file)
import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ["Supported", "Unsupported", "Contradicted"]
NORMALISE = {"supported": "Supported", "unsupported": "Unsupported", "contradicted": "Contradicted"}
DEFAULT_T_ENT, DEFAULT_T_CON = 0.60, 0.50


def predict(entail: float, contra: float, t_ent: float, t_con: float) -> str:
    if entail >= t_ent:
        return "Supported"
    return "Contradicted" if contra >= t_con else "Unsupported"


def load_data(labels_path: Path, preds_path: Path) -> list[dict]:
    labels = {}
    with open(labels_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            lab = NORMALISE.get((row.get("label") or "").strip().lower())
            if lab:  # rows marked 'unsure' or left blank are skipped
                labels[row["sid"].strip()] = lab
    data = []
    with open(preds_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sid = row["sid"].strip()
            if sid in labels:
                data.append({"sid": sid, "true": labels[sid],
                             "entail": float(row["entail"]), "contra": float(row["contra"])})
    return data


def split_dev_test(data: list[dict], seed: int = 42):
    """Split each true label roughly in half, with a fixed seed, so dev and test never overlap."""
    rng = random.Random(seed)
    dev, test = [], []
    for label in LABELS:
        group = sorted((d for d in data if d["true"] == label), key=lambda d: d["sid"])
        rng.shuffle(group)
        half = (len(group) + 1) // 2
        dev += group[:half]
        test += group[half:]
    return dev, test


def flag_metrics(data: list[dict], t_ent: float, t_con: float) -> dict:
    """Treat 'not Supported' as the positive class (the sentences we want to catch)."""
    tp = fp = fn = tn = 0
    for d in data:
        pred_flag = predict(d["entail"], d["contra"], t_ent, t_con) != "Supported"
        true_flag = d["true"] != "Supported"
        if pred_flag and true_flag:
            tp += 1
        elif pred_flag and not true_flag:
            fp += 1
        elif not pred_flag and true_flag:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(precision, 3),
            "recall": round(recall, 3), "f1": round(f1, 3)}


def three_class(data: list[dict], t_ent: float, t_con: float) -> dict:
    confusion = {t: {p: 0 for p in LABELS} for t in LABELS}
    correct = 0
    for d in data:
        pred = predict(d["entail"], d["contra"], t_ent, t_con)
        confusion[d["true"]][pred] += 1
        correct += pred == d["true"]
    return {"accuracy": round(correct / len(data), 3) if data else 0.0, "confusion_true_by_pred": confusion}


def tune(dev: list[dict]) -> dict:
    """Pick the thresholds on DEV only. If several thresholds tie for best, take the middle one
    (a threshold in the middle of a plateau is less brittle than one at its edge)."""
    grid_ent = [round(x * 0.05, 2) for x in range(6, 20)]   # 0.30 ... 0.95
    scored = [(t, flag_metrics(dev, t, DEFAULT_T_CON)) for t in grid_ent]
    best_key = max((m["f1"], m["recall"]) for _, m in scored)
    ties = [(t, m) for t, m in scored if (m["f1"], m["recall"]) == best_key]
    t_ent, m_ent = ties[len(ties) // 2]

    grid_con = [round(x * 0.05, 2) for x in range(4, 19)]   # 0.20 ... 0.90
    acc = [(t, three_class(dev, t_ent, t)["accuracy"]) for t in grid_con]
    best_acc = max(a for _, a in acc)
    ties_con = [t for t, a in acc if a == best_acc]
    t_con = ties_con[len(ties_con) // 2]
    return {"T_ENT": t_ent, "T_CON": t_con, "dev_flag_metrics": m_ent}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["tune", "test"])
    ap.add_argument("--labels", default="eval/sentence_labels.csv")
    ap.add_argument("--preds", default="results/_private_sentence_predictions.csv")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--force", action="store_true", help="allow scoring the test half again (do not do this)")
    args = ap.parse_args()

    data = load_data(ROOT / args.labels, ROOT / args.preds)
    dev, test = split_dev_test(data, args.seed)
    print(f"Usable labelled sentences: {len(data)}  (dev {len(dev)}, test {len(test)})")
    if len(data) < 40:
        print("WARNING: very few labels, so every number below is noisy. Say so in the README.")
    (ROOT / "results").mkdir(exist_ok=True)
    chosen_path = ROOT / "results" / "chosen_thresholds.json"

    if args.command == "tune":
        chosen = tune(dev)
        chosen.update({"seed": args.seed, "dev_n": len(dev)})
        chosen["dev_three_class"] = three_class(dev, chosen["T_ENT"], chosen["T_CON"])
        chosen_path.write_text(json.dumps(chosen, indent=2), encoding="utf-8")
        print("\nChosen on DEV only:")
        print(json.dumps(chosen, indent=2))
        print(f"\nNext: set T_ENT={chosen['T_ENT']} and T_CON={chosen['T_CON']} in src/verify.py, "
              f"then run:  python eval/tune_thresholds.py test")
        return

    if not chosen_path.exists():
        sys.exit("Run 'tune' first.")
    lock = ROOT / "results" / "test_evaluated.lock"
    if lock.exists() and not args.force:
        sys.exit("The test half was already scored once. Re-scoring it would be tuning on test. Stop here.")
    chosen = json.loads(chosen_path.read_text(encoding="utf-8"))
    t_ent, t_con = chosen["T_ENT"], chosen["T_CON"]
    result = {
        "n_test": len(test), "T_ENT": t_ent, "T_CON": t_con,
        "tuned_flag_metrics": flag_metrics(test, t_ent, t_con),
        "tuned_three_class": three_class(test, t_ent, t_con),
        "default_thresholds_flag_metrics": flag_metrics(test, DEFAULT_T_ENT, DEFAULT_T_CON),
    }
    (ROOT / "results" / "verifier_test_metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    t = result["tuned_flag_metrics"]
    d = result["default_thresholds_flag_metrics"]
    md = (
        "# Verifier evaluation (held-out test half)\n\n"
        f"Test sentences: {len(test)}. Thresholds were chosen on the dev half only (seed {args.seed}).\n\n"
        "| Setting | T_ENT | T_CON | Precision | Recall | F1 |\n|---|---|---|---|---|---|\n"
        f"| Tuned on dev | {t_ent} | {t_con} | {t['precision']} | {t['recall']} | {t['f1']} |\n"
        f"| Default | {DEFAULT_T_ENT} | {DEFAULT_T_CON} | {d['precision']} | {d['recall']} | {d['f1']} |\n\n"
        "Positive class = a sentence that is NOT Supported (Unsupported or Contradicted).\n"
        f"Three-class accuracy on test: {result['tuned_three_class']['accuracy']}\n"
    )
    (ROOT / "results" / "verifier_eval.md").write_text(md, encoding="utf-8")
    lock.write_text("test half scored once\n", encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()