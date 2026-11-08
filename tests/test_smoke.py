# runs in dry-run mode, costs no credits
import os

os.environ["DRY_RUN"] = "1"      # must be set BEFORE importing our modules

from src.generate import generate_answer   # noqa: E402
from src.voice import speak, transcribe     # noqa: E402


def test_transcribe_dry_run():
    result = transcribe(b"fake audio bytes")
    assert result["lang"] == "hi"
    assert "किसान" in result["text"]


def test_speak_dry_run_returns_wav():
    audio = speak("नमस्ते", "hi")
    assert audio[:4] == b"RIFF"                # every WAV file starts with RIFF


def test_generate_answer_dry_run():
    assert generate_answer("Who can apply?", [], "en").startswith("Eligible")
    assert generate_answer("What is the weather?", [], "en") == "NO_ANSWER"