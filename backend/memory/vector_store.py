# ==========================================
# memory/vector_store.py - v5.0 ADVANCED
# Decay scoring, contradiction detection,
# priority tagging, compression
# ==========================================

import logging
import os
import time as _time
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_BACKEND_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR             = os.path.join(_BACKEND_DIR, "data", "vector_db")
COLLECTION_NAME    = "astra_memory"
TOP_K              = 5
FACT_THRESHOLD     = 0.50   # slightly lower — catch more
EXCHANGE_THRESHOLD = 0.58
DECAY_HALF_LIFE    = 7 * 24 * 3600   # 7 days in seconds

_client     = None
_collection = None
_embedder   = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("�� Loading embedder...")
        _embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        logger.info("✅ Embedder ready")
    return _embedder


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    import chromadb
    os.makedirs(DB_DIR, exist_ok=True)
    _client     = chromadb.PersistentClient(path=DB_DIR)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    logger.info(f"✅ ChromaDB — {_collection.count()} vectors")
    return _collection


def embed(text: str) -> List[float]:
    try:
        return _get_embedder().encode(text).tolist()
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []


# ── Decay score — recent memories rank higher ─────────────────────────────
def _decay_score(similarity: float, stored_ts: float) -> float:
    age_seconds = _time.time() - stored_ts
    decay       = 0.5 ** (age_seconds / DECAY_HALF_LIFE)
    return similarity * (0.7 + 0.3 * decay)   # 70% semantic, 30% recency


# ── Contradiction detection — before storing ──────────────────────────────
def _is_contradictory(new_text: str, threshold: float = 0.85) -> Optional[str]:
    """
    Returns the existing contradicting text if found, None otherwise.
    Simple heuristic: very high similarity but opposite polarity words.
    """
    try:
        facts, _ = semantic_search(new_text, top_k=3)
        neg_words = {"not", "no", "never", "don't", "isn't", "wasn't", "hate", "dislike"}
        new_words = set(new_text.lower().split())
        for hit in facts:
            if hit["score"] > threshold:
                existing_words = set(hit["text"].lower().split())
                # Contradiction: one has negation the other doesn't
                new_neg      = bool(new_words & neg_words)
                existing_neg = bool(existing_words & neg_words)
                if new_neg != existing_neg:
                    return hit["text"]
    except Exception as _e:
        logger.debug('vector_store contradiction check: %s', _e)
    return None


def store_vector(text: str, source: str = "fact",
                 metadata: Optional[Dict] = None, priority: int = 1) -> bool:
    if not text or not text.strip():
        return False
    try:
        collection = _get_collection()
        vector     = embed(text)
        if not vector:
            return False

        import hashlib
        doc_id = hashlib.md5(text.encode()).hexdigest()

        existing = collection.get(ids=[doc_id])
        if existing["ids"]:
            return True   # already stored

        ts    = _time.time()
        meta  = {
            "source":   source,
            "ts":       ts,
            "priority": priority,
            **(metadata or {})
        }
        collection.add(ids=[doc_id], embeddings=[vector], documents=[text], metadatas=[meta])
        logger.debug(f"📥 [{source}] stored: {text[:60]}")
        return True
    except Exception as e:
        logger.error(f"Store error: {e}")
        return False


def store_fact(fact: str, fact_type: str = "fact", user_name: str = "user",
               priority: int = 1) -> bool:
    # Check for contradiction before storing
    contradiction = _is_contradictory(fact)
    if contradiction:
        logger.info(f"🔄 Contradiction detected — updating: {contradiction[:50]}")
        # Remove old contradicting fact, store new one
        _remove_by_text(contradiction)

    return store_vector(text=fact, source="fact", priority=priority,
                        metadata={"type": fact_type, "user": user_name})


def store_exchange(user_msg: str, assistant_msg: str, user_name: str = "user") -> bool:
    combined = f"User: {user_msg}\nASTRA: {assistant_msg}"
    return store_vector(text=combined, source="exchange",
                        metadata={"user": user_name})


def _remove_by_text(text: str) -> bool:
    try:
        import hashlib
        doc_id = hashlib.md5(text.encode()).hexdigest()
        _get_collection().delete(ids=[doc_id])
        return True
    except Exception:
        return False


def semantic_search(query: str, top_k: int = TOP_K) -> Tuple[List[Dict], List[Dict]]:
    if not query or not query.strip():
        return [], []
    try:
        collection = _get_collection()
        if collection.count() == 0:
            return [], []
        vector = embed(query)
        if not vector:
            return [], []

        results = collection.query(
            query_embeddings=[vector],
            n_results=min(top_k * 2, collection.count()),   # fetch more, rerank with decay
            include=["documents", "metadatas", "distances"]
        )

        facts: List[Dict]     = []
        exchanges: List[Dict] = []

        if not results:
            return [], []

        docs      = (results["documents"] or [[]])[0]
        metas     = (results["metadatas"] or [[]])[0]
        distances = (results["distances"] or [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            similarity = 1.0 - float(dist)
            source     = meta.get("source", "fact")
            stored_ts  = float(meta.get("ts", _time.time()))
            priority   = int(meta.get("priority", 1))

            # Apply decay and priority weighting
            adjusted   = _decay_score(similarity, stored_ts) * (1.0 + 0.1 * (priority - 1))
            hit = {"text": doc, "score": round(adjusted, 3),
                   "raw_score": round(similarity, 3),
                   "source": source, "metadata": meta}

            if source == "fact" and adjusted >= FACT_THRESHOLD:
                facts.append(hit)
            elif source == "exchange" and adjusted >= EXCHANGE_THRESHOLD:
                exchanges.append(hit)

        facts.sort(key=lambda x: x["score"], reverse=True)
        exchanges.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"🔍 search | facts={len(facts)} exchanges={len(exchanges)} query='{query[:40]}'")
        return facts[:top_k], exchanges[:3]

    except Exception as e:
        logger.error(f"Search error: {e}")
        return [], []


def get_collection_size() -> int:
    try:
        return _get_collection().count()
    except Exception:
        return 0


def clear_collection() -> bool:
    global _client, _collection
    try:
        if _client and _collection:
            _client.delete_collection(COLLECTION_NAME)
            _collection = None
        logger.warning("🗑️ Vector store cleared")
        return True
    except Exception as e:
        logger.error(f"Clear error: {e}")
        return False


# ── Memory compression — prune low-score old exchanges ────────────────────
def compress_memory(max_exchanges: int = 200) -> int:
    """Remove oldest low-priority exchanges when collection gets large."""
    try:
        collection = _get_collection()
        count = collection.count()
        if count < max_exchanges:
            return 0

        results = collection.get(include=["metadatas"], where={"source": "exchange"})
        if not results or not results["ids"]:
            return 0

        # Sort by timestamp, remove oldest 20%
        pairs = list(zip(results["ids"], results["metadatas"]))
        pairs.sort(key=lambda x: float(x[1].get("ts", 0)))
        to_remove = pairs[:max(1, len(pairs) // 5)]
        ids_to_remove = [p[0] for p in to_remove]
        collection.delete(ids=ids_to_remove)
        logger.info(f"🗜️ Compressed {len(ids_to_remove)} old exchanges")
        return len(ids_to_remove)
    except Exception as e:
        logger.error(f"Compress error: {e}")
        return 0
