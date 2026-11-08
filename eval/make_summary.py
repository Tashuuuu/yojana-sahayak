# eval/make_summary.py — collect every result into results/summary.md (copy it into the README).
# Usage (repo root):  python eval/make_summary.py
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


def read_json(name):
    p = R / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def na(value, suffix=""):
    return "n/a" if value is None else f"{value}{suffix}"


def pct(value):
    return "n/a" if value is None else f"{round(value * 100)}%"


def correctness():
    p = R / "correctness.csv"
    if not p.exists():
        return None
    scores = []
    with open(p, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                scores.append(int(row["score"]))
            except (KeyError, ValueError):
                pass
    if not scores:
        return None
    return {"n": len(scores), "mean": round(statistics.mean(scores), 2), "zeros": scores.count(0),
            "at_least_1": round(sum(s >= 1 for s in scores) / len(scores), 3)}


def main():
    m = read_json("eval_metrics.json") or {}
    v = read_json("verifier_test_metrics.json")
    s = read_json("stt_wer.json")
    c = correctness()
    lat = m.get("median_seconds") or {}
    lines = ["# Results summary (auto-generated; check every number before publishing)", ""]
    if m.get("dry_run") or "mock" in (m.get("retrieval_sources") or []):
        lines += ["**WARNING: these numbers came from a dry run or mock retrieval. Do NOT publish them.**", ""]
    lines += [
        f"Questions: {na(m.get('n_questions'))} ({na(m.get('n_answerable'))} answerable, "
        f"{na(m.get('n_unanswerable'))} unanswerable); failed runs: {na(m.get('n_errors'))}", "",
        "| Metric | Value |", "|---|---|",
        f"| Retrieval Hit@3 | {pct(m.get('hit_at_3'))} |",
        f"| Retrieval MRR@3 | {na(m.get('mrr_at_3'))} |",
        f"| Refused correctly on unanswerable questions | {na(m.get('refusal_correct'))}/{na(m.get('refusal_total'))} |",
        f"| Wrongly refused answerable questions | {na(m.get('false_refusals_on_answerable'))} |",
        f"| Mean groundedness of answered questions | {na(m.get('mean_groundedness_of_answered'))} |",
        f"| Human correctness, mean of 0-2 (n={na(c['n'] if c else None)}) | {na(c['mean'] if c else None)} |",
        f"| Answers rated 1 or 2 | {pct(c['at_least_1'] if c else None)} |",
    ]
    if v:
        t = v["tuned_flag_metrics"]
        lines += [f"| Verifier precision on unsupported/contradicted (test, n={v['n_test']}) | {t['precision']} |",
                  f"| Verifier recall on unsupported/contradicted (test) | {t['recall']} |"]
    else:
        lines += ["| Verifier precision / recall (test) | n/a |"]
    if s:
        lines += [f"| Speech WER without keyterms | {s['wer_without_keyterms']} |",
                  f"| Speech WER with keyterms | {s['wer_with_keyterms']} (n={s['n_files']}) |"]
    lines += [
        f"| Median seconds: retrieve / generate / verify | {na(lat.get('t_retrieve'))} / "
        f"{na(lat.get('t_generate'))} / {na(lat.get('t_verify'))} |",
        f"| Median seconds, text pipeline total | {na(lat.get('t_total'))} |",
        "", "Add your measured speech-to-text and text-to-speech latency (from results/latency_notes.txt) by hand.", "",
    ]
    (R / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()