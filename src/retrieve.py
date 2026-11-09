"""Multilingual E5 embeddings and FAISS retrieval with relevance-aware language preference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data" / "chunks.jsonl"
INDEX_DIR = ROOT / "index"
INDEX_PATH = INDEX_DIR / "faiss.index"
METADATA_PATH = INDEX_DIR / "chunks.jsonl"
MANIFEST_PATH = INDEX_DIR / "manifest.json"
MODEL_NAME = "intfloat/multilingual-e5-base"
TOP_K = 8
_model = None
_index = None
_chunks = None


def load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def load_chunks() -> list[dict[str, Any]]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing {CHUNKS_PATH}; run `python -m src.ingest` first.")
    result: list[dict[str, Any]] = []
    with CHUNKS_PATH.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid chunks.jsonl line {line_number}: {exc}") from exc
            required = {"chunk_id", "scheme_id", "lang", "section", "text", "source_url"}
            missing = required - item.keys()
            if missing:
                raise ValueError(f"Chunk line {line_number} missing fields: {sorted(missing)}")
            item["lang"] = "hi" if str(item["lang"]).lower().startswith("hi") else "en"
            item["text"] = str(item["text"]).strip()
            if item["text"]:
                result.append(item)
    if not result:
        raise ValueError("data/chunks.jsonl has no non-empty chunks")
    ids = [item["chunk_id"] for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk_id values found; rerun ingestion after fixing the source data")
    return result


def _corpus_signature(chunks: list[dict]) -> str:
    digest = hashlib.sha256(MODEL_NAME.encode("utf-8"))
    fields = ("chunk_id", "scheme_id", "lang", "section", "text", "source_url",
              "name_en", "name_hi", "retrieved_on")
    for item in chunks:
        for field in fields:
            digest.update(str(item.get(field, "")).encode("utf-8"))
            digest.update(b"\0")
    return digest.hexdigest()


def _passage_text(item: dict) -> str:
    name = item.get("name_hi") if item.get("lang") == "hi" else item.get("name_en")
    name = name or item.get("name_en") or item.get("name_hi") or item.get("scheme_id", "")
    return f"passage: Scheme: {name}. Section: {item.get('section', '')}. {item['text']}"


def build_index() -> None:
    global _index, _chunks
    import faiss
    import numpy as np

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    passages = [_passage_text(item) for item in chunks]
    vectors = load_model().encode(
        passages, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise RuntimeError("Embedding model returned an unexpected vector matrix")
    index = faiss.IndexFlatIP(int(vectors.shape[1]))
    index.add(vectors)
    faiss.write_index(index, str(INDEX_PATH))
    with METADATA_PATH.open("w", encoding="utf-8") as stream:
        for item in chunks:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    MANIFEST_PATH.write_text(json.dumps({
        "model": MODEL_NAME,
        "signature": _corpus_signature(chunks),
        "count": len(chunks),
        "dimension": int(vectors.shape[1]),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    _index, _chunks = index, chunks
    print(f"FAISS index built: {index.ntotal} vectors; dimension={vectors.shape[1]}")


def _load_index():
    global _index, _chunks
    import faiss

    current_chunks = load_chunks()
    expected_signature = _corpus_signature(current_chunks)
    valid = INDEX_PATH.exists() and METADATA_PATH.exists() and MANIFEST_PATH.exists()
    if valid:
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            metadata = [json.loads(line) for line in METADATA_PATH.read_text(encoding="utf-8").splitlines()
                        if line.strip()]
            valid = (
                manifest.get("model") == MODEL_NAME
                and manifest.get("signature") == expected_signature
                and int(manifest.get("count", -1)) == len(current_chunks)
                and [x.get("chunk_id") for x in metadata] == [x.get("chunk_id") for x in current_chunks]
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            valid = False
    if not valid:
        build_index()
    elif _index is None or _chunks is None:
        loaded_index = faiss.read_index(str(INDEX_PATH))
        metadata = [json.loads(line) for line in METADATA_PATH.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
        if loaded_index.ntotal != len(current_chunks) or loaded_index.ntotal != len(metadata):
            build_index()
        else:
            _index, _chunks = loaded_index, metadata
    if _index is None or _chunks is None:
        raise RuntimeError("Could not load or build the FAISS index")
    return _index, _chunks

def detect_scheme(query: str) -> str | None:
    """Identify a government scheme mentioned in the query."""

    q = (query or "").casefold().replace("_", " ").strip()

    scheme_aliases = {
        "PMKISAN": [
            "pm-kisan", "pm kisan", "pmkisan", "kisan samman nidhi",
            "प्रधानमंत्री किसान सम्मान निधि", "पीएम किसान",
        ],
        "PMUY": [
            "pmuy", "ujjwala", "pradhan mantri ujjwala",
            "प्रधानमंत्री उज्ज्वला", "उज्ज्वला योजना",
        ]
    }

    for scheme_id, aliases in scheme_aliases.items():
        if any(alias in q for alias in aliases):
            return scheme_id

    return None


def retrieve(query: str, k: int = TOP_K, lang: str | None = None,
             *, top_k: int | None = None) -> list[dict[str, Any]]:
    """Return relevant chunks with soft language and recognized-scheme preferences.

    Preferences adjust ranking only; they never remove otherwise relevant passages.
    `top_k` remains an alias for older evaluation scripts.
    """
    if top_k is not None:
        k = top_k
    if not query or not query.strip() or k <= 0:
        return []
    import numpy as np

    index, chunks = _load_index()
    scheme_id = detect_scheme(query)
    vector = load_model().encode(
        [f"query: {query.strip()}"], convert_to_numpy=True, normalize_embeddings=True
    )
    vector = np.asarray(vector, dtype=np.float32)
    candidate_count = min(index.ntotal, max(k * 4, k))
    scores, positions = index.search(vector, candidate_count)

    ranked: list[dict[str, Any]] = []
    for score, position in zip(scores[0], positions[0]):
        position = int(position)
        if position < 0:
            continue
        item = dict(chunks[position])
        raw_score = float(score)
        preferred_language = lang in {"hi", "en"} and item.get("lang") == lang
        scheme_match = bool(scheme_id and str(item.get("scheme_id", "")).casefold() == scheme_id.casefold())
        # These bonuses only reorder candidates; raw similarity remains available
        # for relevance thresholds and diagnostics.
        adjusted_score = raw_score + (0.025 if preferred_language else 0.0)
        adjusted_score += 0.05 if scheme_match else 0.0
        item["score"] = raw_score
        item["similarity_score"] = raw_score
        item["language_match"] = bool(preferred_language)
        item["scheme_match"] = scheme_match
        item["ranking_score"] = adjusted_score
        ranked.append(item)

    ranked.sort(key=lambda item: item["ranking_score"], reverse=True)

    # Avoid filling the whole context with identical duplicate text records.
    selected: list[dict[str, Any]] = []
    seen_content: set[tuple[str, str]] = set()
    for item in ranked:
        signature = (str(item.get("scheme_id", "")), " ".join(str(item.get("text", "")).casefold().split()))
        if signature in seen_content:
            continue
        seen_content.add(signature)
        selected.append(item)
        if len(selected) >= k:
            break
    return selected

if __name__ == "__main__":
    build_index()
    print(json.dumps(retrieve("How much money do farmers receive under PM-KISAN?", lang="en"),
                     ensure_ascii=False, indent=2))
