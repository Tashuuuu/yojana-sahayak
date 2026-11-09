"""Validate bilingual scheme records and build chunks/keyterms for Yojana Sahayak."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "schemes.jsonl"
CHUNKS_PATH = ROOT / "data" / "chunks.jsonl"
KEYTERMS_PATH = ROOT / "data" / "keyterms.json"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
REQUIRED_FIELDS = {
    "scheme_id", "name_en", "name_hi", "lang", "section", "text", "source_url", "retrieved_on"
}


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "section"


def make_chunk_id(scheme_id: str, lang: str, section: str, index: int) -> str:
    """Use language in the ID; English/Hindi records often share section names."""
    return f"{_slug(scheme_id)}__{lang}__{_slug(section)}__{index}"


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE,
                      overlap: int = CHUNK_OVERLAP) -> list[str]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def load_records() -> list[dict[str, Any]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Scheme dataset not found: {INPUT_PATH}")
    records: list[dict[str, Any]] = []
    with INPUT_PATH.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in schemes.jsonl line {line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Line {line_number} must contain a JSON object")
            missing = REQUIRED_FIELDS - record.keys()
            if missing:
                raise ValueError(f"Line {line_number} is missing fields: {sorted(missing)}")
            clean = {key: normalize_text(value) for key, value in record.items()}
            language = clean["lang"].lower()
            if language not in {"hi", "en", "hi-in", "en-in"}:
                raise ValueError(f"Line {line_number}: lang must be hi or en, got {clean['lang']!r}")
            clean["lang"] = "hi" if language.startswith("hi") else "en"
            if not clean["scheme_id"] or not clean["text"] or not clean["section"]:
                raise ValueError(f"Line {line_number}: scheme_id, section and text cannot be empty")
            if not clean["source_url"].startswith(("https://", "http://")):
                raise ValueError(f"Line {line_number}: source_url must be an official HTTP(S) URL")
            records.append(clean)
    if not records:
        raise ValueError("schemes.jsonl contains no records")
    return records


def main() -> None:
    records = load_records()
    chunks: list[dict[str, Any]] = []
    keyterms: dict[str, set[str]] = {}
    seen_ids: set[str] = set()

    for record in records:
        pieces = split_into_chunks(record["text"])
        for index, piece in enumerate(pieces):
            chunk_id = make_chunk_id(record["scheme_id"], record["lang"], record["section"], index)
            if chunk_id in seen_ids:
                raise ValueError(
                    f"Duplicate chunk id {chunk_id!r}. Check for duplicate scheme/language/section records."
                )
            seen_ids.add(chunk_id)
            chunks.append({
                "chunk_id": chunk_id,
                "scheme_id": record["scheme_id"],
                "name_en": record["name_en"],
                "name_hi": record["name_hi"],
                "lang": record["lang"],
                "section": record["section"],
                "text": piece,
                "source_url": record["source_url"],
                "retrieved_on": record["retrieved_on"],
            })
        terms = keyterms.setdefault(record["scheme_id"], set())
        terms.update(x for x in (record["scheme_id"], record["name_en"], record["name_hi"]) if x)
        aliases = record.get("aliases", "")
        if aliases:
            terms.update(part.strip() for part in re.split(r"[,;|]", aliases) if part.strip())

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHUNKS_PATH.open("w", encoding="utf-8") as stream:
        for item in chunks:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    KEYTERMS_PATH.write_text(
        json.dumps({key: sorted(values) for key, values in sorted(keyterms.items())},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    language_counts = {lang: sum(item["lang"] == lang for item in records) for lang in ("en", "hi")}
    print("INGESTION COMPLETE")
    print(f"Scheme records/sections: {len(records)}")
    print(f"Unique schemes: {len(keyterms)}")
    print(f"Sections by language: {language_counts}")
    print(f"Chunks: {len(chunks)}")
    print(f"Saved: {CHUNKS_PATH}")
    print(f"Saved: {KEYTERMS_PATH}")
    if len(keyterms) < 20:
        print(f"WARNING: target is 20 schemes; current dataset contains {len(keyterms)}.")
    if any(not ({"en", "hi"} <= {r["lang"] for r in records if r["scheme_id"] == scheme})
           for scheme in keyterms):
        print("WARNING: at least one scheme does not yet have both English and Hindi sections.")


if __name__ == "__main__":
    main()
