"""Pipeline tests use mocks; no model downloads or API calls."""
import src.pipeline as pipeline


def test_empty_question_refuses_without_retrieval(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    result = pipeline.answer_question("  ", "hi")
    assert result["status"] == "refused"
    assert result["spoken_text"] == pipeline.FALLBACK["hi"]


def test_unanswerable_retrieval_refuses(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda *a, **k: [])
    result = pipeline.answer_question("What is the weather?", "en")
    assert result["status"] == "refused"
    assert result["spoken_text"] == pipeline.FALLBACK["en"]


def test_verified_answer_returns_supported_sentence(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda *a, **k: [{
        "chunk_id": "c1", "scheme_id": "S", "lang": "en", "section": "Benefits",
        "text": "The scheme provides Rs. 6000 per year.", "source_url": "https://example.gov.in",
        "similarity_score": 0.9,
    }])
    monkeypatch.setattr(pipeline, "generate_answer", lambda *a, **k: "The scheme provides Rs. 6000 per year.")
    monkeypatch.setattr(pipeline, "verify_answer", lambda *a, **k: {
        "sentences": [{"text": "The scheme provides Rs. 6000 per year.", "label": "Supported"}],
        "groundedness": 1.0,
    })
    result = pipeline.answer_question("What is the benefit?", "en")
    assert result["status"] == "verified"
    assert result["spoken_text"] == "The scheme provides Rs. 6000 per year."
    assert result["verification"]["groundedness"] == 1.0
