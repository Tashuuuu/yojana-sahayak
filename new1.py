import json
from src.retrieve import retrieve

print("== top similarity score per question (lowest first) ==")
rows = []
for line in open("eval/eval_questions.jsonl", encoding="utf-8-sig"):
    if line.strip():
        q = json.loads(line)
        top = retrieve(q["question"], k=4)[0]["similarity_score"]
        rows.append((round(top, 2), "ANSWERABLE" if q["answerable"] else "unanswerable", q["lang"], q["qid"], q["question"][:45]))
for r in sorted(rows):
    print(*r)

print("\n== verifier scores for the 4 refused answers ==")
for line in open("results/eval_sentences.jsonl", encoding="utf-8"):
    r = json.loads(line)
    if r["qid"] in ("Q03", "Q09", "Q11", "Q20"):
        print(r["qid"], r["question"])
        for s in r["sentences"]:
            print("   ", s["label"], "e=", s["entail"], "c=", s["contra"], "|", s["text"])