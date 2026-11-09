"""Small language and verifier helper tests."""
import os
os.environ["DRY_RUN"] = "1"

from src.generate import to_english  # noqa: E402
from src.verify import premises_for  # noqa: E402


def test_premises_include_whole_text_sentences_and_pairs():
    source = "One fact. Two facts. Three facts."
    premises = premises_for(source)
    assert source in premises
    assert "One fact. Two facts." in premises
    assert len(premises) == len(set(premises))


def test_to_english_dry_run_is_passthrough():
    assert to_english("पीएम किसान क्या है?") == "पीएम किसान क्या है?"
