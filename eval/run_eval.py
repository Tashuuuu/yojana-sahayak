# eval/run_eval.py — run every evaluation question through the pipeline and compute the metrics.
# Usage (from the repo root):  python eval/run_eval.py --sleep 2
import argparse
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")  # must run BEFORE importing src.* (they read DRY_RUN when imported)

from src.pipeline import answer_question  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return [json.loads(line) for line in f if line.strip()]


def median(values):
    vals = [v for v in values if v is not None]
    return round(statistics.median(vals), 3) if vals else None


def rank_of_gold(chunks: list[dict], gold: str, top: int = 3):
    """1-based position of the first chunk from the gold scheme within the top chunks, else None."""
    for i, chunk in enumerate(chunks[:top], start=1):
        if chunk.get("scheme_id") == gold:
            return i
    return None


def main():
    ap = argparse.ArgumentParser(description="Run the evaluation questions through the pipeline.")
    ap.add_argument("--questions", default="eval/questions.jsonl")
    ap.add_argument("--out", default="results/eval_run.csv")
    ap.add_argument("--sentences", default="results/eval_sentences.jsonl")
    ap.add_argument("--metrics", default="results/eval_metrics.json")
    ap.add_argument("--sleep", type=float, default=2.0, help="seconds to wait between questions (Groq rate limit)")
    ap.add_argument("--limit", type=int, default=0, help="run only the first N questions (0 = all)")
    ap.add_argument("--k", type=int, default=4, help="chunks retrieved per question")
    args = ap.parse_args()

    dry = os.getenv("DRY_RUN", "0") == "1"
    if dry:
        print("WARNING: DRY_RUN=1, so answers are fake. These numbers are NOT real results.\n")

    questions = load_jsonl(ROOT / args.questions)
    if args.limit:
        questions = questions[: args.limit]
    (ROOT / "results").mkdir(exist_ok=True)

    rows, sentence_records, sources = [], [], set()
    for n, q in enumerate(questions, start=1):
        row = {"qid": q["qid"], "lang": q.get("lang", "hi"), "answerable": bool(q.get("answerable")),
               "question": q["question"], "gold_scheme_id": q.get("gold_scheme_id"), "status": "error",
               "hit3": None, "rank": None, "top3_schemes": "", "answer": "", "spoken_text": "",
               "groundedness": None, "t_retrieve": None, "t_generate": None, "t_verify": None,
               "t_total": None, "retrieval_source": "", "error": ""}
        try:
            t0 = time.perf_counter()
            r = answer_question(q["question"], row["lang"], k=args.k)
            row["t_total"] = round(time.perf_counter() - t0, 3)
            sources.add(r.get("retrieval_source", ""))
            top3 = r["chunks"][:3]
            row.update({
                "status": r["status"], "answer": r["answer"], "spoken_text": r["spoken_text"],
                "groundedness": r["verification"]["groundedness"],
                "top3_schemes": " | ".join(c.get("scheme_id", "") for c in top3),
                "retrieval_source": r.get("retrieval_source", ""),
                "t_retrieve": round(r["latency"].get("retrieve", 0), 3),
                "t_generate": round(r["latency"].get("generate", 0), 3),
                "t_verify": round(r["latency"].get("verify", 0), 3),
            })
            if row["answerable"]:
                row["rank"] = rank_of_gold(r["chunks"], row["gold_scheme_id"])
                row["hit3"] = row["rank"] is not None
            sentence_records.append({
                "qid": q["qid"], "lang": row["lang"], "question": q["question"], "status": r["status"],
                "sentences": r["verification"]["sentences"],
                "chunks": [{"chunk_id": c["chunk_id"], "text": c["text"]} for c in top3],
            })
        except Exception as err:  # keep going; record the failure
            row["error"] = f"{type(err).__name__}: {err}"
        rows.append(row)
        print(f"[{n}/{len(questions)}] {row['qid']} -> {row['status']} {row['error']}")
        time.sleep(args.sleep)

    with open(ROOT / args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with open(ROOT / args.sentences, "w", encoding="utf-8") as f:
        for rec in sentence_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    ok = [x for x in rows if not x["error"]]
    answerable = [x for x in ok if x["answerable"]]
    unanswerable = [x for x in ok if not x["answerable"]]
    hits = sum(1 for x in answerable if x["hit3"])
    mrr = sum(1 / x["rank"] for x in answerable if x["rank"]) / len(answerable) if answerable else None
    refused_ok = sum(1 for x in unanswerable if x["status"] == "refused")
    false_refusals = sum(1 for x in answerable if x["status"] == "refused")
    grounded = [x["groundedness"] for x in ok if x["status"] != "refused" and x["groundedness"] is not None]

    metrics = {
        "dry_run": dry, "retrieval_sources": sorted(sources),
        "n_questions": len(rows), "n_errors": len(rows) - len(ok),
        "n_answerable": len(answerable), "n_unanswerable": len(unanswerable),
        "hit_at_3": round(hits / len(answerable), 3) if answerable else None,
        "mrr_at_3": round(mrr, 3) if mrr is not None else None,
        "refusal_correct": refused_ok, "refusal_total": len(unanswerable),
        "false_refusals_on_answerable": false_refusals,
        "status_counts": {s: sum(1 for x in ok if x["status"] == s) for s in ("verified", "partial", "refused")},
        "mean_groundedness_of_answered": round(statistics.mean(grounded), 3) if grounded else None,
        "median_seconds": {k: median([x[k] for x in ok]) for k in ("t_retrieve", "t_generate", "t_verify", "t_total")},
    }
    with open(ROOT / args.metrics, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print("\n=== METRICS ===")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if "mock" in sources:
        print("\nWARNING: some answers used MOCK retrieval. Do not report these numbers.")
    if metrics["n_errors"]:
        print(f"\nWARNING: {metrics['n_errors']} questions failed. See the 'error' column in {args.out}.")


if __name__ == "__main__":
    main()