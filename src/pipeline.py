# retrieve -> generate -> verify -> decide what may be spoken
import os
import time

from src.retrieve import retrieve
from src.generate import generate_answer
from src.verify import verify_answer

FALLBACK = {
    "hi": "मैं इस सवाल का उत्तर सरकारी स्रोत से सत्यापित नहीं कर पा रहा हूँ। कृपया आधिकारिक वेबसाइट देखें।",
    "en": "I cannot verify an answer to this from the official source. Please check the official website.",
}
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.30"))

RETRIEVAL_SOURCE = "real"


def _result(query, lang, chunks, answer, verification, spoken, status, latency):
    return {"query": query, "lang": lang, "chunks": chunks, "answer": answer,
            "verification": verification, "spoken_text": spoken, "status": status,
            "latency": latency, "retrieval_source": RETRIEVAL_SOURCE}


def answer_question(query_text: str, lang: str = "hi", k: int = 4) -> dict:
    """Answer one question. status: 'verified' | 'partial' | 'refused'."""
    lang = "hi" if lang == "hi" else "en"
    query = (query_text or "").strip()
    latency = {}
    no_verification = {"sentences": [], "groundedness": 0.0}

    if not query:
        return _result(query, lang, [], "", no_verification, FALLBACK[lang], "refused", latency)

    t0 = time.perf_counter()
    chunks = retrieve(query, k=k, lang=lang)
    latency["retrieve"] = time.perf_counter() - t0
    chunks = [c for c in chunks if c.get("similarity_score", 0.0) >= MIN_SIMILARITY]
    if not chunks:
        return _result(query, lang, [], "", no_verification, FALLBACK[lang], "refused", latency)

    t0 = time.perf_counter()
    answer = generate_answer(query, chunks, lang)
    latency["generate"] = time.perf_counter() - t0
    if "NO_ANSWER" in answer:
        return _result(query, lang, chunks, answer, no_verification, FALLBACK[lang], "refused", latency)

    t0 = time.perf_counter()
    verification = verify_answer(answer, chunks, lang)
    latency["verify"] = time.perf_counter() - t0

    sentences = verification["sentences"]
    supported = [s["text"] for s in sentences if s["label"] == "Supported"]
    if not supported:
        status, spoken = "refused", FALLBACK[lang]
    elif len(supported) == len(sentences):
        status, spoken = "verified", " ".join(supported)
    else:
        status, spoken = "partial", " ".join(supported)

    return _result(query, lang, chunks, answer, verification, spoken, status, latency)