"""Timbre cache test using a mocked HTTP response."""
import io
import wave

import src.voice as voice


class FakeResponse:
    status_code = 200
    ok = True
    headers = {"Content-Type": "audio/wav"}

    def __init__(self, content):
        self.content = content
        self.text = ""

    def raise_for_status(self):
        pass


def make_wav():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        out.writeframes(b"\x00\x00" * 2400)
    return buffer.getvalue()


def test_tts_response_is_cached(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(voice, "_dry_run", lambda: False)
    monkeypatch.setattr(voice, "_secret", lambda name: "test-key")
    monkeypatch.setattr(voice, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(voice, "_post_with_retry", lambda *a, **k: (
        calls.append(1) or FakeResponse(make_wav())
    ))
    first = voice.speak("नमस्ते", "hi")
    second = voice.speak("नमस्ते", "hi")
    assert first == second
    assert first[:4] == b"RIFF" and first[8:12] == b"WAVE"
    assert len(calls) == 1


def test_empty_tts_text_is_rejected():
    try:
        voice.speak("   ", "hi")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("Expected empty-text validation")
