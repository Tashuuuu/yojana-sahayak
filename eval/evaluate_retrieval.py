
import json
import sys
from pathlib import Path

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.retrieve import retrieve

QUESTIONS_PATH = BASE_DIR / "eval" / "questions.jsonl"
RESULTS_PATH = BASE_DIR / "results" / "retrieval_evaluation.json"

TOP_K = 3


def load_questions():
    """Load manually labelled evaluation questions."""
    questions = []

    with open(QUESTIONS_PATH, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                questions.append(json.loads(line))

    return questions


def evaluate():
    questions = load_questions()

    if not questions:
        raise ValueError("No evaluation questions found.")

    reciprocal_ranks = []
    hit_count = 0
    detailed_results = []

    print("\nRETRIEVAL EVALUATION")
    print("=" * 55)

    for question_data in questions:
        query = question_data["question"]
        relevant_ids = set(question_data["relevant_chunk_ids"])

        # Retrieve top 3 chunks
        retrieved = retrieve(query, top_k=TOP_K)

        retrieved_ids = [
            item["chunk_id"] for item in retrieved
        ]

        # Find the rank of the first relevant result
        reciprocal_rank = 0.0

        for rank, chunk_id in enumerate(retrieved_ids, start=1):
            if chunk_id in relevant_ids:
                reciprocal_rank = 1.0 / rank
                break

        # Hit@3: at least one relevant result in top 3
        hit = reciprocal_rank > 0

        if hit:
            hit_count += 1

        reciprocal_ranks.append(reciprocal_rank)

        detailed_results.append({
            "question": query,
            "relevant_chunk_ids": list(relevant_ids),
            "retrieved_chunk_ids": retrieved_ids,
            "hit_at_3": hit,
            "reciprocal_rank": reciprocal_rank
        })

        print(f"\nQuestion: {query}")
        print("Retrieved:", retrieved_ids)
        print("Hit@3:", hit)
        print("Reciprocal Rank:", reciprocal_rank)

    # Calculate aggregate metrics
    hit_at_3 = hit_count / len(questions)
    mrr = sum(reciprocal_ranks) / len(questions)

    evaluation = {
        "total_questions": len(questions),
        "top_k": TOP_K,
        "hit_at_3": hit_at_3,
        "mrr": mrr,
        "details": detailed_results
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_PATH, "w", encoding="utf-8") as file:
        json.dump(evaluation, file, indent=4, ensure_ascii=False)

    print("\n" + "=" * 55)
    print("FINAL EVALUATION RESULTS")
    print("=" * 55)
    print(f"Total questions: {len(questions)}")
    print(f"Hit@3: {hit_at_3:.4f} ({hit_at_3 * 100:.2f}%)")
    print(f"MRR: {mrr:.4f}")
    print(f"Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    evaluate()
