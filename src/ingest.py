
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "data" / "schemes.jsonl"
CHUNKS_PATH = BASE_DIR / "data" / "chunks.jsonl"
KEYTERMS_PATH = BASE_DIR / "data" / "keyterms.json"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def normalize_text(text):
    """Remove unnecessary whitespace while preserving the words."""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_into_chunks(text, chunk_size=CHUNK_SIZE,
                      overlap=CHUNK_OVERLAP):
    """Split text into overlapping word-based chunks."""
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        if end == len(words):
            break

        start = end - overlap

    return chunks


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Run csv_to_jsonl.py before running ingest.py"
        )

    records = []

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    all_chunks = []
    keyterms = {}

    for record in records:
        text = normalize_text(record["text"])
        chunks = split_into_chunks(text)

        for i, chunk_text in enumerate(chunks):
            chunk = {
                "chunk_id": f'{record["scheme_id"]}_{record["lang"]}_{record["section"]}_{i}',
                "scheme_id": record["scheme_id"],
                "name_en": record["name_en"],
                "name_hi": record["name_hi"],
                "lang": record["lang"],
                "section": record["section"],
                "text": chunk_text,
                "source_url": record["source_url"]
            }

            all_chunks.append(chunk)

        terms = keyterms.setdefault(record["scheme_id"], [])
        terms.extend([
            record["name_en"],
            record["section"],
            record["scheme_id"]
        ])

    # Remove duplicate keywords
    keyterms = {
        scheme_id: sorted(set(terms))
        for scheme_id, terms in keyterms.items()
    }

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    with open(KEYTERMS_PATH, "w", encoding="utf-8") as f:
        json.dump(keyterms, f, ensure_ascii=False, indent=4)

    print("INGESTION COMPLETE")
    print(f"Input records: {len(records)}")
    print(f"Generated chunks: {len(all_chunks)}")
    print(f"Saved chunks: {CHUNKS_PATH}")
    print(f"Saved keyterms: {KEYTERMS_PATH}")


if __name__ == "__main__":
    main()
