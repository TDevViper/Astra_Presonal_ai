# ==========================================
# astra_engine/websearch/search.py
# ==========================================

import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"


def serper_search(query: str, num_results: int = 5) -> Optional[list]:
    """
    Search Google via Serper API.
    Returns list of result dicts or None on failure.
    """
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
    """
    Format search results into clean context for LLM.
    """
    if not results:
        return "No search results found."

    formatted = "SEARCH RESULTS:\n"
    total_chars = 0

    for i, r in enumerate(results, 1):
        snippet = r.get("snippet", "").strip()
        title = r.get("title", "").strip()
        source = r.get("source", "").strip()

        entry = f"\n[{i}] {title}\n{snippet}\nSource: {source}\n"

        if total_chars + len(entry) > max_chars:
            break

        formatted += entry
        total_chars += len(entry)

    return formatted


def extract_citations(results: list) -> list:
    """
    Extract source URLs for citations.
    """
    citations = []
    for i, r in enumerate(results, 1):
        source = r.get("source", "")
        title = r.get("title", "")
        if source and source.startswith("http"):
            citations.append({
                "index": i,
                "title": title,
                "url": source
            })
    return citations


# ==========================================
# astra_engine/websearch/search_agent.py
# ==========================================

import logging
import ollama
from typing import Dict, Optional

from websearch.search import (
    serper_search,
    format_results_for_llm,
    extract_citations
)

logger = logging.getLogger(__name__)


class WebSearchAgent:
    """
    Full search → summarize → cite pipeline.
    
    Flow:
        user query
            → search Google via Serper
            → format results
            → LLM summarizes with citations
            → structured reply
    """

    def __init__(self, model: str = "phi3:mini"):
        self.model = model

    def run(self, query: str, user_name: str = "Arnav") -> Dict:
        """
        Execute full search pipeline.
        
        Returns:
            {
                "reply": str,
                "citations": list,
                "search_used": bool,
                "results_count": int
            }
        """
        logger.info(f"🔍 WebSearchAgent running for: {query}")

        # 1. SEARCH
        results = serper_search(query, num_results=5)

        if not results:
            return {
                "reply": "I tried to search but couldn't get results. Check your SERPER_API_KEY.",
                "citations": [],
                "search_used": False,
                "results_count": 0
            }

        # 2. FORMAT FOR LLM
        context = format_results_for_llm(results)
        citations = extract_citations(results)

        # 3. SUMMARIZE WITH LLM
        prompt = f"""You are ASTRA, {user_name}'s AI assistant.
        
Using ONLY the search results below, answer the question concisely and accurately.
Be direct. Cite sources by [number] when using specific facts.
Do not make up information not in the results.

Question: {query}

{context}

Answer (2-4 sentences, cite sources):"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_predict": 300}
            )
            summary = response["message"]["content"].strip()
            logger.info(f"✅ Search summarized: {summary[:80]}...")

        except Exception as e:
            logger.error(f"❌ LLM summarization error: {e}")
            # Fallback: return top snippet directly
            summary = results[0].get("snippet", "I found some results but couldn't summarize them.")

        # 4. FORMAT CITATIONS
        citation_text = ""
        if citations:
            citation_text = "\n\n📚 Sources:\n"
            for c in citations[:3]:
                citation_text += f"[{c['index']}] {c['title']} — {c['url']}\n"

        full_reply = summary + citation_text

        return {
            "reply": full_reply,
            "citations": citations,
            "search_used": True,
            "results_count": len(results)
        }