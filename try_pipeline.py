# try_pipeline.py — manual check of the whole text pipeline (no Gnani credits are ever used here).
#   python try_pipeline.py          -> FREE: fake LLM (dry run) + mock retrieval
#   python try_pipeline.py --real   -> real Groq LLM + Bhawna's real retrieval (uses your free Groq quota)
import argparse
import os

ap = argparse.ArgumentParser()
ap.add_argument("--real", action="store_true", help="use the real LLM and the real retrieval")
args = ap.parse_args()

# set BEFORE importing src.* (they read these when imported); values set here beat the ones in .env
os.environ["DRY_RUN"] = "0" if args.real else "1"
os.environ["USE_MOCK_RETRIEVE"] = "0" if args.real else "1"

from src.pipeline import answer_question  # noqa: E402

for question, lang in [("Who can apply for PM-KISAN?", "en"),
                       ("पीएम किसान में कौन आवेदन कर सकता है?", "hi"),
                       ("What is the weather today?", "en")]:
    r = answer_question(question, lang)
    print("\nQ:", question)
    print("status:", r["status"], "| groundedness:", r["verification"]["groundedness"],
          "| retrieval:", r["retrieval_source"])
    for s in r["verification"]["sentences"]:
        print(f"   {s['label']:<12} {s['text']}")
    print("spoken:", r["spoken_text"])
    print("latency:", {k: round(v, 2) for k, v in r["latency"].items()})