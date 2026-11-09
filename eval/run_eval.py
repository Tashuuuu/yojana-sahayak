"""Run the 40-question answer/refusal/verifier evaluation using real components."""
from __future__ import annotations

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
load_dotenv(ROOT / ".env")
from src.pipeline import answer_question  # noqa: E402
from src.retrieve import retrieve  # noqa: E402


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 3) if values else None


def _gold_rank(chunks: list[dict], question: dict, top: int = 3) -> int | None:
    for rank, chunk in enumerate(chunks[:top], 1):
        if chunk.get("scheme_id") != question.get("gold_scheme_id"):
            continue
        section = question.get("gold_section")
        if section and str(chunk.get("section", "")).casefold() != str(section).casefold():
            continue
        return rank
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default="eval/eval_questions.jsonl")
    parser.add_argument("--out", default="results/eval_run.csv")
    parser.add_argument("--sentences", default="results/eval_sentences.jsonl")
    parser.add_argument("--metrics", default="results/eval_metrics.json")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()
    questions = _load_jsonl(ROOT / args.questions)
    if args.limit:
        questions = questions[:args.limit]
    if not questions:
        raise SystemExit("Evaluation question set is empty")
    dry_run = os.getenv("DRY_RUN", "0") == "1"
    if dry_run:
        print("WARNING: DRY_RUN=1; generation/speech are simulated. Do not report these as real results.")

    rows: list[dict] = []
    sentence_records: list[dict] = []
    for number, question in enumerate(questions, 1):
        lang = "hi" if str(question.get("lang", "en")).lower().startswith("hi") else "en"
        answerable = bool(question.get("answerable"))
        start = time.perf_counter()
        row = {
            "qid": question.get("qid", f"Q{number:03d}"), "lang": lang,
            "answerable": answerable, "question": question["question"],
            "gold_scheme_id": question.get("gold_scheme_id") or "",
            "status": "error", "hit3": None, "rank": None, "top3_schemes": "",
            "answer": "", "spoken_text": "", "groundedness": None,
            "t_retrieve": None, "t_generate": None, "t_verify": None, "t_total": None, "error": "",
        }
        try:
            raw_retrieval = retrieve(question["question"], k=args.k, lang=lang)
            rank = _gold_rank(raw_retrieval, question) if answerable else None
            result = answer_question(question["question"], lang=lang, k=args.k)
            row.update({
                "status": result["status"],
                "rank": rank,
                "hit3": (rank is not None) if answerable else None,
                "top3_schemes": " | ".join(str(x.get("scheme_id", "")) for x in raw_retrieval[:3]),
                "answer": result["answer"],
                "spoken_text": result["spoken_text"],
                "groundedness": result["verification"].get("groundedness", 0.0),
                "t_retrieve": round(result["latency"].get("retrieve", 0.0), 3),
                "t_generate": round(result["latency"].get("generate", 0.0), 3),
                "t_verify": round(result["latency"].get("verify", 0.0), 3),
            })
            sentence_records.append({
                "qid": row["qid"], "lang": lang, "question": question["question"],
                "status": result["status"], "sentences": result["verification"].get("sentences", []),
                "chunks": [{"chunk_id": chunk.get("chunk_id"), "text": chunk.get("text"),
                            "source_url": chunk.get("source_url")} for chunk in raw_retrieval[:3]],
            })
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["t_total"] = round(time.perf_counter() - start, 3)
        rows.append(row)
        print(f"[{number}/{len(questions)}] {row['qid']} -> {row['status']} {row['error']}")
        if args.sleep > 0 and number < len(questions):
            time.sleep(args.sleep)

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (ROOT / args.sentences).open("w", encoding="utf-8") as handle:
        for item in sentence_records:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    successful = [row for row in rows if not row["error"]]
    answerable_rows = [row for row in successful if row["answerable"]]
    unanswerable_rows = [row for row in successful if not row["answerable"]]
    reciprocal = [1 / row["rank"] for row in answerable_rows if row["rank"]]
    grounded = [row["groundedness"] for row in successful
                if row["status"] != "refused" and row["groundedness"] is not None]
    metrics = {
        "dry_run": dry_run,
        "n_questions": len(rows), "n_errors": len(rows) - len(successful),
        "n_answerable": len(answerable_rows), "n_unanswerable": len(unanswerable_rows),
        "hit_at_3": round(sum(bool(row["hit3"]) for row in answerable_rows) / len(answerable_rows), 3) if answerable_rows else None,
        "mrr_at_3": round(sum(reciprocal) / len(answerable_rows), 3) if answerable_rows else None,
        "refusal_correct": sum(row["status"] == "refused" for row in unanswerable_rows),
        "refusal_total": len(unanswerable_rows),
        "false_refusals_on_answerable": sum(row["status"] == "refused" for row in answerable_rows),
        "mean_groundedness_of_answered": round(statistics.mean(grounded), 4) if grounded else None,
        "status_counts": {status: sum(row["status"] == status for row in successful)
                          for status in ("verified", "partial", "refused")},
        "median_seconds": {
            key: _median([row[key] for row in successful if row[key] is not None])
            for key in ("t_retrieve", "t_generate", "t_verify", "t_total")
        },
        "note": "Human correctness and held-out verifier precision/recall require separate human labels.",
    }
    (ROOT / args.metrics).write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
