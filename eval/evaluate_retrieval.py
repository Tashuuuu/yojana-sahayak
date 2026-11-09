"""Calculate retrieval Hit@3 and MRR over eval/eval_questions.jsonl."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieve import retrieve  # noqa: E402

QUESTIONS = ROOT / "eval" / "eval_questions.jsonl"
OUTPUT = ROOT / "results" / "retrieval_evaluation.json"


def main() -> None:
    questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    answerable = [item for item in questions if item.get("answerable")]
    if not answerable:
        raise SystemExit("No answerable questions found in eval/eval_questions.jsonl")
    rows = []
    reciprocal_ranks = []
    for item in answerable:
        hits = retrieve(item["question"], k=3, lang=item.get("lang"))
        gold_scheme = item.get("gold_scheme_id")
        gold_section = item.get("gold_section")
        rank = None
        for position, chunk in enumerate(hits, 1):
            same_scheme = chunk.get("scheme_id") == gold_scheme
            same_section = not gold_section or str(chunk.get("section", "")).casefold() == str(gold_section).casefold()
            if same_scheme and same_section:
                rank = position
                break
        rr = 1.0 / rank if rank else 0.0
        reciprocal_ranks.append(rr)
        rows.append({
            "qid": item.get("qid"), "question": item["question"],
            "gold_scheme_id": gold_scheme, "gold_section": gold_section,
            "retrieved_chunk_ids": [chunk.get("chunk_id") for chunk in hits],
            "retrieved_schemes": [chunk.get("scheme_id") for chunk in hits],
            "rank": rank, "hit_at_3": rank is not None, "reciprocal_rank": rr,
        })
    report = {
        "n_answerable": len(answerable),
        "top_k": 3,
        "hit_at_3": round(sum(value > 0 for value in reciprocal_ranks) / len(reciprocal_ranks), 4),
        "mrr_at_3": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
        "details": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
