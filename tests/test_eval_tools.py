"""Offline tests for evaluation helpers and the held-out verifier threshold tuner."""
import unicodedata

from eval.text_utils import normalise
from eval.tune_thresholds import flag_metrics, predict, split_dev_test, three_class, tune


def sample_data():
    rows = []
    for index in range(10):
        rows.append({"sid": f"s{index}", "true": "Supported", "entail": 0.95, "contra": 0.01})
        rows.append({"sid": f"u{index}", "true": "Unsupported", "entail": 0.05, "contra": 0.10})
        rows.append({"sid": f"c{index}", "true": "Contradicted", "entail": 0.02, "contra": 0.95})
    return rows


def test_predict_three_classes():
    assert predict(0.9, 0.0, 0.6, 0.5) == "Supported"
    assert predict(0.1, 0.8, 0.6, 0.5) == "Contradicted"
    assert predict(0.1, 0.1, 0.6, 0.5) == "Unsupported"


def test_tuner_has_perfect_synthetic_separation():
    chosen = tune(sample_data())
    assert chosen["dev_flag_metrics"]["f1"] == 1.0
    assert 0.3 <= chosen["T_ENT"] <= 0.95


def test_dev_test_split_is_stable_and_disjoint():
    data = sample_data()
    dev1, test1 = split_dev_test(data, seed=42)
    dev2, test2 = split_dev_test(data, seed=42)
    assert [x["sid"] for x in dev1] == [x["sid"] for x in dev2]
    assert not ({x["sid"] for x in dev1} & {x["sid"] for x in test1})
    assert len(dev1) + len(test1) == len(data)


def test_unicode_normalisation_preserves_hindi_vowel_marks():
    assert unicodedata.category("ा").startswith("M")
    assert normalise("पीएम किसान, योजना।") == "पीएम किसान योजना"
    assert normalise(" Hello, WORLD! ") == "hello world"
