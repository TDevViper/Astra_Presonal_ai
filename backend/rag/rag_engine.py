# rag/rag_engine.py — Main RAG interface
from rag.retriever import hybrid_search
from rag.reranker import rerank
from rag.vector_store import count


def query_rag(query: str, top_k: int = 3, use_reranker: bool = True) -> str:
    if count() == 0:
        return ""
    results = hybrid_search(query, top_k=top_k * 2)
    if not results:
        return ""
    if use_reranker and len(results) > 1:
        results = rerank(query, results, top_k=top_k)
    else:
        results = results[:top_k]
    if not results:
        return ""
    context_parts = []
    for r in results:
        source = r.get("source", "unknown")
        text = r["text"].strip()
        context_parts.append(f"[{source}]\n{text}")
    return "\n\n---\n\n".join(context_parts)


def should_use_rag(query: str) -> bool:
    if count() == 0:
        return False
    q = query.lower().strip()
    skip_exact = ["hi", "hello", "hey", "bye", "thanks", "what time", "how are you"]
    if any(q == s for s in skip_exact):
        return False
    if len(q.split()) < 3:
        return False
    personal = [
        "my name",
        "my hobby",
        "hobbies",
        "i love",
        "i like",
        "i prefer",
        "my favorite",
        "my colour",
        "my color",
        "my language",
        "where i live",
        "who am i",
        "what do i",
        "do i like",
        "my task",
        "my reminder",
        "my project",
        "what is my",
    ]
    if any(p in q for p in personal):
        return False
    return True
