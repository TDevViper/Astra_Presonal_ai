# astra_engine/websearch/search.py

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"


def serper_search(query: str, num_results: int = 5) -> Optional[list]:
    """Search Google via Serper API."""
    if not SERPER_API_KEY:
        logger.error("❌ SERPER_API_KEY not set in .env")
        return None

    try:
        response = requests.post(
            SERPER_URL,
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": num_results},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        results = []

        # Knowledge graph (instant answer)
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            results.append({
                "title": kg.get("title", ""),
                "snippet": kg.get("description", ""),
                "source": kg.get("website", "Google Knowledge Graph"),
                "type": "knowledge_graph"
            })

        # Organic results
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("link", ""),
                "type": "organic"
            })

        logger.info(f"🔍 Serper returned {len(results)} results for: {query}")
        return results

    except requests.exceptions.Timeout:
        logger.error("❌ Serper API timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Serper API error: {e}")
        return None


def format_results_for_llm(results: list, max_chars: int = 2000) -> str:
    """Format search results into clean context for LLM."""
    if not results:
        return "No search results found."

    formatted = "SEARCH RESULTS:\n"
    total_chars = 0

    for i, r in enumerate(results, 1):
        snippet = r.get("snippet", "").strip()
        title   = r.get("title", "").strip()
        source  = r.get("source", "").strip()

        entry = f"\n[{i}] {title}\n{snippet}\nSource: {source}\n"

        if total_chars + len(entry) > max_chars:
            break

        formatted += entry
        total_chars += len(entry)

    return formatted


def extract_citations(results: list) -> list:
    """Extract source URLs for citations."""
    citations = []
    for i, r in enumerate(results, 1):
        source = r.get("source", "")
        title  = r.get("title", "")
        if source and source.startswith("http"):
            citations.append({
                "index": i,
                "title": title,
                "url": source
            })
    return citations