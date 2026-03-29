"""
Vector memory store — LanceDB backend.
"""
import os
import logging
import time
import uuid
import threading
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

DB_DIR          = os.path.join(os.path.dirname(__file__), "..", "data", "lancedb")
TABLE_NAME      = "astra_memory"
TOP_K           = 5
EMBED_MODEL     = "BAAI/bge-small-en-v1.5"
SCORE_THRESHOLD = 0.30
RECENCY_WEIGHT  = 0.30
SEMANTIC_WEIGHT = 0.70

_embedder      = None
_embedder_lock = threading.Lock()

def _get_embedder():
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _embedder = SentenceTransformer(EMBED_MODEL)
                    logger.info("Embedder loaded: %s", EMBED_MODEL)
                except Exception as e:
                    logger.error("Embedder load failed: %s", e)
    return _embedder

def _embed(text: str):
    emb = _get_embedder()
    if emb is None:
        return None
    try:
        return emb.encode(text, normalize_embeddings=True).tolist()
    except Exception as e:
        logger.error("Embed error: %s", e)
        return None

_table      = None
_table_lock = threading.Lock()

def _get_table():
    global _table
    if _table is not None:
        return _table
    with _table_lock:
        if _table is not None:
            return _table
        try:
            import lancedb
            import pyarrow as pa
            os.makedirs(DB_DIR, exist_ok=True)
            db = lancedb.connect(DB_DIR)
            schema = pa.schema([
                pa.field("id",        pa.string()),
                pa.field("text",      pa.string()),
                pa.field("vector",    pa.list_(pa.float32(), 384)),
                pa.field("source",    pa.string()),
                pa.field("user",      pa.string()),
                pa.field("user_id",   pa.string()),
                pa.field("fact_type", pa.string()),
                pa.field("priority",  pa.float32()),
                pa.field("ts",        pa.float64()),
            ])
            if TABLE_NAME in db.table_names():
                _table = db.open_table(TABLE_NAME)
            else:
                _table = db.create_table(TABLE_NAME, schema=schema)
                logger.info("LanceDB table created: %s", TABLE_NAME)
            logger.info("LanceDB connected at %s", DB_DIR)
            return _table
        except Exception as e:
            logger.error("LanceDB init failed: %s", e)
            return None

def store_fact(fact: str, fact_type: str = "fact",
               user_name: str = "user", user_id: str = "default",
               priority: float = 0.8) -> bool:
    vector = _embed(fact)
    if vector is None:
        return False
    tbl = _get_table()
    if tbl is None:
        return False
    try:
        existing, _ = semantic_search(fact, top_k=1, user_id=user_id)
        if existing and existing[0]["score"] > 0.92:
            return False
        import pyarrow as pa
        tbl.add(pa.table({
            "id": [str(uuid.uuid4())], "text": [fact], "vector": [vector],
            "source": ["fact"], "user": [user_name], "user_id": [user_id],
            "fact_type": [fact_type], "priority": [float(priority)],
            "ts": [time.time()],
        }))
        logger.info("stored fact | user=%s text=%s", user_name, fact[:60])
        return True
    except Exception as e:
        logger.error("store_fact error: %s", e)
        return False

def store_exchange(user_msg: str, assistant_msg: str,
                   user_name: str = "user", user_id: str = "default") -> bool:
    if len(user_msg.strip()) < 10 or len(assistant_msg.strip()) < 10:
        return False
    combined = f"User: {user_msg}\nASTRA: {assistant_msg}"
    vector = _embed(combined)
    if vector is None:
        return False
    tbl = _get_table()
    if tbl is None:
        return False
    try:
        import pyarrow as pa
        tbl.add(pa.table({
            "id": [str(uuid.uuid4())], "text": [combined], "vector": [vector],
            "source": ["exchange"], "user": [user_name], "user_id": [user_id],
            "fact_type": ["exchange"], "priority": [0.5], "ts": [time.time()],
        }))
        return True
    except Exception as e:
        logger.error("store_exchange error: %s", e)
        return False

def semantic_search(query: str, top_k: int = TOP_K,
                    user_id: str = None) -> Tuple[List[Dict], List[Dict]]:
    vector = _embed(query)
    if vector is None:
        return [], []
    tbl = _get_table()
    if tbl is None:
        return [], []
    try:
        now    = time.time()
        oldest = now - 60 * 60 * 24 * 90
        results = tbl.search(vector).limit(top_k * 3).to_list()
        facts, exchanges = [], []
        for r in results:
            if user_id and r.get("user_id", "default") != user_id:
                continue
            raw_score = 1.0 - float(r.get("_distance", 1.0))
            age_score = max(0, (r["ts"] - oldest) / (now - oldest + 1))
            score     = SEMANTIC_WEIGHT * raw_score + RECENCY_WEIGHT * age_score
            if score < SCORE_THRESHOLD:
                continue
            hit = {"text": r["text"], "score": round(score, 3),
                   "fact_type": r.get("fact_type", ""), "ts": r["ts"]}
            if r["source"] == "fact":
                facts.append(hit)
            else:
                exchanges.append(hit)
        facts.sort(key=lambda x: x["score"], reverse=True)
        exchanges.sort(key=lambda x: x["score"], reverse=True)
        return facts[:top_k], exchanges[:top_k]
    except Exception as e:
        logger.error("semantic_search error: %s", e)
        return [], []

def get_memory_count() -> int:
    tbl = _get_table()
    if tbl is None:
        return 0
    try:
        return tbl.count_rows()
    except Exception:
        return 0

def compress_memory(max_exchanges: int = 200, user_id: str = None) -> int:
    tbl = _get_table()
    if tbl is None:
        return 0
    try:
        df = tbl.to_pandas()
        exchanges = df[df["source"] == "exchange"]
        if user_id:
            exchanges = exchanges[exchanges["user_id"] == user_id]
        if len(exchanges) <= max_exchanges:
            return 0
        cutoff = int(len(exchanges) * 0.20)
        oldest = exchanges.nsmallest(cutoff, "ts")
        ids    = oldest["id"].tolist()
        ids_sql = ", ".join(f'"{i}"' for i in ids)
        tbl.delete(f"id IN ({ids_sql})")
        logger.info("compressed %d exchanges", len(ids))
        return len(ids)
    except Exception as e:
        logger.error("compress_memory error: %s", e)
        return 0
