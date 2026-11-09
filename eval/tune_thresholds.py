"""Tune NLI thresholds on a dev split and evaluate the held-out test split once."""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ["Supported", "Unsupported", "Contradicted"]
_NORMALIZE = {value.casefold(): value for value in LABELS}
DEFAULT_T_ENT = 0.60
DEFAULT_T_CON = 0.50


def predict(entail: float, contra: float, t_ent: float, t_con: float) -> str:
    if entail >= t_ent:
        return "Supported"
    return "Contradicted" if contra >= t_con else "Unsupported"


def load_data(labels_path: Path, predictions_path: Path) -> list[dict]:
    labels = {}
    with labels_path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            label = _NORMALIZE.get((row.get("label") or "").strip().casefold())
            if label:
                labels[row["sid"].strip()] = label
    result = []
    with predictions_path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            sid = row["sid"].strip()
            if sid in labels:
                result.append({"sid": sid, "true": labels[sid],
                               "entail": float(row["entail"]), "contra": float(row["contra"])})
    return result


def split_dev_test(data: list[dict], seed: int = 42):
    rng = random.Random(seed)
    dev, test = [], []
    for label in LABELS:
        group = sorted((item for item in data if item["true"] == label), key=lambda item: item["sid"])
        rng.shuffle(group)
        split = (len(group) + 1) // 2
        dev.extend(group[:split])
        test.extend(group[split:])
    return dev, test


def flag_metrics(data: list[dict], t_ent: float, t_con: float) -> dict:
    tp = fp = fn = tn = 0
    for item in data:
        predicted_flag = predict(item["entail"], item["contra"], t_ent, t_con) != "Supported"
        true_flag = item["true"] != "Supported"
        if predicted_flag and true_flag:
            tp += 1
        elif predicted_flag:
            fp += 1
        elif true_flag:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def three_class(data: list[dict], t_ent: float, t_con: float) -> dict:
    matrix = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    for item in data:
        predicted = predict(item["entail"], item["contra"], t_ent, t_con)
        matrix[item["true"]][predicted] += 1
    correct = sum(matrix[label][label] for label in LABELS)
    return {"accuracy": round(correct / len(data), 3) if data else 0.0,
            "confusion_true_by_pred": matrix}


def tune(dev: list[dict]) -> dict:
    if not dev:
        raise ValueError("No development labels available")
    entail_grid = [round(value * 0.05, 2) for value in range(6, 20)]
    scored = [(threshold, flag_metrics(dev, threshold, DEFAULT_T_CON)) for threshold in entail_grid]
    best = max((metrics["f1"], metrics["recall"]) for _, metrics in scored)
    tied = [(threshold, metrics) for threshold, metrics in scored
            if (metrics["f1"], metrics["recall"]) == best]
    t_ent, dev_flag = tied[len(tied) // 2]
    contra_grid = [round(value * 0.05, 2) for value in range(4, 19)]
    scored_contra = [(threshold, three_class(dev, t_ent, threshold)["accuracy"])
                     for threshold in contra_grid]
    best_accuracy = max(score for _, score in scored_contra)
    tied_contra = [threshold for threshold, score in scored_contra if score == best_accuracy]
    t_con = tied_contra[len(tied_contra) // 2]
    return {"T_ENT": t_ent, "T_CON": t_con, "dev_flag_metrics": dev_flag,
            "dev_three_class": three_class(dev, t_ent, t_con)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["tune", "test"])
    parser.add_argument("--labels", default="eval/sentence_labels.csv")
    parser.add_argument("--preds", default="results/_private_sentence_predictions.csv")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    data = load_data(ROOT / args.labels, ROOT / args.preds)
    if len(data) < 40:
        print(f"WARNING: only {len(data)} labelled sentences; report this limitation.")
    dev, test = split_dev_test(data, args.seed)
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    chosen_path = out_dir / "chosen_thresholds.json"
    if args.command == "tune":
        selected = tune(dev)
        selected.update({"seed": args.seed, "n_labelled": len(data), "dev_n": len(dev), "test_n": len(test)})
        chosen_path.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(selected, ensure_ascii=False, indent=2))
        print(f"Set T_ENT={selected['T_ENT']} and T_CON={selected['T_CON']} in .env, then restart the app.")
        print("After applying those dev-only thresholds, run `python -m eval.tune_thresholds test` once.")
        return
    lock = out_dir / "test_evaluated.lock"
    if not chosen_path.exists():
        raise SystemExit("Run `python -m eval.tune_thresholds tune` first")
    if lock.exists() and not args.force:
        raise SystemExit("Held-out test was already evaluated. Do not tune against the test split.")
    selected = json.loads(chosen_path.read_text(encoding="utf-8"))
    t_ent, t_con = float(selected["T_ENT"]), float(selected["T_CON"])
    report = {
        "n_test": len(test), "T_ENT": t_ent, "T_CON": t_con,
        "tuned_flag_metrics": flag_metrics(test, t_ent, t_con),
        "tuned_three_class": three_class(test, t_ent, t_con),
        "default_thresholds_flag_metrics": flag_metrics(test, DEFAULT_T_ENT, DEFAULT_T_CON),
    }
    (out_dir / "verifier_test_metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lock.write_text("held-out verifier test evaluated once\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
