"""
rag/vector_store.py — Compatibility shim for the RAG subsystem.

The project migrated from FAISS to LanceDB (memory/vector_store.py).
This file re-exposes the old interface (add_chunks, search, _load_meta, count)
so that rag/ingest.py, rag/retriever.py, and rag/rag_engine.py continue to work
without modification.
"""

import logging
from typing import List, Dict
import numpy as np

logger = logging.getLogger(__name__)
_RAG_SOURCE = "rag_chunk"


def add_chunks(chunks: List[str], embeddings: np.ndarray, source: str = "manual", tags: List[str] = None) -> None:
    try:
        import pyarrow as pa, time, uuid
        from memory.vector_store import _get_table
        tbl = _get_table()
        if tbl is None:
            logger.error("add_chunks: LanceDB table unavailable")
            return
        rows = {"id": [], "text": [], "vector": [], "source": [], "user": [], "user_id": [], "fact_type": [], "priority": [], "ts": []}
        now = time.time()
        for i, chunk in enumerate(chunks):
            vec = embeddings[i].tolist() if hasattr(embeddings[i], "tolist") else list(embeddings[i])
            rows["id"].append(str(uuid.uuid4()))
            rows["text"].append(chunk)
            rows["vector"].append(vec)
            rows["source"].append(_RAG_SOURCE)
            rows["user"].append(source)
            rows["user_id"].append("rag")
            rows["fact_type"].append(",".join(tags) if tags else "rag")
            rows["priority"].append(0.7)
            rows["ts"].append(now)
        tbl.add(pa.table(rows))
        logger.info("add_chunks: stored %d chunks from source=%s", len(chunks), source)
    except Exception as e:
        logger.error("add_chunks error: %s", e)


def search(query_vec: np.ndarray, top_k: int = 5) -> List[Dict]:
    try:
        from memory.vector_store import _get_table
        tbl = _get_table()
        if tbl is None:
            return []
        vec = query_vec.tolist() if hasattr(query_vec, "tolist") else list(query_vec)
        if isinstance(vec[0], list):
            vec = vec[0]
        results = tbl.search(vec).where(f"source = '{_RAG_SOURCE}'", prefilter=True).limit(top_k).to_list()
        return [{"text": r["text"], "score": round(1.0 - float(r.get("_distance", 1.0)), 3), "source": r.get("user", "unknown")} for r in results]
    except Exception as e:
        logger.error("search error: %s", e)
        return []


def _load_meta() -> List[Dict]:
    try:
        from memory.vector_store import _get_table
        tbl = _get_table()
        if tbl is None:
            return []
        df = tbl.to_pandas()
        rag_rows = df[df["source"] == _RAG_SOURCE]
        return [{"text": row["text"], "source": row["user"]} for _, row in rag_rows.iterrows()]
    except Exception as e:
        logger.error("_load_meta error: %s", e)
        return []


def count() -> int:
    try:
        from memory.vector_store import _get_table
        tbl = _get_table()
        if tbl is None:
            return 0
        df = tbl.to_pandas()
        return int((df["source"] == _RAG_SOURCE).sum())
    except Exception as e:
        logger.error("count error: %s", e)
        return 0
