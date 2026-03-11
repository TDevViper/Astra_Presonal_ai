# ==========================================
# tests/test_brain_pipeline.py
# ==========================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock


def _fake_ollama_response(text="This is a test reply."):
    mock = MagicMock()
    mock.__getitem__ = lambda s, k: {"message": {"content": text}}[k]
    return mock


def _fake_memory():
    return {
        "preferences": {"name": "Arnav", "location": "India"},
        "user_facts": [],
        "emotion_history": [],
    }


def _brain_with_mocks():
    with patch("core.brain.MemoryManager"), \
         patch("core.brain.ResponseCache"), \
         patch("core.brain.TruthGuard"), \
         patch("core.brain.CapabilityManager"), \
         patch("core.brain.ModelManager"), \
         patch("core.brain.WebSearchAgent"), \
         patch("core.brain.EarlyExitHandler"), \
         patch("core.brain.ContextBuilder"), \
         patch("core.brain.PostProcessor"):

        from core.brain import Brain
        brain = Brain.__new__(Brain)

        mem = MagicMock()
        mem.load.return_value          = _fake_memory()
        mem.user_name.return_value     = "Arnav"
        mem.user_location.return_value = "India"
        mem.update_emotion.side_effect = lambda m, *a: m
        mem.extract_and_store_fact.return_value = (None, _fake_memory())
        mem.recall.return_value        = None
        brain._mem = mem

        cache = MagicMock()
        cache.get.return_value = None
        brain._cache = cache

        tg = MagicMock()
        tg.validate.return_value = (True, None)
        brain.truth_guard = tg

        cap = MagicMock()
        cap.is_enabled.return_value = False
        brain.capabilities = cap

        mm = MagicMock()
        mm.classify_query_intent.return_value = "general"
        mm.select_model.return_value          = "phi3:mini"
        mm.get_model_info.return_value        = {"model": "phi3:mini"}
        brain.model_manager = mm

        brain.search_agent = MagicMock()

        exit_h = MagicMock()
        exit_h.check_mode_switch.return_value     = None
        exit_h.check_chain.return_value           = None
        exit_h.check_briefing.return_value        = None
        exit_h.check_quick_tools.return_value     = None
        exit_h.check_intent_shortcut.return_value = None
        exit_h.check_self_query.return_value      = None
        brain._exit = exit_h

        ctx = MagicMock()
        ctx.build.return_value = ("You are ASTRA.", 0.5)
        brain._ctx = ctx

        post = MagicMock()
        post.process.side_effect = lambda reply, *a, **kw: reply
        brain._post = post

        brain.conversation_history = []
        return brain


# ── Happy path ─────────────────────────────────────────────────────────────

class TestHappyPath(unittest.TestCase):

    @patch("ollama.chat")
    def test_simple_query_returns_reply(self, mock_chat):
        mock_chat.return_value = _fake_ollama_response("Python is a programming language.")
        brain = _brain_with_mocks()
        result = brain.process("What is Python?")
        self.assertIn("reply", result)
        self.assertIn("Python", result["reply"])

    @patch("ollama.chat")
    def test_reply_has_all_required_keys(self, mock_chat):
        mock_chat.return_value = _fake_ollama_response("Some answer.")
        brain = _brain_with_mocks()
        result = brain.process("hello")
        for key in ["reply", "emotion", "intent", "agent", "confidence", "tool_used", "memory_updated"]:
            self.assertIn(key, result, f"Missing key: {key}")


# ── Early exits ────────────────────────────────────────────────────────────

