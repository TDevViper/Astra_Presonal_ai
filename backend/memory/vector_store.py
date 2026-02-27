# ==========================================
# memory/vector_store.py - v4
# ChromaDB + sentence-transformers (no hnswlib)
# ==========================================

import logging
import os
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────
_BACKEND_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR            = os.path.join(_BACKEND_DIR, "data", "vector_db")
COLLECTION_NAME   = "astra_memory"
TOP_K             = 5
FACT_THRESHOLD    = 0.70
EXCHANGE_THRESHOLD = 0.75

# ── State ─────────────────────────────────────────────────────
_client     = None
_collection = None
_embedder   = None


# ── Init ──────────────────────────────────────────────────────
def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("🧠 Loading embedding model (all-MiniLM-L6-v2)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ Embedder ready")
    return _embedder


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb
    os.makedirs(DB_DIR, exist_ok=True)
    _client = chromadb.PersistentClient(path=DB_DIR)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    logger.info(f"✅ ChromaDB ready — {_collection.count()} vectors")
    return _collection


# ── Embedding ─────────────────────────────────────────────────
def embed(text: str) -> List[float]:
    try:
        embedder = _get_embedder()
        return embedder.encode(text).tolist()
    except Exception as e:
        logger.error(f"❌ Embedding error: {e}")
        return []


# ── Store ─────────────────────────────────────────────────────
def store_vector(text: str, source: str = "fact", metadata: Optional[Dict] = None) -> bool:
    if not text or not text.strip():
        return False

    try:
        collection = _get_collection()
        vector = embed(text)
        if not vector:
            return False

        import hashlib
        doc_id = hashlib.md5(text.encode()).hexdigest()

        # Check if already exists
        existing = collection.get(ids=[doc_id])
        if existing["ids"]:
            return True

        collection.add(
            ids=[doc_id],
            embeddings=[vector],
            documents=[text],
            metadatas=[{"source": source, **(metadata or {})}]
        )
        logger.debug(f"📥 [{source}] stored: {text[:60]}...")
        return True

    except Exception as e:
        logger.error(f"❌ Store error: {e}")
        return False


def store_fact(fact: str, fact_type: str = "fact", user_name: str = "user") -> bool:
    return store_vector(
        text=fact, source="fact",
        metadata={"type": fact_type, "user": user_name}
    )


def store_exchange(user_msg: str, assistant_msg: str, user_name: str = "user") -> bool:
    combined = f"User: {user_msg}\nASTRA: {assistant_msg}"
    return store_vector(
        text=combined, source="exchange",
        metadata={"user": user_name}
    )


# ── Query ─────────────────────────────────────────────────────
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
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        facts: List[Dict] = []
        exchanges: List[Dict] = []

        if not results: return [], []
        docs      = (results["documents"] or [[]])[0]
        metas     = (results["metadatas"] or [[]])[0]
        distances = (results["distances"] or [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            # ChromaDB cosine distance → similarity
            similarity = 1.0 - float(dist)
            source = meta.get("source", "fact")

            hit = {"text": doc, "score": round(similarity, 3), "source": source, "metadata": meta}

            if source == "fact" and similarity >= FACT_THRESHOLD:
                facts.append(hit)
            elif source == "exchange" and similarity >= EXCHANGE_THRESHOLD:
                exchanges.append(hit)

        facts.sort(key=lambda x: x["score"], reverse=True)
        exchanges.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"🔍 semantic_search | facts={len(facts)} exchanges={len(exchanges)} query='{query[:40]}'")
        return facts, exchanges

    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        return [], []


# ── Utils ─────────────────────────────────────────────────────
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
        logger.error(f"❌ Clear error: {e}")
        return False