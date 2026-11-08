# runs the real NLI model locally (no API credits; first run downloads ~1 GB)
from src.verify import split_sentences, verify_answer

EN = [{"chunk_id": "c1", "lang": "en",
       "text": "PM-KISAN gives eligible farmer families six thousand rupees per year in three instalments."}]
HI = [{"chunk_id": "c2", "lang": "hi",
       "text": "पीएम-किसान योजना में पात्र किसान परिवारों को प्रति वर्ष छह हज़ार रुपये तीन किस्तों में मिलते हैं।"}]


def test_split_hindi_and_english():
    assert len(split_sentences("यह एक वाक्य है। यह दूसरा है।")) == 2
    assert len(split_sentences("One sentence. Two sentences.")) == 2


def test_supported_english():
    r = verify_answer("Eligible farmers get six thousand rupees per year.", EN, "en")
    assert r["sentences"][0]["label"] == "Supported"


def test_unsupported_english():
    r = verify_answer("The scheme gives a free tractor to every farmer.", EN, "en")
    assert r["sentences"][0]["label"] != "Supported"


def test_supported_hindi():
    r = verify_answer("पात्र किसान परिवारों को हर साल छह हज़ार रुपये मिलते हैं।", HI, "hi")
    assert r["sentences"][0]["label"] == "Supported"


def test_empty_answer():
    r = verify_answer("", EN, "en")
    assert r["groundedness"] == 0.0 and r["sentences"] == []


def test_groundedness_is_a_fraction():
    r = verify_answer("Farmers get six thousand rupees a year. The scheme gives a car to every farmer.", EN, "en")
    assert 0.0 <= r["groundedness"] <= 1.0