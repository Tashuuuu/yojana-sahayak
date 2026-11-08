# quick manual check of the verifier (no API credits)
from src.verify import verify_answer

chunks = [{"chunk_id": "t1", "lang": "en",
           "text": "PM-KISAN gives eligible farmer families six thousand rupees per year in three instalments."}]
answer = "Farmers get six thousand rupees a year. The scheme gives a car to every farmer."

result = verify_answer(answer, chunks, "en")
for s in result["sentences"]:
    print(f"{s['label']:<13} entail={s['entail']:.2f} contra={s['contra']:.2f}  {s['text']}")
print("groundedness:", result["groundedness"])