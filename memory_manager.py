# ==========================================
# core/memory_manager.py
# ==========================================
import logging, threading
from typing import Dict, List, Optional, Tuple

from memory.memory_engine import load_memory, save_memory
from memory.memory_extractor import extract_user_fact
from memory.memory_recall import memory_recall
from memory.summarizer import should_summarize, summarize_conversation, store_summary
from memory.semantic_recall import index_user_fact, index_exchange
from memory.episodic import store_episode
from emotion.emotion_memory import update_emotion, ensure_emotion_memory
from intents.classifier import is_question_like

logger = logging.getLogger(__name__)

class MemoryManager:
    def load(self) -> Dict:
        return ensure_emotion_memory(load_memory())

    def save(self, memory: Dict) -> None:
        try:
            save_memory(memory)
        except Exception as e:
            logger.error("save_memory failed: %s", e)

    def user_name(self, memory: Dict) -> str:
        return memory.get("preferences", {}).get("name", "User")

    def user_location(self, memory: Dict) -> str:
        return memory.get("preferences", {}).get("location", "")

    def update_emotion(self, memory: Dict, label: str, score: float) -> Dict:
        try:
            return update_emotion(memory, label, score)
        except Exception as e:
            logger.warning("update_emotion failed: %s", e)
            return memory

    def extract_and_store_fact(self, user_input, memory, user_name) -> Tuple[Optional[Dict], Dict]:
        try:
            fact = extract_user_fact(user_input)
            if fact:
                memory = self._store_fact(fact, memory)
                try:
                    index_user_fact(fact, user_name=user_name)
                except Exception as e:
                    logger.warning("index_user_fact failed: %s", e)
                return fact, memory
        except Exception as e:
            logger.warning("extract_user_fact failed: %s", e)
        return None, memory

    def _store_fact(self, fact, memory):
        memory["user_facts"].append(fact)
        ftype, subtype, value = fact["type"], fact.get("subtype", ""), fact.get("value")
        if ftype == "identity":     memory["preferences"]["name"]       = value
        elif ftype == "location":   memory["preferences"]["location"]   = value
        elif ftype == "preference": memory["preferences"][subtype]      = value
        return memory

    def acknowledge_fact(self, fact: Dict) -> str:
        return f"Got it. {fact['fact']}."

    def recall(self, user_input, memory, user_name) -> Optional[str]:
        try:
            return memory_recall(user_input, memory, user_name)
        except Exception as e:
            logger.warning("memory_recall failed: %s", e)
            return None

    def post_turn(self, user_input, reply, memory, user_name, query_intent, emotion_label, conversation_history, selected_model="phi3:mini") -> Dict:
        try:
            index_exchange(user_input, reply, user_name=user_name)
        except Exception as e:
            logger.warning("index_exchange failed: %s", e)
        try:
            store_episode(user_input, reply, intent=query_intent, emotion=emotion_label, user_name=user_name)
        except Exception as e:
            logger.warning("store_episode failed: %s", e)
        try:
            if should_summarize(conversation_history):
                summary = summarize_conversation(conversation_history, memory, user_name, model=selected_model)
                memory  = store_summary(memory, summary)
        except Exception as e:
            logger.warning("summarize failed: %s", e)
        self.save(memory)
        threading.Thread(target=self._kg, args=(user_input, reply, user_name), daemon=True).start()
        threading.Thread(target=self._si, args=(user_input, reply),            daemon=True).start()
        return memory

    def _kg(self, user_input, reply, user_name):
        try:
            from knowledge.auto_extractor import extract_from_exchange
            extract_from_exchange(user_input, reply, user_name=user_name)
        except Exception as e:
            logger.warning("auto_extractor failed: %s", e)

    def _si(self, user_input, reply):
        try:
            from core.self_improve import log_response
            log_response(user_input, reply, 0.75)
        except Exception as e:
            logger.warning("self_improve failed: %s", e)
