import logging
import re
from typing import Optional
from ddgs import DDGS

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, region="us-en"))
        if not results:
            return f"No results found for '{query}'."
        lines = [f"Search: **{query}**\n"]
        for i, r in enumerate(results[:3], 1):
            lines.append(f"{i}. **{r.get('title','')}**")
            lines.append(f"   {r.get('body','')[:220]}")
            lines.append(f"   {r.get('href','')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"


def search_news(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results, region="us-en"))
        if not results:
            return f"No news found for '{query}'."
        lines = [f"Latest news: **{query}**\n"]
        for i, r in enumerate(results[:3], 1):
            date = r.get("date","")[:10] if r.get("date") else ""
            lines.append(f"{i}. **{r.get('title','')}** ({date})")
            lines.append(f"   {r.get('body','')[:200]}")
            lines.append(f"   {r.get('url','')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"News search failed: {e}"


def search_quick(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3, region="us-en"))
        if not results:
            return search_web(query)
        top  = results[0]
        body = top.get("body", "")[:400]
        ans  = _best_sentence(query, body)
        return f"{ans}\nSource: {top.get('title','')}\n{top.get('href','')}"
    except Exception as e:
        return search_web(query)


def _best_sentence(query: str, text: str) -> str:
    if not text:
        return text
    sentences  = text.replace("\n", " ").split(". ")
    query_words = set(query.lower().split())
    best, best_score = text[:300], 0
    for s in sentences:
        score = sum(1 for w in query_words if w in s.lower())
        if score > best_score:
            best_score = score
            best = s
    return best.strip()


def handle_search_command(text: str) -> Optional[str]:
    t = text.lower().strip()

    # ── News ──────────────────────────────────────────────────
    if any(w in t for w in ["news about", "latest news", "recent news", "what's happening", "headlines"]):
        query = t
        for p in ["news about", "latest news on", "latest news about", "recent news on", "what's happening with", "headlines on"]:
            query = query.replace(p, "").strip()
        return search_news(query or t)

    # ── Factual with "and" — split into multiple searches ─────
    KEYWORDS = ["ceo", "founder", "president", "capital", "owner", "price", "cto", "age"]
    kw_match  = re.search(r"(ceo|founder|president|capital|owner|price|cto|age) of", t)

    if kw_match and " and " in t:
        kw      = kw_match.group(1)
        # extract everything after "X of "
        after   = t[t.index(kw_match.group(0)) + len(kw_match.group(0)):].strip()
        entities = [e.strip() for e in after.split(" and ") if e.strip()]
        results  = []
        for entity in entities:
            r = search_quick(f"{kw} of {entity}")
            if r:
                results.append(f"**{entity.title()}:** {r}")
        if results:
            return "\n\n".join(results)

    # ── Single factual question ────────────────────────────────
    factual_starts = ["who is ", "what is ", "when is ", "where is ", "how much ",
                      "what are ", "who are ", "which is ", "how many ", "when was ", "what was "]
    factual_contains = [" ceo of ", " founder of ", " president of ", " capital of ",
                        " population of ", " age of ", " cto of ", " owner of ", " price of "]

    if (any(t.startswith(w) for w in factual_starts)
            or any(w in t for w in factual_contains)
            or (kw_match and len(t.split()) <= 6)):
        return search_quick(t)

    # ── Explicit search ────────────────────────────────────────
    if any(w in t for w in ["search ", "search for ", "look up ", "google ", "find info", "find out"]):
        query = t
        for p in ["search for ", "search ", "look up ", "google ", "find info on ", "find info about ", "find out about "]:
            query = query.replace(p, "").strip()
        return search_web(query)

    return None


if __name__ == "__main__":
    print("=== ceo of apple and google ===")
    print(handle_search_command("ceo of apple and google"))
    print("\n=== who is the PM of india ===")
    print(handle_search_command("who is the PM of india"))
    print("\n=== latest news AI ===")
    print(handle_search_command("latest news AI"))
