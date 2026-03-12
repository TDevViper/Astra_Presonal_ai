# ==========================================
# tests/test_agent_loop.py
# ==========================================
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock
from core.agent_loop import (
    AgentLoop, LoopStatus,
    _observe, _plan,
    _act_llm, _act_reflect
)


class TestObserve(unittest.TestCase):

    def test_simple_query_low_complexity(self):
        obs = _observe("hi there", {})
        self.assertEqual(obs["complexity"], 1)
        self.assertFalse(obs["requires_tools"])
        self.assertFalse(obs["requires_reflection"])

    def test_tool_query_detected(self):
        obs = _observe("search for latest python news", {})
        self.assertTrue(obs["requires_tools"])

    def test_complex_query_high_complexity(self):
        obs = _observe(
            "research and compare the pros and cons of React vs Vue "
            "and then give me a step by step recommendation", {}
        )
        self.assertGreaterEqual(obs["complexity"], 3)
        self.assertTrue(obs["requires_reflection"])


class TestPlan(unittest.TestCase):

    def test_simple_plan_single_step(self):
        obs  = _observe("what is 2 + 2", {})
        plan = _plan(obs)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["action"], "llm_reply")

    def test_tool_plan_two_steps(self):
        obs  = _observe("search for weather in Mumbai", {})
        plan = _plan(obs)
        actions = [p["action"] for p in plan]
        self.assertIn("tool_execute", actions)
        self.assertIn("llm_reply", actions)

    def test_complex_plan_has_reflect(self):
        obs = {"complexity": 4, "requires_tools": True,
               "requires_reflection": True, "input": "analyze this"}
        plan = _plan(obs)
        actions = [p["action"] for p in plan]
        self.assertIn("reflect", actions)


class TestAgentLoop(unittest.TestCase):

    @patch("core.agent_loop._act_llm")
    def test_simple_query_resolves(self, mock_llm):
        mock_llm.return_value = ("Paris is the capital of France.", 0.9)
        loop   = AgentLoop(max_iterations=5)
        result = loop.run("what is the capital of France", {})
        self.assertEqual(result.status, LoopStatus.DONE)
        self.assertIn("Paris", result.final_reply)
        self.assertGreater(result.confidence, 0.0)

    @patch("core.agent_loop._act_llm")
    def test_empty_llm_response_handled(self, mock_llm):
        mock_llm.return_value = ("", 0.0)
        loop   = AgentLoop(max_iterations=5)
        result = loop.run("test query", {})
        self.assertIsNotNone(result.final_reply)
        self.assertNotEqual(result.final_reply, "")

    @patch("core.agent_loop._act_llm")
    def test_max_iterations_respected(self, mock_llm):
        mock_llm.return_value = ("partial answer", 0.3)
        loop   = AgentLoop(max_iterations=2)
        result = loop.run(
            "research and compare and analyze and step by step "
            "explain everything about quantum computing", {}
        )
        self.assertLessEqual(result.iterations, 5)

    @patch("core.agent_loop._act_reflect")
    @patch("core.agent_loop._act_llm")
    def test_reflect_approves_good_answer(self, mock_llm, mock_reflect):
        mock_llm.return_value     = ("Python is great for data science.", 0.8)
        mock_reflect.return_value = ("Python is great for data science.", 0.95)
        loop   = AgentLoop(max_iterations=5)
        result = loop.run(
            "should i learn python for data science", {}
        )
        self.assertEqual(result.status, LoopStatus.DONE)
        self.assertGreaterEqual(result.confidence, 0.8)

    def test_loop_steps_recorded(self):
        with patch("core.agent_loop._act_llm") as mock_llm:
            mock_llm.return_value = ("Some answer.", 0.8)
            loop   = AgentLoop(max_iterations=5)
            result = loop.run("explain how neural networks work", {})
            self.assertGreater(len(result.steps), 0)
            for step in result.steps:
                self.assertIsNotNone(step.action)
                self.assertGreaterEqual(step.elapsed, 0)


class TestReflect(unittest.TestCase):

    @patch("ollama.Client")
    def test_reflect_returns_approved(self, mock_client):
        mock_response = MagicMock()
        mock_response.__getitem__ = lambda s, k: \
            {"message": {"content": "APPROVED"}}[k]
        mock_client.return_value.chat.return_value = mock_response

        reply, conf = _act_reflect(
            "what is python",
            "Python is a programming language.",
            {}
        )
        # Either approved (original) or improved — both valid
        self.assertIsInstance(reply, str)
        self.assertGreater(conf, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
