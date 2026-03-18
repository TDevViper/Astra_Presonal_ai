# core/context_engine_v2.py — Context Engine v2
# Priority ranking + compression + relevance scoring
import logging
import time
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 800
MAX_FACTS          = 5
MAX_EXCHANGES      = 3


def _relevance_score(chunk: str, query: str) -> float:
    q_words = set(query.lower().split())
    c_words = set(chunk.lower().split())
    stop = {"i","a","the","is","are","was","what","how","why","do","did",
            "can","you","me","my","about","to","in","of","and","or","for",
            "with","it","this","that","be","have","has","will","would"}
    q_sig = q_words - stop
    c_sig = c_words - stop
    if not q_sig:
        return 0.3
    overlap = len(q_sig & c_sig)
    score   = min(1.0, overlap / len(q_sig))
    if len(c_words) > 80:
        score *= 0.85
    return round(score, 3)


def _compress_text(text: str, max_words: int = 40) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    last_dot  = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if last_dot > len(truncated) * 0.6:
        return truncated[:last_dot + 1]
    return truncated + "..."


def _count_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def select_best_chunks(query: str, chunks: List[Dict],
                       max_tokens: int = MAX_CONTEXT_TOKENS,
                       top_k: int = MAX_FACTS) -> List[Dict]:
    if not chunks:
        return []
    scored = []
    for chunk in chunks:
        text     = chunk.get("text", "")
        base     = chunk.get("score", 0.5)
        rel      = _relevance_score(text, query)
        combined = round(0.6 * base + 0.4 * rel, 3)
        scored.append({**chunk, "combined_score": combined})
    scored.sort(key=lambda x: x["combined_score"], reverse=True)
    selected    = []
    used_tokens = 0
    for chunk in scored[:top_k * 2]:
        tokens = _count_tokens(chunk["text"])
        if used_tokens + tokens > max_tokens:
            compressed = _compress_text(chunk["text"], max_words=25)
            tokens     = _count_tokens(compressed)
            if used_tokens + tokens <= max_tokens:
                selected.append({**chunk, "text": compressed})
                used_tokens += tokens
        else:
            selected.append(chunk)
            used_tokens += tokens
        if len(selected) >= top_k:
            break
    logger.info("context_v2: selected %d/%d chunks (%d tokens)",
                len(selected), len(chunks), used_tokens)
    return selected


def build_ranked_context(query: str, user_name: str,
                         query_intent: str = "general") -> Tuple[str, float]:
    t0 = time.time()
    try:
        from memory.vector_store import semantic_search
        facts, exchanges = semantic_search(query, top_k=8)
    except Exception as e:
        logger.warning("context_v2 vector search failed: %s", e)
        return "", 0.0

    confidence_boost = 0.0
    parts: List[str] = []

    if facts:
        ranked_facts = select_best_chunks(query, facts, top_k=MAX_FACTS)
        if ranked_facts:
            parts.append(f"What I know about {user_name}:")
            for f in ranked_facts:
                parts.append(f"  * {f['text']}")
                if f.get("combined_score", 0) >= 0.65:
                    confidence_boost = 0.85

    if exchanges:
        ranked_ex = select_best_chunks(query, exchanges, max_tokens=300, top_k=MAX_EXCHANGES)
        if ranked_ex:
            parts.append("\nRelevant past context:")
            for ex in ranked_ex:
                compressed = _compress_text(ex["text"], max_words=30)
                parts.append(f"  * {compressed}")

    try:
        from memory.episodic import build_episodic_context
        ep_ctx = build_episodic_context(query, user_name)
        if ep_ctx and len(ep_ctx.strip()) > 10:
            rel = _relevance_score(ep_ctx, query)
            if rel > 0.2 or query_intent in ("memory", "casual"):
                parts.append(f"\nRecent sessions:\n{_compress_text(ep_ctx, 50)}")
    except Exception as e:
        logger.debug("context_v2 episodic: %s", e)

    if not parts:
        return "", 0.0

    context    = "\n".join(parts)
    elapsed_ms = round((time.time() - t0) * 1000)
    logger.info("context_v2: built in %dms | boost=%.2f | chars=%d",
                elapsed_ms, confidence_boost, len(context))
    return context, confidence_boost


def context_quality_report(query: str, context: str) -> Dict:
    return {
        "query_words":    len(query.split()),
        "context_chars":  len(context),
        "context_tokens": _count_tokens(context),
        "relevance":      _relevance_score(context[:200], query),
        "has_facts":      "What I know" in context,
        "has_exchanges":  "past context" in context,
        "has_episodic":   "sessions" in context,
    }
