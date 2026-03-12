# rag/retriever.py — Hybrid search: FAISS + BM25
import numpy as np
from rank_bm25 import BM25Okapi
from rag.embeddings import embed
from rag.vector_store import search, _load_meta

def _bm25_search(query: str, top_k: int = 5) -> list[dict]:
    meta = _load_meta()
    if not meta:
        return []
    corpus = [m["text"].lower().split() for m in meta]
    bm25   = BM25Okapi(corpus)
    scores = bm25.get_scores(query.lower().split())
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        {**meta[i], "score": float(scores[i]), "method": "bm25"}
        for i in top_indices if scores[i] > 0
    ]

def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    query_vec   = embed(query)
    vec_results = search(query_vec, top_k=top_k)
    for r in vec_results:
        r["method"] = "vector"
    bm25_results = _bm25_search(query, top_k=top_k)
    # Merge — deduplicate by text
    seen    = set()
    merged  = []
    for r in vec_results + bm25_results:
        key = r["text"][:80]
        if key not in seen:
            seen.add(key)
            merged.append(r)
    # Sort by score descending
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:top_k]
