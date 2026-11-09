"""Fast, offline contract tests; no model downloads or paid API calls."""
from __future__ import annotations

import io
import json
import wave

import src.pipeline as pipeline
import src.retrieve as retrieve_module
import src.voice as voice
from src.ingest import make_chunk_id
from src.verify import premises_for, split_sentences


def wav_bytes(seconds: float = 0.2) -> bytes:
    data = io.BytesIO()
    with wave.open(data, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(24000)
        stream.writeframes(b"\x00\x00" * int(24000 * seconds))
    return data.getvalue()


class FakeResponse:
    def __init__(self, *, payload=None, content=b"", status_code=200, text=""):
        self._payload = payload or {}
        self.content = content
        self.status_code = status_code
        self.text = text
        self.headers = {"Content-Type": "audio/wav"}
        self.ok = status_code < 400

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_language_qualified_chunk_ids_do_not_collide():
    en = make_chunk_id("pm-kisan", "en", "Eligibility", 0)
    hi = make_chunk_id("pm-kisan", "hi", "Eligibility", 0)
    assert en != hi
    assert "__en__" in en and "__hi__" in hi


def test_e5_passage_prefix_is_used():
    chunk = {"scheme_id": "S", "name_en": "Scheme", "section": "Benefits",
             "lang": "en", "text": "Eligible families receive support."}
    assert retrieve_module._passage_text(chunk).startswith("passage: ")


def test_split_sentences_and_premises_cover_hindi_english_and_rs_abbreviation():
    assert len(split_sentences("पहला वाक्य। दूसरा वाक्य।")) == 2
    assert len(split_sentences("First sentence. Second sentence.")) == 2
    assert split_sentences("Farmers receive Rs. 6000 per year. It is paid in instalments.")[0] == \
        "Farmers receive Rs. 6000 per year."
    assert "One fact. Two facts." in premises_for("One fact. Two facts. Three facts.")


def test_prisma_dry_run_contract(monkeypatch):
    monkeypatch.setattr(voice, "_dry_run", lambda: True)
    output = voice.transcribe(b"test")
    assert output["lang"] == "hi"
    assert output["detected_language_code"] == "hi-IN"
    assert "किसान" in output["text"]


def test_prisma_real_request_contract_and_keyterms(monkeypatch):
    calls = []
    monkeypatch.setattr(voice, "_dry_run", lambda: False)
    monkeypatch.setattr(voice, "_secret", lambda name: "test-key")
    monkeypatch.setattr(voice, "_post_with_retry", lambda *args, **kwargs: (
        calls.append(kwargs) or FakeResponse(payload={
            "success": True, "transcript": "पीएम किसान में कौन पात्र है?",
            "detected_language_code": "hi-IN", "request_id": "req-1",
        })
    ))
    result = voice.transcribe(wav_bytes(), keyterms=["PM-KISAN", "पीएम-किसान"])
    assert result["request_id"] == "req-1"
    sent_data = calls[0]["data"]
    assert sent_data["model"] == "prisma-v3.0"
    assert sent_data["language_code"] == "hi-IN,en-IN"
    assert "multi_lang_codes" not in sent_data
    # Gnani's current REST API calls the synopsis's keyterms `keywords`.
    assert json.loads(sent_data["keyterms"]) == ["PM-KISAN", "पीएम-किसान"]


def test_prisma_v25_fallback_omits_model_and_v3_only_fields(monkeypatch):
    calls = []
    responses = [
        FakeResponse(status_code=400, text='{"success":false,"error":{"type":"INVALID_MODEL"}}'),
        FakeResponse(payload={"success": True, "transcript": "नमस्ते", "request_id": "fallback"}),
    ]
    monkeypatch.setattr(voice, "_dry_run", lambda: False)
    monkeypatch.setattr(voice, "_secret", lambda name: "test-key")
    monkeypatch.setattr(voice, "_env", lambda name, default="": {
        "PRISMA_V25_FALLBACK": "1", "PRISMA_V25_LANGUAGE_CODE": "hi-IN",
    }.get(name, default))
    monkeypatch.setattr(voice, "_post_with_retry", lambda *a, **k: (
        calls.append(k) or responses.pop(0)
    ))
    result = voice.transcribe(wav_bytes(), keyterms=["PM-KISAN"])
    assert result["request_id"] == "fallback"
    assert calls[0]["data"]["model"] == "prisma-v3.0"
    assert calls[1]["data"] == {"language_code": "hi-IN", "format": "transcribe"}


def test_prisma_rejects_audio_over_30_seconds(monkeypatch):
    monkeypatch.setattr(voice, "_dry_run", lambda: False)
    monkeypatch.setattr(voice, "_secret", lambda name: "test-key")
    monkeypatch.setattr(voice, "_post_with_retry", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("request must not be sent for long audio")))
    try:
        voice.transcribe(wav_bytes(30.1))
    except ValueError as exc:
        assert "30 seconds" in str(exc)
    else:
        raise AssertionError("Expected 30-second validation")


