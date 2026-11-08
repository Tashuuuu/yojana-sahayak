# tests/test_voice_cache.py — free: proves a repeated sentence is not sent to Gnani twice (the network is faked)
import src.voice as voice


class FakeResponse:
    status_code = 200
    content = b"RIFF-fake-audio"

    def raise_for_status(self):
        pass


def test_speak_is_cached(tmp_path, monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse()

    monkeypatch.setattr(voice, "DRY_RUN", False)      # other tests import voice in dry-run mode
    monkeypatch.setattr(voice, "TTS_KEY", "test-key")
    monkeypatch.setattr(voice, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(voice.requests, "post", fake_post)

    first = voice.speak("आपका आवेदन स्वीकार किया गया है।", "hi")
    second = voice.speak("आपका आवेदन स्वीकार किया गया है।", "hi")
    assert first == second == b"RIFF-fake-audio"
    assert len(calls) == 1                             # the second call came from the cache


def test_empty_text_does_not_call_the_service(monkeypatch):
    def no_call(*args, **kwargs):
        raise AssertionError("the service must not be called for empty text")

    monkeypatch.setattr(voice, "DRY_RUN", False)
    monkeypatch.setattr(voice.requests, "post", no_call)
    assert voice.speak("   ", "hi")[:4] == b"RIFF"