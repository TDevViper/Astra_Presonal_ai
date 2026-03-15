# tools/rag_tool.py — RAG search as a ReAct tool
from tools.registry import tool


@tool("rag_search", "search ingested documents and personal knowledge base for relevant context")
def rag_search(query: str) -> str:
    try:
        from rag.embeddings import embed
        from rag.vector_store import search
        from rag.reranker import rerank
        results  = search(embed(query), top_k=6)
        reranked = rerank(query, results, top_k=3)
        if not reranked:
            return "No relevant documents found in knowledge base."
        lines = []
        for r in reranked:
            source = r.get("source", "unknown")
            text   = r.get("text", "")[:300]
            lines.append(f"[{source}] {text}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"RAG search error: {e}"
