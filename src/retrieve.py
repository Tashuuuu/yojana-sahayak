
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


def retrieve(query, top_k=TOP_K):
    """Find the most semantically similar chunks."""
    if not query or not query.strip():
        return []

    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        build_index()

    model = load_model()
    index = faiss.read_index(str(INDEX_PATH))

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        chunks = [
            json.loads(line)
            for line in file if line.strip()
        ]

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    query_embedding = np.asarray(
        query_embedding, dtype="float32"
    )

    k = min(top_k, index.ntotal)
    scores, indices = index.search(query_embedding, k)

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        result = chunks[idx].copy()
        result["similarity_score"] = float(score)
        results.append(result)

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