class TestEarlyExits(unittest.TestCase):

    def test_mode_switch_skips_llm(self):
        brain = _brain_with_mocks()
        brain._exit.check_mode_switch.return_value = "Mode switched: FOCUS"
        result = brain.process("focus mode")
        self.assertEqual(result["intent"], "mode_switch")
        brain._ctx.build.assert_not_called()

    def test_cache_hit_skips_llm(self):
        brain = _brain_with_mocks()
        brain._cache.get.return_value = {
            "reply": "cached answer", "emotion": "neutral", "intent": "general",
            "agent": "cache", "confidence": 0.9, "tool_used": False,
            "memory_updated": False, "confidence_label": "HIGH", "confidence_emoji": "🟢"
        }
        result = brain.process("what is python")
        self.assertEqual(result["reply"], "cached answer")
        brain._ctx.build.assert_not_called()

    def test_chain_reply_skips_llm(self):
        brain = _brain_with_mocks()
        brain._exit.check_chain.return_value = "Chain result: done"
        result = brain.process("search then summarise")
        self.assertEqual(result["intent"], "chain")

    def test_intent_shortcut_skips_llm(self):
        brain = _brain_with_mocks()
        brain._exit.check_intent_shortcut.return_value = "Hey Arnav!"
        result = brain.process("hi")
        self.assertEqual(result["intent"], "shortcut")
        brain._ctx.build.assert_not_called()

    def test_self_query_skips_llm(self):
        brain = _brain_with_mocks()
        brain._exit.check_self_query.return_value = "I am ASTRA."
        result = brain.process("who are you")
        self.assertEqual(result["intent"], "self_awareness")
        brain._ctx.build.assert_not_called()

    def test_empty_input_returns_error(self):
        brain = _brain_with_mocks()
        result = brain.process("   ")
        self.assertEqual(result["intent"], "error")
        self.assertEqual(result["confidence"], 0.0)


# ── Memory ─────────────────────────────────────────────────────────────────

class TestMemory(unittest.TestCase):

    def test_fact_stored_returns_ack(self):
        brain = _brain_with_mocks()
        fake_fact = {"type": "identity", "value": "Arnav", "fact": "User's name is Arnav"}
        brain._mem.extract_and_store_fact.return_value = (fake_fact, _fake_memory())
        brain._mem.acknowledge_fact.return_value       = "Got it. User's name is Arnav."
        with patch("core.brain.is_question_like", return_value=False):
            result = brain.process("my name is Arnav")
        self.assertEqual(result["intent"], "memory_storage")
        self.assertTrue(result["memory_updated"])

    def test_memory_recall_skips_llm(self):
        brain = _brain_with_mocks()
        brain._mem.recall.return_value = "Your name is Arnav."
        result = brain.process("what is my name")
        self.assertEqual(result["intent"], "memory_recall")
        brain._ctx.build.assert_not_called()

    @patch("ollama.chat")
    def test_post_turn_called_after_llm(self, mock_chat):
        mock_chat.return_value = _fake_ollama_response("Some reply.")
        brain = _brain_with_mocks()
        brain.process("tell me something")
        brain._mem.post_turn.assert_called_once()


# ── Web search ─────────────────────────────────────────────────────────────

class TestWebSearch(unittest.TestCase):

    def test_web_search_triggered_on_keyword(self):
        brain = _brain_with_mocks()
        brain.capabilities.is_enabled.return_value = True
        brain.search_agent.run.return_value = {
            "reply": "Latest Python news.", "citations": [], "results_count": 5
        }
        result = brain.process("latest python news")
        self.assertEqual(result["intent"], "web_search")
        brain.search_agent.run.assert_called_once()

    def test_local_query_skips_web_search(self):
        brain = _brain_with_mocks()
        brain.capabilities.is_enabled.return_value = True
        with patch("ollama.chat") as mock_chat:
            mock_chat.return_value = _fake_ollama_response("Here is your code.")
            brain.process("show me my code")
        brain.search_agent.run.assert_not_called()


# ── Post-processor ─────────────────────────────────────────────────────────

class TestPostProcessor(unittest.TestCase):

    @patch("ollama.chat")
    def test_post_processor_called_with_reply(self, mock_chat):
        mock_chat.return_value = _fake_ollama_response("Raw LLM reply.")
        brain = _brain_with_mocks()
        brain.process("explain neural networks")
        brain._post.process.assert_called_once()
        self.assertEqual(brain._post.process.call_args[0][0], "Raw LLM reply.")

    @patch("ollama.chat")
    def test_post_processor_output_is_final_reply(self, mock_chat):
        mock_chat.return_value = _fake_ollama_response("Raw reply.")
        brain = _brain_with_mocks()
        brain._post.process.side_effect = lambda r, *a, **kw: "POLISHED: " + r
        result = brain.process("hello")
        self.assertTrue(result["reply"].startswith("POLISHED:"))


