"""Build a submission results summary only from measured result files."""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def read_json(name: str):
    path = RESULTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def display(value) -> str:
    return "n/a" if value is None else str(value)


def percent(value) -> str:
    return "n/a" if value is None else f"{round(float(value) * 100, 1)}%"


def correctness():
    path = RESULTS / "correctness.csv"
    if not path.exists():
        return None
    scores = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                score = int(row.get("score", ""))
                if score in {0, 1, 2}:
                    scores.append(score)
            except (TypeError, ValueError):
                pass
    if not scores:
        return None
    return {"n": len(scores), "mean": round(statistics.mean(scores), 2),
            "at_least_1": sum(score >= 1 for score in scores) / len(scores)}


def main() -> None:
    metrics = read_json("eval_metrics.json") or {}
    verifier = read_json("verifier_test_metrics.json")
    stt = read_json("stt_wer.json")
    voice = read_json("voice_latency.json")
    human = correctness()
    text_latency = metrics.get("median_seconds", {})
    voice_latency = (voice or {}).get("median_seconds", {})

    lines = ["# Yojana Sahayak — measured results", ""]
    if metrics.get("dry_run"):
        lines += ["**WARNING: this evaluation used DRY_RUN. These are not real model results.**", ""]
    lines += [
        f"Questions: {display(metrics.get('n_questions'))} ({display(metrics.get('n_answerable'))} answerable, "
        f"{display(metrics.get('n_unanswerable'))} unanswerable); errors: {display(metrics.get('n_errors'))}",
        "", "| Metric | Measured value |", "|---|---|",
        f"| Retrieval Hit@3 | {percent(metrics.get('hit_at_3'))} |",
        f"| Retrieval MRR@3 | {display(metrics.get('mrr_at_3'))} |",
        f"| Correct refusals | {display(metrics.get('refusal_correct'))}/{display(metrics.get('refusal_total'))} |",
        f"| False refusals on answerable questions | {display(metrics.get('false_refusals_on_answerable'))} |",
        f"| Mean groundedness on answered questions | {display(metrics.get('mean_groundedness_of_answered'))} |",
        f"| Human correctness mean (0–2; n={display(human['n'] if human else None)}) | {display(human['mean'] if human else None)} |",
        f"| Human answers scored 1 or 2 | {percent(human['at_least_1'] if human else None)} |",
    ]
    if verifier:
        score = verifier.get("tuned_flag_metrics", {})
        lines += [
            f"| Verifier precision, Unsupported-or-Contradicted (test n={display(verifier.get('n_test'))}) | {display(score.get('precision'))} |",
            f"| Verifier recall, Unsupported-or-Contradicted | {display(score.get('recall'))} |",
        ]
    else:
        lines.append("| Verifier precision/recall on held-out test | n/a |")
    if stt:
        lines += [
            f"| STT WER without keyterms | {display(stt.get('wer_without_keyterms'))} |",
            f"| STT WER with keyterms | {display(stt.get('wer_with_keyterms'))} (n={display(stt.get('n_files'))}) |",
        ]
    lines += [
        f"| Median STT / retrieval / generation / NLI / TTS seconds | {display(voice_latency.get('stt'))} / "
        f"{display(text_latency.get('t_retrieve'))} / {display(text_latency.get('t_generate'))} / "
        f"{display(text_latency.get('t_verify'))} / {display(voice_latency.get('tts'))} |",
        f"| Median end-to-end voice seconds | {display(voice_latency.get('end_to_end_voice'))} |",
        "", "Only publish values regenerated from the final corpus and final code. Do not reuse old result files.", "",
    ]
    output = RESULTS / "summary.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
