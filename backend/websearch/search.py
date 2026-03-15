# websearch/search.py
import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_URL     = "https://google.serper.dev/search"


def duckduckgo_search(query: str, num_results: int = 5) -> list:
    """Free search fallback — no API key needed."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
    except ImportError:
        logger.error("duckduckgo-search not installed. Run: pip install duckduckgo-search")
        return []
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "source":  r.get("href", ""),
                    "type":    "organic"
                })
        logger.info(f"🦆 DuckDuckGo: {len(results)} results for: {query[:50]}")
        if not results:
            logger.warning("DuckDuckGo returned 0 results — may be rate-limited")
        return results
    except Exception as e:
        logger.error(f"DuckDuckGo error ({type(e).__name__}): {e}")
        return []


def serper_search(query: str, num_results: int = 5) -> list:
    """
    Search via Serper API (Google). Falls back to DuckDuckGo if:
    - No SERPER_API_KEY set
    - Serper times out or errors
    """
    if not SERPER_API_KEY:
        logger.info("No SERPER_API_KEY — using DuckDuckGo")
        return duckduckgo_search(query, num_results)

    try:
        response = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=10
        )
        response.raise_for_status()
        data    = response.json()
        results = []

        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            results.append({
                "title":   kg.get("title", ""),
                "snippet": kg.get("description", ""),
                "source":  kg.get("website", "Google Knowledge Graph"),
                "type":    "knowledge_graph"
            })

        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title":   item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source":  item.get("link", ""),
                "type":    "organic"
            })

        logger.info(f"🔍 Serper: {len(results)} results for: {query[:50]}")
        return results

    except requests.exceptions.Timeout:
        logger.warning("Serper timeout — falling back to DuckDuckGo")
        return duckduckgo_search(query, num_results)
    except requests.exceptions.RequestException as e:
        logger.warning(f"Serper error ({e}) — falling back to DuckDuckGo")
        return duckduckgo_search(query, num_results)


def format_results_for_llm(results: list, max_chars: int = 2000) -> str:
    """Format search results into clean context for LLM."""
    if not results:
        return "No search results found."
    formatted   = "SEARCH RESULTS:\n"
    total_chars = 0
    for i, r in enumerate(results, 1):
        entry = f"\n[{i}] {r.get('title','').strip()}\n{r.get('snippet','').strip()}\nSource: {r.get('source','').strip()}\n"
        if total_chars + len(entry) > max_chars:
            break
        formatted   += entry
        total_chars += len(entry)
    return formatted


def extract_citations(results: list) -> list:
    """Extract source URLs for citations."""
    return [
        {"index": i, "title": r.get("title", ""), "url": r.get("source", "")}
        for i, r in enumerate(results, 1)
        if r.get("source", "").startswith("http")
    ]
