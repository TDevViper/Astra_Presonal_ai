# core/memory_manager.py
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class MemoryManager:

    def load(self) -> Dict:
        try:
            from memory.memory_engine import load_memory
            return load_memory()
        except Exception as e:
            logger.warning("MemoryManager.load failed: %s", e)
            return {"preferences": {"name": "User"}, "user_facts": [], "emotion_history": []}

    def save(self, memory: Dict) -> None:
        try:
            from memory.memory_engine import save_memory
            save_memory(memory)
        except Exception as e:
            logger.warning("MemoryManager.save failed: %s", e)

    def user_name(self, memory: Dict) -> str:
        try:
            return memory.get("preferences", {}).get("name", "User")
        except Exception:
            return "User"

    def user_location(self, memory: Dict) -> str:
        try:
            return memory.get("preferences", {}).get("location", "")
        except Exception:
            return ""

    def update_emotion(self, memory: Dict, label: str, score: float) -> Dict:
        try:
            from emotion.emotion_memory import update_emotion, ensure_emotion_memory
            ensure_emotion_memory(memory)
            return update_emotion(memory, label, score)
        except Exception as e:
            logger.debug("update_emotion failed: %s", e)
        return memory

    def extract_and_store_fact(self, user_input: str, memory: Dict,
                                user_name: str) -> Tuple[Optional[Dict], Dict]:
        try:
            from memory.memory_extractor import extract_user_fact
            fact = extract_user_fact(user_input)
            if fact:
                memory.setdefault("user_facts", []).append(fact)
                try:
                    from memory.semantic_recall import index_user_fact
                    index_user_fact(fact, user_name)
                except Exception as e:
                    logger.debug("index_user_fact failed: %s", e)
            return fact, memory
        except Exception as e:
            logger.warning("extract_and_store_fact failed: %s", e)
        return None, memory

    def acknowledge_fact(self, fact: Dict) -> str:
        try:
            val = fact.get("value") or fact.get("fact", "that")
            return f"Got it — I'll remember {val}."
        except Exception:
            return "Got it, I'll remember that."

    def recall(self, user_input: str, memory: Dict, user_name: str) -> Optional[str]:
        try:
            from memory.memory_recall import memory_recall
            return memory_recall(user_input, memory, user_name)
        except Exception as e:
            logger.debug("MemoryManager.recall failed: %s", e)
        return None

    def post_turn(self, user_input: str, reply: str, memory: Dict,
                  user_name: str, query_intent: str, emotion_label: str,
                  history: List[Dict], selected_model: str) -> None:
        try:
            from memory.episodic import store_episode
            store_episode(user_input, reply, intent=query_intent, user_name=user_name)
        except Exception as e:
            logger.debug("store_episode failed: %s", e)
        try:
            from memory.semantic_recall import index_exchange
            index_exchange(user_input, reply, user_name)
        except Exception as e:
            logger.debug("index_exchange failed: %s", e)
        try:
            from memory.summarizer import should_summarize, summarize_conversation, store_summary
            if should_summarize(history):
                summary = summarize_conversation(history, user_name, model=selected_model)
                store_summary(summary, memory)
                self.save(memory)
        except Exception as e:
            logger.debug("summarizer failed: %s", e)
        try:
            from knowledge.graph import update_graph
            update_graph(user_input, reply, user_name)
        except Exception as e:
            logger.debug("update_graph failed: %s", e)
