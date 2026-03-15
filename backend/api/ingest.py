# api/ingest.py — Document ingestion endpoints
import os
import logging
from flask import Blueprint, request, jsonify

logger    = logging.getLogger(__name__)
ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.route("/ingest/status", methods=["GET"])
def ingest_status():
    """How many chunks are in the RAG index?"""
    try:
        from rag.vector_store import count
        from rag.watcher import DOCS_DIR
        files = [f for f in os.listdir(DOCS_DIR)
                 if os.path.isfile(os.path.join(DOCS_DIR, f))]
        return jsonify({"chunks_indexed": count(), "docs_folder": DOCS_DIR,
                        "files_in_folder": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ingest_bp.route("/ingest/scan", methods=["POST"])
def ingest_scan():
    """Manually trigger a scan of the docs folder."""
    try:
        from rag.watcher import ingest_now
        results = ingest_now()
        total   = sum(v for v in results.values() if isinstance(v, int))
        return jsonify({"status": "ok", "files": results, "total_chunks": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ingest_bp.route("/ingest/text", methods=["POST"])
def ingest_text():
    """Ingest raw text directly. POST {text, source}"""
    try:
        data   = request.get_json() or {}
        text   = data.get("text", "").strip()
        source = data.get("source", "manual")
        if not text:
            return jsonify({"error": "No text provided"}), 400
        from rag.ingest import ingest_text as _ingest
        n = _ingest(text, source=source)
        return jsonify({"status": "ok", "chunks": n, "source": source})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ingest_bp.route("/ingest/search", methods=["POST"])
def ingest_search():
    """Search the RAG index. POST {query, top_k}"""
    try:
        data    = request.get_json() or {}
        query   = data.get("query", "").strip()
        top_k   = int(data.get("top_k", 5))
        if not query:
            return jsonify({"error": "No query provided"}), 400
        from rag.embeddings import embed
        from rag.vector_store import search
        from rag.reranker import rerank
        results  = search(embed(query), top_k=top_k * 2)
        reranked = rerank(query, results, top_k=top_k)
        return jsonify({"results": reranked, "count": len(reranked)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
