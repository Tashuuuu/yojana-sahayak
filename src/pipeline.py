# translate question -> retrieve -> generate (English) -> verify (English) -> translate -> decide what may be spoken
import os
import time

from src.retrieve import retrieve
from src.generate import generate_answer, to_english, translate
from src.verify import verify_answer

FALLBACK = {
    "hi": "मैं इस सवाल का उत्तर सरकारी स्रोत से सत्यापित नहीं कर पा रहा हूँ। कृपया आधिकारिक वेबसाइट देखें।",
    "en": "I cannot verify an answer to this from the official source. Please check the official website.",
}

# Chunks scoring below this are treated as "not related to the question".
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.30"))


def _result(query, lang, chunks, answer, verification, spoken, status, latency, search_query=""):
    return {"query": query, "lang": lang, "chunks": chunks, "answer": answer,
            "verification": verification, "spoken_text": spoken, "status": status,
            "latency": latency, "retrieval_source": "real", "search_query": search_query}


def answer_question(query_text: str, lang: str = "hi", k: int = 4) -> dict:
    """Answer one question. status: 'verified' | 'partial' | 'refused'."""
    lang = "hi" if lang == "hi" else "en"
    query = (query_text or "").strip()
    latency = {}
    no_verification = {"sentences": [], "groundedness": 0.0}

    if not query:
        return _result(query, lang, [], "", no_verification, FALLBACK[lang], "refused", latency)

    # the documents are English, so search and answer with an English question
    t0 = time.perf_counter()
    search_query = to_english(query) if lang == "hi" else query
    latency["translate_query"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    chunks = retrieve(search_query, k=k, lang="en")
    latency["retrieve"] = time.perf_counter() - t0

    chunks = [c for c in chunks if c.get("similarity_score", 0.0) >= MIN_SIMILARITY]
    if not chunks:
        return _result(query, lang, [], "", no_verification, FALLBACK[lang], "refused", latency, search_query)

    t0 = time.perf_counter()
    answer = generate_answer(search_query, chunks, "en")
    latency["generate"] = time.perf_counter() - t0
    if "NO_ANSWER" in answer:
        return _result(query, lang, chunks, answer, no_verification, FALLBACK[lang], "refused", latency, search_query)

    t0 = time.perf_counter()
    verification = verify_answer(answer, chunks, "en")
    latency["verify"] = time.perf_counter() - t0

    sentences = verification["sentences"]
    supported = [s["text"] for s in sentences if s["label"] == "Supported"]
    if not supported:
        return _result(query, lang, chunks, answer, verification, FALLBACK[lang], "refused", latency, search_query)
    if len(supported) < len(sentences):
        # a half-answer can mislead; speak only fully verified answers
        return _result(query, lang, chunks, answer, verification, FALLBACK[lang], "partial", latency, search_query)

    t0 = time.perf_counter()
    spoken = translate(" ".join(supported), lang)
    latency["translate"] = time.perf_counter() - t0

    return _result(query, lang, chunks, answer, verification, spoken, "verified", latency, search_query)