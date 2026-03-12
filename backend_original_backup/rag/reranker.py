# rag/reranker.py — Cross-encoder reranking
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("BAAI/bge-reranker-base")
    return _reranker

def rerank(query: str, chunks: list[dict], top_k: int = 3) -> list[dict]:
    if not chunks:
        return []
    try:
        reranker = _get_reranker()
        pairs    = [(query, c["text"]) for c in chunks]
        scores   = reranker.predict(pairs)
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])
        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]
    except Exception:
        return chunks[:top_k]
