# manual check of the whole pipeline (real retrieval, fake LLM/speech by default)
import os

os.environ.setdefault("DRY_RUN", "1")

from src.pipeline import answer_question  # noqa: E402

QUESTIONS = [
    ("Who can apply for PM-KISAN?", "en"),
    ("पीएम किसान में कौन आवेदन कर सकता है?", "hi"),
    ("What is the weather today?", "en"),
]

for question, lang in QUESTIONS:
    r = answer_question(question, lang)
    print("\nQ:", question)
    print("status:", r["status"], "| groundedness:", r["verification"]["groundedness"])
    print("top scores:", [round(c["similarity_score"], 2) for c in r["chunks"]])
    print("spoken:", r["spoken_text"])
    print("latency:", {k: round(v, 2) for k, v in r["latency"].items()})