# ── Error resilience ───────────────────────────────────────────────────────

class TestErrorResilience(unittest.TestCase):

    @patch("ollama.chat", side_effect=Exception("Ollama is down"))
    def test_ollama_failure_does_not_crash(self, mock_chat):
        brain = _brain_with_mocks()
        result = brain.process("hello")
        self.assertIn("reply", result)
        self.assertNotEqual(result["reply"], "")

    def test_broken_memory_returns_error_reply(self):
        brain = _brain_with_mocks()
        brain._mem.load.side_effect = Exception("DB corrupt")
        result = brain.process("hello")
        self.assertIn("reply", result)


# ── Streaming ──────────────────────────────────────────────────────────────

class TestStreaming(unittest.TestCase):

    def _stream_chunks(self, words):
        for word in words:
            chunk = MagicMock()
            chunk.__getitem__ = lambda s, k, w=word: {"message": {"content": w + " "}}[k]
            yield chunk

    @patch("ollama.chat")
    def test_stream_yields_tokens(self, mock_chat):
        brain = _brain_with_mocks()
        mock_chat.return_value = self._stream_chunks(["Hello", "world"])
        tokens = [i for i in brain.process_stream("say hello") if "token" in i]
        self.assertGreater(len(tokens), 0)

    @patch("ollama.chat")
    def test_stream_ends_with_meta(self, mock_chat):
        brain = _brain_with_mocks()
        mock_chat.return_value = self._stream_chunks(["test"])
        items = list(brain.process_stream("hello"))
        self.assertIn("meta", items[-1])
        self.assertIn("full",   items[-1]["meta"])
        self.assertIn("intent", items[-1]["meta"])

    def test_stream_empty_input_yields_error_token(self):
        brain = _brain_with_mocks()
        items = list(brain.process_stream("   "))
        self.assertEqual(len(items), 1)
        self.assertIn("token", items[0])

    def test_stream_cache_hit_yields_words(self):
        brain = _brain_with_mocks()
        brain._cache.get.return_value = {"reply": "cached streaming reply"}
        tokens = [i["token"] for i in brain.process_stream("hello") if "token" in i]
        self.assertGreater(len(tokens), 0)
        self.assertIn("cached", " ".join(tokens))


# ── Helpers ────────────────────────────────────────────────────────────────

class TestHelpers(unittest.TestCase):

    def test_build_reply_has_all_keys(self):
        brain = _brain_with_mocks()
        result = brain._build_reply("hello", "neutral", "general", "phi3:mini")
        for key in ["reply", "emotion", "intent", "agent", "confidence",
                    "tool_used", "memory_updated", "confidence_label", "confidence_emoji"]:
            self.assertIn(key, result)

    def test_error_reply_zero_confidence(self):
        brain = _brain_with_mocks()
        result = brain._error_reply("Something broke")
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["intent"],     "error")

    def test_history_capped_at_12(self):
        brain = _brain_with_mocks()
        for i in range(20):
            brain._add_to_history("user", f"message {i}")
        self.assertLessEqual(len(brain.conversation_history), 12)

    def test_needs_web_search_triggers(self):
        from core.brain import _needs_web_search
        self.assertTrue(_needs_web_search("latest AI news"))
        self.assertTrue(_needs_web_search("search for python tips"))
        self.assertFalse(_needs_web_search("how do I write a for loop"))

    def test_is_local_query(self):
        from core.brain import _is_local_query
        self.assertTrue(_is_local_query("show me my code"))
        self.assertTrue(_is_local_query("where is my project"))
        self.assertFalse(_is_local_query("what is machine learning"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
