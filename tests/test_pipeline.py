# real retrieval + fake LLM/speech (DRY_RUN, no API credits)
import os

os.environ["DRY_RUN"] = "1"

import pytest  # noqa: E402

from src.pipeline import FALLBACK, answer_question  # noqa: E402
from src.retrieve import retrieve  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def warm_up():
    """Load the model and index once, so tests are not slow one by one."""
    retrieve("test")


def test_english_question_is_verified():
    r = answer_question("Who can apply for PM-KISAN?", "en")
    assert r["status"] == "verified"
    assert r["verification"]["groundedness"] == 1.0
    assert r["spoken_text"] == r["answer"]


def test_hindi_question_is_verified():
    r = answer_question("पीएम किसान में कौन आवेदन कर सकता है?", "hi")
    assert r["status"] == "verified"


def test_unanswerable_question_is_refused():
    r = answer_question("What is the weather today?", "en")
    assert r["status"] == "refused"
    assert r["spoken_text"] == FALLBACK["en"]


def test_empty_question_is_refused():
    r = answer_question("   ", "hi")
    assert r["status"] == "refused"
    assert r["spoken_text"] == FALLBACK["hi"]


def test_result_has_contract_keys():
    r = answer_question("Who can apply?", "en")
    for key in ["query", "lang", "chunks", "answer", "verification",
                "spoken_text", "status", "latency"]:
        assert key in r