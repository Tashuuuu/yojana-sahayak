# offline tests for the new helper functions (no model download, no API credits)
import os

os.environ["DRY_RUN"] = "1"      # must be set BEFORE importing our modules

from src.generate import to_english   # noqa: E402
from src.verify import premises_for   # noqa: E402


def test_premises_include_whole_chunk_sentences_and_pairs():
    text = "One is here. Two is here. Three is here."
    premises = premises_for(text)
    assert text in premises
    assert "Two is here." in premises
    assert "One is here. Two is here." in premises
    assert len(premises) == len(set(premises))


def test_single_sentence_chunk_has_one_premise():
    assert premises_for("Only one sentence here.") == ["Only one sentence here."]


def test_to_english_dry_run_returns_input():
    assert to_english("पीएम किसान क्या है?") == "पीएम किसान क्या है?"