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


def test_generate_answer_dry_run_uses_chunk_text():
    chunks = [{
        "chunk_id": "T_0",
        "lang": "en",
        "text": "Eligible farmer families receive six thousand rupees per year. Money comes in three instalments.",
    }]
    answer = generate_answer("Who can apply?", chunks, "en")
    assert answer == "Eligible farmer families receive six thousand rupees per year."


def test_generate_answer_dry_run_prefers_same_language():
    chunks = [
        {"chunk_id": "T_en", "lang": "en", "text": "English sentence one. English sentence two."},
        {"chunk_id": "T_hi", "lang": "hi", "text": "हिंदी वाक्य एक। हिंदी वाक्य दो।"},
    ]
    assert generate_answer("पात्रता क्या है?", chunks, "hi") == "हिंदी वाक्य एक।"


def test_generate_answer_dry_run_no_chunks():
    assert generate_answer("Who can apply?", [], "en") == "NO_ANSWER"