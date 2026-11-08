
import json
import pandas as pd
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "schemes.csv"
JSONL_PATH = BASE_DIR / "data" / "schemes.jsonl"

REQUIRED_COLUMNS = [
    "scheme_id", "name_en", "name_hi", "lang",
    "section", "text", "source_url", "retrieved_on"
]


def convert_csv_to_jsonl():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH).fillna("")

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    records = []

    for _, row in df.iterrows():
        record = {
            "scheme_id": str(row["scheme_id"]).strip(),
            "name_en": str(row["name_en"]).strip(),
            "name_hi": str(row["name_hi"]).strip(),
            "lang": str(row["lang"]).strip(),
            "section": str(row["section"]).strip(),
            "text": str(row["text"]).strip(),
            "source_url": str(row["source_url"]).strip(),
            "retrieved_on": str(row["retrieved_on"]).strip()
        }

        if not record["scheme_id"] or not record["text"]:
            continue

        records.append(record)

    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Conversion successful: {len(records)} records")
    print(f"Saved to: {JSONL_PATH}")


if __name__ == "__main__":
    convert_csv_to_jsonl()
