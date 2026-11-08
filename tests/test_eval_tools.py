# tests/test_eval_tools.py — free tests for the evaluation helpers (no models, no credits)
import unicodedata

from eval.text_utils import normalise
from eval.tune_thresholds import flag_metrics, predict, split_dev_test, three_class, tune


def make_data():
    data = []
    for i in range(10):
        data.append({"sid": f"a{i}", "true": "Supported", "entail": 0.90 + i * 0.005, "contra": 0.02})
        data.append({"sid": f"b{i}", "true": "Unsupported", "entail": 0.05 + i * 0.01, "contra": 0.10})
        data.append({"sid": f"c{i}", "true": "Contradicted", "entail": 0.03, "contra": 0.80 + i * 0.01})
    return data


def test_predict_rules():
    assert predict(0.9, 0.0, 0.6, 0.5) == "Supported"
    assert predict(0.1, 0.8, 0.6, 0.5) == "Contradicted"
    assert predict(0.1, 0.1, 0.6, 0.5) == "Unsupported"


def test_perfect_separation_gives_perfect_scores():
    m = flag_metrics(make_data(), 0.6, 0.5)
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0
    assert three_class(make_data(), 0.6, 0.5)["accuracy"] == 1.0


def test_tune_picks_threshold_between_the_classes():
    chosen = tune(make_data())
    assert 0.20 <= chosen["T_ENT"] <= 0.95
    assert chosen["dev_flag_metrics"]["f1"] == 1.0


def test_split_is_disjoint_stable_and_complete():
    data = make_data()
    dev1, test1 = split_dev_test(data, seed=42)
    dev2, test2 = split_dev_test(data, seed=42)
    assert [d["sid"] for d in dev1] == [d["sid"] for d in dev2]
    assert not ({d["sid"] for d in dev1} & {d["sid"] for d in test1})
    assert len(dev1) + len(test1) == len(data)


def test_hindi_normalisation_keeps_vowel_signs():
    assert unicodedata.category("ा").startswith("M")          # a vowel sign: regex \w would delete it
    assert normalise("पीएम किसान, योजना।") == "पीएम किसान योजना"
    assert normalise("  Hello,   WORLD! ") == "hello world"