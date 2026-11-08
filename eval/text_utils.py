# eval/text_utils.py — small text helpers shared by the evaluation scripts and tests
import unicodedata


def normalise(text: str) -> str:
    """Lowercase, drop punctuation and symbols (including the Hindi danda), collapse spaces.
    Do NOT use the regex \\w for this: it does not treat Hindi vowel signs as letters and would delete them."""
    text = unicodedata.normalize("NFC", text.lower())
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith(("P", "S")))
    return " ".join(text.split())