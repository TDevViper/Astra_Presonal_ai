# rag/vector_store.py — FAISS index with metadata
import os
import json
import faiss
import numpy as np
from datetime import datetime

STORE_DIR  = os.path.join(os.path.dirname(__file__), "..", "memory", "vector_store")
INDEX_PATH = os.path.join(STORE_DIR, "index.faiss")
META_PATH  = os.path.join(STORE_DIR, "metadata.json")
DIM        = 384

os.makedirs(STORE_DIR, exist_ok=True)

def _load_index():
    if os.path.exists(INDEX_PATH):
        return faiss.read_index(INDEX_PATH)
    return faiss.IndexFlatIP(DIM)  # Inner product for normalized vecs = cosine similarity

def _load_meta() -> list:
    if os.path.exists(META_PATH):
        with open(META_PATH) as f:
            return json.load(f)
    return []

def add_chunks(chunks: list[str], embeddings: np.ndarray, source: str, tags: list[str] = None):
    index = _load_index()
    meta  = _load_meta()
    index.add(embeddings.astype(np.float32))
    for chunk in chunks:
        meta.append({
            "text":      chunk,
            "source":    source,
            "tags":      tags or [],
            "timestamp": datetime.now().isoformat()
        })
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

def search(query_vec: np.ndarray, top_k: int = 5) -> list[dict]:
    index = _load_index()
    meta  = _load_meta()
    if index.ntotal == 0:
        return []
    scores, indices = index.search(query_vec.reshape(1, -1).astype(np.float32), min(top_k, index.ntotal))
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and idx < len(meta):
            results.append({**meta[idx], "score": float(score)})
    return results

def count() -> int:
    return _load_index().ntotal
