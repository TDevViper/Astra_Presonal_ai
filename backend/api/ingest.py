# api/ingest.py — Document ingestion endpoints
import os
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
ingest_bp = APIRouter()


@ingest_bp.get("/ingest/status")
def ingest_status(request: Request):
    """How many chunks are in the RAG index?"""
    try:
        from rag.vector_store import count
        from rag.watcher import DOCS_DIR

        files = [
            f for f in os.listdir(DOCS_DIR) if os.path.isfile(os.path.join(DOCS_DIR, f))
        ]
        return JSONResponse(content=
            {
                "chunks_indexed": count(),
                "docs_folder": DOCS_DIR,
                "files_in_folder": files,
            }
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@ingest_bp.post("/ingest/scan")
def ingest_scan(request: Request):
    """Manually trigger a scan of the docs folder."""
    try:
        from rag.watcher import ingest_now

        results = ingest_now()
        total = sum(v for v in results.values() if isinstance(v, int))
        return JSONResponse(content={"status": "ok", "files": results, "total_chunks": total})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@ingest_bp.post("/ingest/text")
def ingest_text(request: Request):
    """Ingest raw text directly. POST {text, source}"""
    try:
        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        text = data.get("text", "").strip()
        source = data.get("source", "manual")
        if not text:
            return JSONResponse(content={"error": "No text provided"}, status_code=400)
        from rag.ingest import ingest_text as _ingest

        n = _ingest(text, source=source)
        return JSONResponse(content={"status": "ok", "chunks": n, "source": source})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@ingest_bp.post("/ingest/search")
def ingest_search(request: Request):
    """Search the RAG index. POST {query, top_k}"""
    try:
        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        query = data.get("query", "").strip()
        top_k = int(data.get("top_k", 5))
        if not query:
            return JSONResponse(content={"error": "No query provided"}, status_code=400)
        from rag.embeddings import embed
        from rag.vector_store import search
        from rag.reranker import rerank

        results = search(embed(query), top_k=top_k * 2)
        reranked = rerank(query, results, top_k=top_k)
        return JSONResponse(content={"results": reranked, "count": len(reranked)})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500