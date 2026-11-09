
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent
CHUNKS_PATH = BASE_DIR / "data" / "chunks.jsonl"
INDEX_DIR = BASE_DIR / "index"
INDEX_PATH = INDEX_DIR / "faiss.index"
METADATA_PATH = INDEX_DIR / "chunks.jsonl"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 4

_model = None
_index = None
_chunks = None

def load_model():
    """Load the embedding model once."""
    global _model

    if _model is None:
        print("Loading multilingual embedding model...")
        _model = SentenceTransformer(MODEL_NAME)
        print("Model loaded successfully.")

    return _model


def load_chunks():
    """Load processed scheme chunks."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError("Run src/ingest.py first.")

    chunks = []

    with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(json.loads(line))

    if not chunks:
        raise ValueError("No chunks available.")

    return chunks


def build_index():
    """Generate embeddings and create a FAISS index."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    chunks = load_chunks()
    model = load_model()

    texts = [
        f'{chunk["name_en"]}. {chunk["section"]}. {chunk["text"]}'
        for chunk in chunks
    ]

    print(f"Generating embeddings for {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    embeddings = np.asarray(embeddings, dtype="float32")

    # Normalized vectors + inner product = cosine similarity
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))

    # Preserve the metadata in the same order as the vectors
    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print("\nFAISS INDEX CREATED")
    print("Vectors:", index.ntotal)
    print("Dimensions:", dimension)

    global _index, _chunks
    _index, _chunks = None, None  # force reload after rebuild

def _load_index():
    """Load FAISS index and metadata once, then reuse."""
    global _index, _chunks

    if _index is None or _chunks is None:
        if not INDEX_PATH.exists() or not METADATA_PATH.exists():
            build_index()

        _index = faiss.read_index(str(INDEX_PATH))
        with open(METADATA_PATH, "r", encoding="utf-8") as file:
            _chunks = [json.loads(line) for line in file if line.strip()]

    return _index, _chunks

def detect_scheme(query):
    """Identify a government scheme mentioned in the query."""

    q = query.lower().replace("_", " ").strip()

    scheme_aliases = {
        "PMKISAN": [
            "pm-kisan", "pm kisan", "pmkisan",
            "kisan samman nidhi"
        ],
        "PMUY": [
            "pmuy", "ujjwala", "pradhan mantri ujjwala"
        ]
    }

    for scheme_id, aliases in scheme_aliases.items():
        if any(alias in q for alias in aliases):
            return scheme_id

    return None

def retrieve(query, k=TOP_K, lang=None):
    """Find semantically similar chunks, prioritizing the requested scheme."""

    if not query or not query.strip():
        return []

    model = load_model()
    index, chunks = _load_index()

    # Identify the scheme mentioned in the question
    scheme_id = detect_scheme(query)

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_embedding = np.asarray(query_embedding, dtype="float32")

    # Search all chunks
    scores, indices = index.search(
        query_embedding,
        index.ntotal
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        chunk = chunks[idx]

        # Filter by language
        if lang and chunk.get("lang") != lang:
            continue

        # Filter by scheme when one is identified
        if scheme_id and chunk.get("scheme_id") != scheme_id:
            continue

        result = chunk.copy()
        result["similarity_score"] = float(score)
        results.append(result)

        if len(results) >= k:
            break

    return results

if __name__ == "__main__":
    build_index()

    test_query = "How much money do farmers receive under PM KISAN?"

    print("\nTEST QUERY:", test_query)

    results = retrieve(test_query)

    for rank, result in enumerate(results, start=1):
        print(f"\nResult {rank}")
        print("Scheme:", result["name_en"])
        print("Section:", result["section"])
        print("Similarity:", round(result["similarity_score"], 4))
        print("Text:", result["text"])
        print("Source:", result["source_url"])
