"""Dry-run smoke tests: no API keys, model downloads or network calls."""
import os
os.environ["DRY_RUN"] = "1"

from src.generate import generate_answer  # noqa: E402
from src.voice import speak, transcribe  # noqa: E402


def test_transcribe_dry_run():
    result = transcribe(b"test audio")
    assert result["lang"] == "hi" and "किसान" in result["text"]


def test_speak_dry_run_returns_wav():
    audio = speak("नमस्ते", "hi")
    assert audio[:4] == b"RIFF" and audio[8:12] == b"WAVE"


def test_generate_dry_run_uses_context_sentence():
    chunks = [{"chunk_id": "x", "lang": "en", "text": "Eligible families receive support. More details follow."}]
    assert generate_answer("Who is eligible?", chunks, "en") == "Eligible families receive support."


def test_generate_does_not_split_rs_abbreviation():
    chunks = [{"chunk_id": "x", "lang": "en", "text": "Farmers receive Rs. 6000 per year. Other details follow."}]
    assert generate_answer("How much?", chunks, "en") == "Farmers receive Rs. 6000 per year."


def test_generate_empty_context_returns_no_answer():
    assert generate_answer("question", [], "en") == "NO_ANSWER"
