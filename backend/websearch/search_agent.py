import os
import logging
import ollama
from typing import Dict
from websearch.search import (
    serper_search,
    duckduckgo_search,
    format_results_for_llm,
    extract_citations,
)

logger = logging.getLogger(__name__)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


class WebSearchAgent:
    def __init__(self, model: str = "phi3:mini"):
        self.model = model

    def _client(self):
        return ollama.Client(host=OLLAMA_HOST)

    def run(self, query: str, user_name: str = "User") -> Dict:
        logger.info(f"🔍 WebSearchAgent: {query}")

        results = serper_search(query, num_results=5)
        if not results:
            logger.info("Serper unavailable — trying DuckDuckGo")
            results = duckduckgo_search(query, num_results=5)

        if not results:
            return {
                "reply": "Search unavailable. Add SERPER_API_KEY to .env or install: pip install duckduckgo-search",
                "citations": [],
                "search_used": False,
                "results_count": 0,
            }

        context = format_results_for_llm(results)
        citations = extract_citations(results)

        prompt = f"""You are ASTRA, {user_name}'s AI assistant.
Using ONLY the search results below, answer concisely and accurately.
Be direct. Cite sources by [number] when using specific facts.

Question: {query}

{context}

Answer (2-4 sentences, cite sources):"""

        try:
            response = self._client().chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_predict": 300},
            )
            summary = response["message"]["content"].strip()
        except Exception as e:
            logger.error(f"LLM summarization error: {e}")
            summary = results[0].get("snippet", "Found results but couldn't summarize.")

        citation_text = ""
        if citations:
            citation_text = "\n\n📚 Sources:\n"
            for c in citations[:3]:
                citation_text += f"[{c['index']}] {c['title']} — {c['url']}\n"

        return {
            "reply": summary + citation_text,
            "citations": citations,
            "search_used": True,
            "results_count": len(results),
        }
