"""Regression tests for the English-evidence/Hindi-answer case in the UI screenshot."""
import src.pipeline as pipeline


def _english_chunks():
    return [
        {
            "chunk_id": "pmkisan-benefits-en",
            "scheme_id": "PMKISAN",
            "lang": "en",
            "section": "Benefits",
            "text": "The scheme provides eligible farmer families financial assistance of Rs. 6000 per year in three equal instalments.",
            "source_url": "https://pmkisan.gov.in/",
            "similarity_score": 0.83,
        },
        {
            "chunk_id": "pmkisan-eligibility-en",
            "scheme_id": "PMKISAN",
            "lang": "en",
            "section": "Eligibility",
            "text": "Eligible landholding farmer families are identified subject to the scheme guidelines and exclusion criteria.",
            "source_url": "https://pmkisan.gov.in/",
            "similarity_score": 0.81,
        },
    ]


def test_hindi_question_with_english_only_evidence_verifies_in_english_then_translates(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda *a, **k: _english_chunks())
    calls = {}

    def fake_generate(query, chunks, lang):
        calls["generate_lang"] = lang
        assert all(item["lang"] == "en" for item in chunks)
        return (
            "The scheme provides eligible farmer families Rs. 6000 per year in three equal instalments. "
            "Eligible landholding farmer families are covered subject to the scheme guidelines and exclusions."
        )

    def fake_verify(answer, chunks, lang):
        calls["verify_lang"] = lang
        assert all(item["lang"] == "en" for item in chunks)
        return {
            "sentences": [
                {"text": "The scheme provides eligible farmer families Rs. 6000 per year in three equal instalments.", "label": "Supported"},
                {"text": "Eligible landholding farmer families are covered subject to the scheme guidelines and exclusions.", "label": "Supported"},
            ],
            "groundedness": 1.0,
        }

    monkeypatch.setattr(pipeline, "generate_answer", fake_generate)
    monkeypatch.setattr(pipeline, "verify_answer", fake_verify)
    monkeypatch.setattr(
        pipeline, "translate_verified_answer",
        lambda text, target, source: "इस योजना के तहत पात्र किसान परिवारों को तीन समान किस्तों में प्रति वर्ष 6000 रुपये मिलते हैं। पात्र भूमिधारक किसान परिवार योजना के दिशा-निर्देशों और अपवर्जन शर्तों के अधीन शामिल हैं।",
    )

    result = pipeline.answer_question("पीएम किसान योजना के बारे में बताइए", lang="hi", make_audio=False)

    assert calls == {"generate_lang": "en", "verify_lang": "en"}
    assert result["status"] == "verified"
    assert result["verification_language"] == "en"
    assert result["answer_translated"] is True
    assert "पात्र किसान परिवारों" in result["answer"]
    assert result["answer"] == result["spoken_text"]


def test_unverified_draft_is_not_returned_as_display_answer(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda *a, **k: _english_chunks())
    draft = (
        "The scheme provides eligible farmer families Rs. 6000 per year. "
        "All farmers receive an additional Rs. 12000 every month. "
        "The benefit is paid in three instalments."
    )
    monkeypatch.setattr(pipeline, "generate_answer", lambda *a, **k: draft)
    monkeypatch.setattr(pipeline, "verify_answer", lambda *a, **k: {
        "sentences": [
            {"text": "The scheme provides eligible farmer families Rs. 6000 per year.", "label": "Supported"},
            {"text": "All farmers receive an additional Rs. 12000 every month.", "label": "Unsupported"},
            {"text": "The benefit is paid in three instalments.", "label": "Supported"},
        ],
        "groundedness": 2 / 3,
    })
    monkeypatch.setattr(pipeline, "translate_verified_answer", lambda *a, **k: "इस योजना में पात्र किसान परिवारों को प्रति वर्ष 6000 रुपये मिलते हैं। लाभ तीन किस्तों में दिया जाता है।")

    result = pipeline.answer_question("पीएम किसान योजना के बारे में बताइए", lang="hi", make_audio=False)

    assert result["status"] == "partial"
    assert result["answer_translated"] is True
    assert "12000" not in result["answer"]
    assert "12000" not in result["spoken_text"]
    assert "12000" in result["draft_answer"]  # retained for diagnostic expander only


def test_broad_question_refuses_if_only_one_sentence_passes_verification(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda *a, **k: _english_chunks())
    monkeypatch.setattr(pipeline, "generate_answer", lambda *a, **k: "The scheme provides support to eligible farmer families. It is governed by official guidelines.")
    monkeypatch.setattr(pipeline, "verify_answer", lambda *a, **k: {
        "sentences": [
            {"text": "The scheme provides support to eligible farmer families.", "label": "Supported"},
            {"text": "It is governed by official guidelines.", "label": "Unsupported"},
        ],
        "groundedness": 0.5,
    })
    monkeypatch.setattr(pipeline, "translate_verified_answer", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not translate incomplete answer")))

    result = pipeline.answer_question("पीएम किसान योजना के बारे में बताइए", lang="hi", make_audio=False)

    assert result["status"] == "refused"
    assert result["answer"] == "NO_ANSWER"
    assert result["spoken_text"] == pipeline.FALLBACK["hi"]


def test_verified_translation_preserves_numbers_and_sentence_count(monkeypatch):
    import src.generate as generate

    monkeypatch.setattr(generate, "_dry_run", lambda: False)
    monkeypatch.setattr(
        generate, "_ask",
        lambda *a, **k: "किसानों को प्रति वर्ष 6000 रुपये मिलते हैं। भुगतान तीन किस्तों में किया जाता है।",
    )
    translated = generate.translate_verified_answer(
        "Farmers receive Rs. 6000 per year. Payment is made in three instalments.",
        target_lang="hi", source_lang="en",
    )
    assert "6000" in translated
    assert len(generate._split_sentences(translated)) == 2


def test_bad_translation_is_rejected_instead_of_returned(monkeypatch):
    import src.generate as generate

    monkeypatch.setattr(generate, "_dry_run", lambda: False)
    monkeypatch.setattr(generate, "_ask", lambda *a, **k: "किसानों को प्रति वर्ष 5000 रुपये मिलते हैं।")
    translated = generate.translate_verified_answer(
        "Farmers receive Rs. 6000 per year. Payment is made in three instalments.",
        target_lang="hi", source_lang="en",
    )
    assert translated == "NO_ANSWER"
