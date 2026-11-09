"""Unicode-safe evaluation text normalisation (preserves Hindi combining marks)."""
from __future__ import annotations

import unicodedata


def normalise(text: str) -> str:
    value = unicodedata.normalize("NFC", (text or "").lower())
    value = "".join(char for char in value
                    if not unicodedata.category(char).startswith(("P", "S")))
    return " ".join(value.split())
