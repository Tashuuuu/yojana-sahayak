"""Quick local pipeline check; retrieval/NLI are real, DRY_RUN replaces only the LLM response."""
from __future__ import annotations

import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--real-llm", action="store_true", help="use the configured Groq/Ollama model")
args = parser.parse_args()
if not args.real_llm:
    os.environ["DRY_RUN"] = "1"

from src.pipeline import answer_question  # noqa: E402

for question, language in [
    ("Who can apply for PM-KISAN?", "en"),
    ("पीएम किसान में कौन आवेदन कर सकता है?", "hi"),
    ("What is the weather today?", "en"),
]:
    result = answer_question(question, language)
    print("\nQUESTION:", question)
    print("STATUS:", result["status"], "GROUNDEDNESS:", result["verification"]["groundedness"])
    for item in result["verification"]["sentences"]:
        print(f"  {item['label']}: {item['text']}")
    print("SPOKEN:", result["spoken_text"])
    print("LATENCY:", result["latency"])