def test_timbre_request_uses_correct_model_and_voice(monkeypatch, tmp_path):
    calls = []
    audio = wav_bytes()
    monkeypatch.setattr(voice, "_dry_run", lambda: False)
    monkeypatch.setattr(voice, "_secret", lambda name: "test-key")
    monkeypatch.setattr(voice, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(voice, "_post_with_retry", lambda *a, **kwargs: (
        calls.append(kwargs) or FakeResponse(content=audio)
    ))
    output = voice.speak("Namaste", "en", use_cache=False)
    assert output[:4] == b"RIFF" and output[8:12] == b"WAVE"
    payload = calls[0]["json"]
    assert payload["model"] == "timbre-v2.5"
    assert payload["voice"] == "Kaveri"
    assert payload["language"] == "en-IN"


def test_only_supported_sentences_are_spoken(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda *args, **kwargs: [{
        "chunk_id": "c1", "scheme_id": "S", "lang": "en", "section": "Benefits",
        "text": "Eligible families receive Rs. 6000 per year.", "source_url": "https://example.gov.in",
        "similarity_score": 0.9,
    }])
    monkeypatch.setattr(pipeline, "generate_answer", lambda *args, **kwargs:
                        "Eligible families receive Rs. 6000 per year. Every family gets a car.")
    monkeypatch.setattr(pipeline, "verify_answer", lambda *args, **kwargs: {
        "sentences": [
            {"text": "Eligible families receive Rs. 6000 per year.", "label": "Supported"},
            {"text": "Every family gets a car.", "label": "Unsupported"},
        ], "groundedness": 0.5,
    })
    result = pipeline.answer_question("How much do families receive?", "en")
    assert result["status"] == "partial"
    assert "Rs. 6000" in result["spoken_text"]
    assert "gets a car" not in result["spoken_text"]
    assert pipeline.FALLBACK["en"] in result["spoken_text"]


def test_voice_pipeline_calls_prisma_then_timbre(monkeypatch):
    events = []
    monkeypatch.setattr(pipeline, "transcribe", lambda audio, keyterms=None: (
        events.append("prisma") or {"text": "How much is the scheme benefit?", "lang": "en",
                                    "detected_language_code": "en-IN", "request_id": "req"}
    ))
    monkeypatch.setattr(pipeline, "load_scheme_keyterms", lambda: ["PM-KISAN"])
    monkeypatch.setattr(pipeline, "retrieve", lambda *a, **k: [{
        "chunk_id": "x", "scheme_id": "S", "lang": "en", "section": "Benefits",
        "text": "Eligible families receive Rs. 6000 per year.",
        "source_url": "https://example.gov.in", "similarity_score": 0.9,
    }])
    monkeypatch.setattr(pipeline, "generate_answer", lambda *a, **k:
                        "Eligible families receive Rs. 6000 per year.")
    monkeypatch.setattr(pipeline, "verify_answer", lambda *a, **k: {
        "sentences": [{"text": "Eligible families receive Rs. 6000 per year.", "label": "Supported"}],
        "groundedness": 1.0,
    })
    monkeypatch.setattr(pipeline, "speak", lambda text, lang: events.append("timbre") or b"RIFF-WAVE")
    result = pipeline.answer_audio(b"voice-bytes", make_audio=True)
    assert events == ["prisma", "timbre"]
    assert result["status"] == "verified"
    assert result["spoken_audio"] == b"RIFF-WAVE"
    assert result["transcription"]["request_id"] == "req"
    assert "stt" in result["latency"] and "tts" in result["latency"]
