import os
os.environ["DRY_RUN"] = "1"
from src.pipeline import answer_question

r = answer_question("Who can apply for PM-KISAN?", "en")
print("ANSWER:", r["answer"])
print("VERIFICATION:", r["verification"])
print("TOP CHUNK:", r["chunks"][0]["text"][:300])