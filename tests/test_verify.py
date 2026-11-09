"""NLI logic tests with a fake model score function; the real model is tested by smoke runs."""
import src.verify as verify


def test_split_hindi_and_english():
    assert len(verify.split_sentences("यह पहला वाक्य है। यह दूसरा वाक्य है।")) == 2
    assert len(verify.split_sentences("First sentence. Second sentence.")) == 2


def test_checkpoint_label_mapping_matches_published_config():
    assert verify.resolve_id2label({"0": "entailment", "1": "neutral", "2": "contradiction"}) == {
        0: "entailment", 1: "neutral", 2: "contradiction"
    }
    assert verify.resolve_id2label({"0": "LABEL_0", "1": "LABEL_1", "2": "LABEL_2"}) == {
        0: "entailment", 1: "neutral", 2: "contradiction"
    }


def test_supported_unsupported_and_contradicted_labels(monkeypatch):
    def fake_batch(premises, hypothesis):
        lowered = hypothesis.lower()
        if "unsupported" in lowered:
            return [{"entailment": 0.10, "neutral": 0.85, "contradiction": 0.05} for _ in premises]
        if "contradicted" in lowered:
            return [{"entailment": 0.02, "neutral": 0.03, "contradiction": 0.95} for _ in premises]
        if "conflict" in lowered:
            return [{"entailment": 0.91, "neutral": 0.02, "contradiction": 0.75} for _ in premises]
        if "supported" in lowered:
            return [{"entailment": 0.95, "neutral": 0.04, "contradiction": 0.01} for _ in premises]
        return [{"entailment": 0.10, "neutral": 0.85, "contradiction": 0.05} for _ in premises]
    monkeypatch.setattr(verify, "nli_batch", fake_batch)
    chunks = [{"chunk_id": "c1", "lang": "en", "text": "A source premise is available."}]
    result = verify.verify_answer(
        "This is supported. This is unsupported. This is contradicted. This is conflict.", chunks, "en"
    )
    assert [item["label"] for item in result["sentences"]] == [
        "Supported", "Unsupported", "Contradicted", "Contradicted"
    ]
    assert round(result["groundedness"], 3) == 0.25


def test_rs_abbreviation_does_not_split_answer_sentence():
    assert verify.split_sentences("Farmers receive Rs. 6000 per year. It is paid in instalments.") == [
        "Farmers receive Rs. 6000 per year.", "It is paid in instalments."
    ]


def test_empty_answer_is_zero_groundedness():
    result = verify.verify_answer("", [], "en")
    assert result == {"sentences": [], "groundedness": 0.0}
