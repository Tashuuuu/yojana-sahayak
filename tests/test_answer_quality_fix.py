"""Offline tests for the answer-quality patch; no API calls or model downloads."""
from __future__ import annotations

import src.generate as generate
import src.pipeline as pipeline


def test_dry_run_never_returns_english_source_for_hindi_question(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "1")
    chunks = [{
        "lang": "en",
        "text": "Landholding farmer families are eligible subject to the scheme guidelines.",
    }]
    assert generate.generate_answer("पीएम किसान योजना के बारे में बताइए", chunks, "hi") == "NO_ANSWER"


def test_dry_run_returns_same_language_source_sentence(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "1")
    chunks = [{
        "lang": "hi",
        "text": "इस योजना के तहत पात्र किसान परिवारों को सहायता मिलती है।",
    }]
    assert generate.generate_answer("यह योजना क्या है?", chunks, "hi") == chunks[0]["text"]


def test_broad_question_retries_short_fragment_then_accepts_full_answer(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "0")
    outputs = iter([
        "PM-KISAN योजना के तहत पात्र किसान परिवार",
        "PM-KISAN योजना पात्र किसान परिवारों को वित्तीय सहायता देती है। पात्रता और लाभ आधिकारिक दिशा-निर्देशों के अनुसार तय होते हैं।",
    ])
    calls = []

    def fake_ask(system, user, max_tokens=550):
        calls.append((system, user, max_tokens))
        return next(outputs)

    monkeypatch.setattr(generate, "_ask", fake_ask)
    chunks = [{
        "scheme_id": "PMKISAN", "name_hi": "पीएम-किसान", "name_en": "PM-KISAN",
        "lang": "en", "section": "Eligibility",
        "text": "Eligible farmer families receive financial assistance under the scheme, subject to official guidelines.",
    }]
    answer = generate.generate_answer("PM किसान योजना के बारे में बताइए", chunks, "hi")
    assert len(calls) == 2
    assert "पात्र किसान परिवारों" in answer
    assert len(generate._split_sentences(answer)) == 2


def test_broad_question_refuses_after_retry_if_only_fragment_returned(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(generate, "_ask", lambda *a, **k: "PM-KISAN योजना के तहत पात्र किसान परिवार")
    chunks = [{"lang": "hi", "text": "पात्र किसान परिवार इस योजना के लाभार्थी हो सकते हैं।"}]
    assert generate.generate_answer("पीएम किसान योजना के बारे में बताइए", chunks, "hi") == "NO_ANSWER"


def test_pipeline_requests_eight_chunks_and_surfaces_diagnostics(monkeypatch):
    observed = {}

    def fake_retrieve(query, k, lang):
        observed["k"] = k
        return [{
            "chunk_id": "c1", "scheme_id": "PMKISAN", "lang": "en",
            "section": "Benefits", "text": "Eligible farmer families receive financial support.",
            "source_url": "https://example.gov.in", "similarity_score": 0.8,
        }]

    monkeypatch.setattr(pipeline, "retrieve", fake_retrieve)
    monkeypatch.setattr(pipeline, "generate_answer", lambda *a, **k: "Eligible farmer families receive financial support.")
    monkeypatch.setattr(pipeline, "verify_answer", lambda *a, **k: {
        "sentences": [{"text": "Eligible farmer families receive financial support.", "label": "Supported"}],
        "groundedness": 1.0,
    })
    result = pipeline.answer_question("Who benefits?", "en", make_audio=False)
    assert observed["k"] == 8
    assert result["status"] == "verified"
    assert result["retrieval_diagnostics"]["chunks_used"] == 1
    assert result["retrieval_diagnostics"]["languages_found"] == ["en"]
