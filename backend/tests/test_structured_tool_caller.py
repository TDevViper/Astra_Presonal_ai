"""
Tests for StructuredToolCaller.
No real Ollama or tool execution needed — all mocked.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_stc():
    mm = MagicMock()
    te = MagicMock()
    br = MagicMock(
        return_value={
            "reply": "ok",
            "intent": "tool_git",
            "agent": "tool/git",
            "confidence": 0.92,
        }
    )
    from core.structured_tool_caller import StructuredToolCaller

    return StructuredToolCaller(mm, te, br)


def test_no_schemas_returns_none_for_old_model():
    stc = _make_stc()
    with patch("tools.tool_schemas.get_schemas_for_model", return_value=[]):
        result = stc.try_tool_call("git status", "sys", "phi3:mini", [], {}, "User")
    assert result is None


def test_llm_no_tool_call_returns_none():
    stc = _make_stc()
    fake_resp = {
        "message": {"content": "I don't need a tool for that.", "tool_calls": []}
    }
    with patch(
        "tools.tool_schemas.get_schemas_for_model",
        return_value=[{"type": "function", "function": {"name": "git"}}],
    ):
        with patch("ollama.Client") as mock_client:
            mock_client.return_value.chat.return_value = fake_resp
            result = stc.try_tool_call(
                "hello how are you", "sys", "llama3.2", [], {}, "User"
            )
    assert result is None


def test_llm_tool_call_triggers_execution():
    stc = _make_stc()
    fake_resp = {
        "message": {
            "tool_calls": [
                {
                    "function": {
                        "name": "system_monitor",
                        "arguments": {"detail": "summary"},
                    }
                }
            ]
        }
    }
    with patch(
        "tools.tool_schemas.get_schemas_for_model",
        return_value=[{"type": "function", "function": {"name": "system_monitor"}}],
    ):
        with patch("ollama.Client") as mock_client:
            mock_client.return_value.chat.return_value = fake_resp
            with patch.object(
                stc, "_execute_tool", return_value="CPU: 45%"
            ) as mock_exec:
                with patch.object(
                    stc, "_synthesize_reply", return_value="Your CPU is at 45%."
                ):
                    result = stc.try_tool_call(
                        "how's my cpu", "sys", "llama3.2", [], {}, "User"
                    )
    mock_exec.assert_called_once_with(
        "system_monitor", {"detail": "summary"}, "how's my cpu", {}, "User"
    )
    assert result is not None
    assert result["tool_used"] is True


def test_tool_schemas_exist_for_capable_models():
    from tools.tool_schemas import get_schemas_for_model

    schemas = get_schemas_for_model("llama3.2:3b")
    assert len(schemas) > 0
    names = [s["function"]["name"] for s in schemas]
    assert "web_search" in names
    assert "task_manager" in names
    assert "git" in names


def test_tool_schemas_empty_for_incapable_models():
    from tools.tool_schemas import get_schemas_for_model

    schemas = get_schemas_for_model("phi3:mini")
    assert schemas == []


def test_args_as_json_string_parsed_correctly():
    stc = _make_stc()
    import json

    fake_resp = {
        "message": {
            "tool_calls": [
                {
                    "function": {
                        "name": "git",
                        "arguments": json.dumps({"operation": "status"}),
                    }
                }
            ]
        }
    }
    with patch(
        "tools.tool_schemas.get_schemas_for_model",
        return_value=[{"type": "function", "function": {"name": "git"}}],
    ):
        with patch("ollama.Client") as mock_client:
            mock_client.return_value.chat.return_value = fake_resp
            with patch.object(stc, "_execute_tool", return_value="clean") as mock_exec:
                with patch.object(
                    stc, "_synthesize_reply", return_value="Repo is clean."
                ):
                    stc.try_tool_call("git status", "sys", "llama3.2", [], {}, "User")
    # args should be parsed from JSON string to dict
    mock_exec.assert_called_once_with(
        "git", {"operation": "status"}, "git status", {}, "User"
    )


def test_execute_tool_unknown_returns_none():
    stc = _make_stc()
    result = stc._execute_tool("nonexistent_tool", {}, "input", {}, "User")
    assert result is None


def test_synthesis_failure_returns_raw_tool_result():
    stc = _make_stc()
    with patch("ollama.Client") as mock_client:
        mock_client.return_value.chat.side_effect = Exception("Ollama down")
        with patch("config.config") as mock_cfg:
            mock_cfg.OLLAMA_HOST = "http://localhost:11434"
            result = stc._synthesize_reply(
                "q", "git", "CPU: 80%", "sys", "llama3.2", []
            )
    assert result == "CPU: 80%"
