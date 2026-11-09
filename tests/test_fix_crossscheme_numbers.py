"""Regression tests for the two bugs seen in the Streamlit screenshots."""
import src.generate as gen
import src.verify as ver


def test_number_normalisation_matches_rs_and_rupee_forms():
    src = "Eligible families receive Rs6,000 per year in three instalments of Rs2,000 each."
    hi = "पात्र परिवारों को हर साल ₹6000 तीन किस्तों में, हर किस्त ₹2,000 की, मिलती है।"
    assert gen._numbers(src) == gen._numbers(hi) == ["2000", "6000"]
    assert gen._numbers("६,००० रुपये") == ["6000"]
    assert gen._numbers("Rs6,000") != gen._numbers("Rs7,000")  # real changes still caught


def test_other_scheme_cannot_contradict(monkeypatch):
    chunks = [
        {"chunk_id": "kisan", "scheme_id": "PMKISAN", "lang": "en", "text": "Farmers are eligible."},
        {"chunk_id": "ujj", "scheme_id": "PMUY", "lang": "en", "text": "Applicant must be a woman."},
    ]
    def fake_nli(premises, hypothesis):
        return [{"entailment": 0.95, "neutral": 0.04, "contradiction": 0.01} if "Farmers" in p
                else {"entailment": 0.01, "neutral": 0.09, "contradiction": 0.90} for p in premises]
    monkeypatch.setattr(ver, "nli_batch", fake_nli)
    out = ver.verify_answer("Landholding farmer families are eligible.", chunks, "en")
    assert out["sentences"][0]["label"] == "Supported"


def test_same_scheme_contradiction_still_blocks(monkeypatch):
    chunks = [{"chunk_id": "a", "scheme_id": "PMKISAN", "lang": "en", "text": "Farmers get Rs6,000."}]
    monkeypatch.setattr(ver, "nli_batch", lambda p, h: [
        {"entailment": 0.70, "neutral": 0.0, "contradiction": 0.60} for _ in p])
    out = ver.verify_answer("Farmers get Rs9,000.", chunks, "en")
    assert out["sentences"][0]["label"] == "Contradicted"
