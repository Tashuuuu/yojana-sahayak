"""End-to-end Yojana Sahayak with language-aligned verification.

When the requested answer language is absent from the retrieved corpus, the
pipeline drafts and verifies in the evidence language, then translates ONLY
supported sentences into the requested language. This prevents cross-language
NLI false negatives and prevents unverified draft text from being displayed or
spoken as a verified answer.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

from src.generate import generate_answer, requires_explanation, requires_conditions_list, translate_verified_answer  # noqa: E402
from src.retrieve import retrieve  # noqa: E402
from src.verify import verify_answer  # noqa: E402
from src.voice import speak, transcribe  # noqa: E402

FALLBACK = {
    "hi": "उपलब्ध सरकारी स्रोतों से इस प्रश्न का पूरा उत्तर सत्यापित नहीं हो पाया। कृपया संबंधित योजना की आधिकारिक वेबसाइट देखें।",
    "en": "I could not verify a complete answer from the available official sources. Please check the scheme's official website.",
}


def _min_similarity() -> float:
    try:
        return float(os.getenv("MIN_SIMILARITY", "0.25"))
    except ValueError:
        return 0.25


def enrich_search_query(query: str) -> str:
    """Add retrieval terms for PMUY eligibility questions, without answering them."""
    q = (query or "").casefold()
    pmuy_terms = (
        "ujjwala", "pmuy", "pradhan mantri ujjwala", "प्रधानमंत्री उज्ज्वला", "उज्ज्वला",
    )
    eligibility_terms = (
        "eligib", "qualif", "who can", "applicant", "apply", "age", "woman", "women",
        "महिला", "पात्र", "पात्रता", "योग्य", "कौन", "आवेदन", "लाभार्थी",
    )
    if any(term in q for term in pmuy_terms) and any(term in q for term in eligibility_terms):
        # These are search hints only. Generation still receives the user's original query
        # and can state facts only when they appear in retrieved source passages.
        return f"{query} PMUY eligibility applicant age woman household"
    return query


def load_scheme_keyterms() -> list[str]:
    """Read bilingual scheme names and aliases written by src.ingest."""
    path = ROOT / "data" / "keyterms.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []
    groups = data.values() if isinstance(data, dict) else [data] if isinstance(data, list) else []
    terms: list[str] = []
    seen: set[str] = set()
    for group in groups:
        candidates = group if isinstance(group, list) else [group]
        for candidate in candidates:
            value = str(candidate).strip()
            if value and value.casefold() not in seen:
                seen.add(value.casefold())
                terms.append(value)
            if len(terms) >= 200:
                return terms
    return terms


def _empty_verification() -> dict[str, Any]:
    return {"sentences": [], "groundedness": 0.0}


def _normalise_lang(value: str | None) -> str:
    return "hi" if str(value or "").lower().startswith("hi") else "en"


def _evidence_language(chunks: list[dict], requested_lang: str) -> str:
    """Choose the language with the strongest retrieved evidence coverage."""
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for item in chunks:
        language = _normalise_lang(item.get("lang"))
        totals[language] += max(0.0, float(item.get("similarity_score", item.get("score", 0.0))))
        counts[language] += 1
    if not totals:
        return requested_lang
    return max(
        totals,
        key=lambda language: (
            totals[language], counts[language], language == requested_lang, language == "en"
        ),
    )


def _finish(
    query: str,
    lang: str,
    chunks: list[dict],
    answer: str,
    verification: dict,
    status: str,
    spoken_text: str,
    latency: dict[str, float],
    *,
    make_audio: bool,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "query": query,
        "lang": lang,
        "chunks": chunks,
        # `answer` is ALWAYS safe display text: supported only, in the requested language.
        # The original model draft is retained separately for diagnostics, never shown by default.
        "answer": answer,
        "verification": verification,
        "spoken_text": spoken_text,
        "spoken_audio": None,
        "status": status,
        "latency": latency,
        "retrieval_source": "FAISS",
        "search_query": query,
        "retrieval_diagnostics": {
            "chunks_used": len(chunks),
            "languages_found": sorted({_normalise_lang(item.get("lang")) for item in chunks}),
            "schemes_found": sorted({str(item.get("scheme_id", "unknown")) for item in chunks}),
            "best_similarity": max(
                (float(item.get("similarity_score", item.get("score", 0.0))) for item in chunks),
                default=0.0,
            ),
            "minimum_similarity": _min_similarity(),
        },
    }
    if extra:
        result.update(extra)
    if make_audio and spoken_text:
        started = time.perf_counter()
        result["spoken_audio"] = speak(spoken_text, lang)
        latency["tts"] = round(time.perf_counter() - started, 4)
    return result


def _refuse(
    query: str, lang: str, chunks: list[dict], verification: dict,
    latency: dict[str, float], *, make_audio: bool, reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details = {"answer_reason": reason}
    if extra:
        details.update(extra)
    return _finish(
        query, lang, chunks, "NO_ANSWER", verification, "refused", FALLBACK[lang], latency,
        make_audio=make_audio, extra=details,
    )


def answer_question(
    query_text: str,
    lang: str = "hi",
    k: int = 8,
    *,
    make_audio: bool = False,
) -> dict[str, Any]:
    """Retrieve, generate in evidence language, verify, then translate if necessary."""
    lang = _normalise_lang(lang)
    query = (query_text or "").strip()
    latency: dict[str, float] = {}
    empty = _empty_verification()
    if not query:
        return _refuse(query, lang, [], empty, latency, make_audio=make_audio,
                       reason="Please enter a question.")

    # Keep main's bilingual retrieval flow; apply the feature-branch PMUY hint
    # only to the retrieval query, never to the user's prompt for answer generation.
    search_query = enrich_search_query(query)
    started = time.perf_counter()
    retrieved = retrieve(search_query, k=max(8, int(k)), lang=lang)
    latency["retrieve"] = round(time.perf_counter() - started, 4)

    minimum = _min_similarity()
    chunks = [
        item for item in retrieved
        if float(item.get("similarity_score", item.get("score", 0.0))) >= minimum
    ]
    if not chunks:
        return _refuse(query, lang, [], empty, latency, make_audio=make_audio,
                       reason="No sufficiently relevant official source passage was retrieved.",
                       extra={"retrieved_candidates": retrieved})

    evidence_lang = _evidence_language(chunks, lang)
    evidence_chunks = [item for item in chunks if _normalise_lang(item.get("lang")) == evidence_lang]
    # If metadata is unexpectedly missing, don't discard all retrieved evidence.
    if not evidence_chunks:
        evidence_chunks = chunks

    started = time.perf_counter()
    draft = generate_answer(query, evidence_chunks, evidence_lang)
    latency["generate"] = round(time.perf_counter() - started, 4)
    if not draft or draft.strip().upper().rstrip(".!?। ") == "NO_ANSWER":
        return _refuse(query, lang, chunks, empty, latency, make_audio=make_audio,
                       reason="The generator could not create a complete answer from the retrieved evidence.",
                       extra={"evidence_language": evidence_lang, "draft_answer": draft or "NO_ANSWER"})

    started = time.perf_counter()
    verification = verify_answer(draft, evidence_chunks, evidence_lang)
    latency["verify"] = round(time.perf_counter() - started, 4)
    sentence_results = verification.get("sentences", [])
    supported = [item["text"] for item in sentence_results if item.get("label") == "Supported"]
    all_supported = bool(sentence_results) and len(supported) == len(sentence_results)

    required_supported = 2 if (requires_explanation(query) or requires_conditions_list(query)) else 1
    if len(supported) < required_supported:
        return _refuse(
            query, lang, chunks, verification, latency, make_audio=make_audio,
            reason=(
                f"Only {len(supported)} complete sentence(s) passed verification; "
                f"this question requires at least {required_supported} to avoid an incomplete answer."
            ),
            extra={"evidence_language": evidence_lang, "verification_language": evidence_lang,
                   "draft_answer": draft, "supported_source_answer": " ".join(supported),
                   "answer_translated": False, "translation_attempted": False},
        )

    supported_source_answer = " ".join(supported).strip()
    if evidence_lang == lang:
        final_answer = supported_source_answer
    else:
        started = time.perf_counter()
        final_answer = translate_verified_answer(supported_source_answer, lang, evidence_lang)
        latency["translate"] = round(time.perf_counter() - started, 4)
        if not final_answer or final_answer.strip().upper() == "NO_ANSWER":
            return _refuse(
                query, lang, chunks, verification, latency, make_audio=make_audio,
                reason="The source facts passed verification, but the translation did not pass completeness checks.",
                extra={"evidence_language": evidence_lang, "verification_language": evidence_lang,
                       "draft_answer": draft, "supported_source_answer": supported_source_answer,
                       "answer_translated": False, "translation_attempted": True,
                       "translation_failed": True},
            )

    status = "verified" if all_supported else "partial"
    spoken_text = final_answer if all_supported else f"{final_answer} {FALLBACK[lang]}"
    return _finish(
        query, lang, chunks, final_answer, verification, status, spoken_text, latency,
        make_audio=make_audio,
        extra={
            "evidence_language": evidence_lang,
            "verification_language": evidence_lang,
            "answer_translated": evidence_lang != lang,
            "draft_answer": draft,
            "supported_source_answer": supported_source_answer,
            "answer_reason": None if all_supported else "Unsupported draft sentences were removed. Only verified statements are shown and spoken.",
        },
    )


def answer_audio(
    wav_bytes: bytes,
    keyterms: list[str] | None = None,
    *,
    make_audio: bool = True,
) -> dict[str, Any]:
    """Full voice flow: Gnani Prisma transcription, answer pipeline, optional Timbre speech."""
    active_terms = keyterms if keyterms is not None else load_scheme_keyterms()
    started = time.perf_counter()
    transcript = transcribe(wav_bytes, keyterms=active_terms)
    stt_seconds = time.perf_counter() - started
    result = answer_question(transcript["text"], transcript["lang"], make_audio=make_audio)
    result["transcription"] = transcript
    result["latency"]["stt"] = round(stt_seconds, 4)
    result["latency"]["end_to_end_voice"] = round(time.perf_counter() - started, 4)
    return result
