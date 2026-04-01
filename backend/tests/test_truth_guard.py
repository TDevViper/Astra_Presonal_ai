"""Tests for TruthGuard — hallucination and identity protection."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.truth_guard import TruthGuard


@pytest.fixture
def guard():
    return TruthGuard(user_name="Arnav", user_location="Delhi")


# ── Static forbidden patterns ─────────────────────────────────


def test_blocks_created_by_anthropic(guard):
    ok, vtype = guard.validate("I was created by Anthropic.")
    assert ok is False
    assert vtype == "wrong_creator"


def test_blocks_made_by_anthropic(guard):
    ok, vtype = guard.validate("I was made by Anthropic.")
    assert ok is False
    assert vtype == "wrong_creator"


def test_blocks_built_by_openai(guard):
    ok, vtype = guard.validate("I was built by OpenAI.")
    assert ok is False
    assert vtype == "wrong_creator"


def test_blocks_i_am_chatgpt(guard):
    ok, vtype = guard.validate("I am ChatGPT, here to help.")
    assert ok is False
    assert vtype == "wrong_creator"


def test_blocks_i_am_gpt(guard):
    ok, vtype = guard.validate("I am GPT.")
    assert ok is False
    assert vtype == "wrong_creator"


def test_allows_correct_identity(guard):
    ok, _ = guard.validate("I am ASTRA, your personal AI assistant.")
    assert ok is True


# ── Location guard ────────────────────────────────────────────


def test_blocks_wrong_location(guard):
    ok, vtype = guard.validate("You live in Mumbai.")
    assert ok is False
    assert vtype == "wrong_location"


def test_allows_correct_location(guard):
    ok, _ = guard.validate("You live in Delhi.")
    assert ok is True


def test_no_location_guard_when_location_unknown():
    g = TruthGuard(user_name="Arnav", user_location="")
    ok, _ = g.validate("You live in Mumbai.")
    assert ok is True  # no location set — no guard active


# ── Name hallucination guard ──────────────────────────────────


def test_blocks_name_hallucination(guard):
    ok, vtype = guard.validate("I don't know your name.")
    assert ok is False
    assert vtype == "name_hallucination"


def test_blocks_user_name_hallucination(guard):
    ok, vtype = guard.validate("I don't know the user's name.")
    assert ok is False
    assert vtype == "name_hallucination"


# ── update_user_info ──────────────────────────────────────────


def test_update_user_info_changes_location_guard():
    g = TruthGuard(user_name="Arnav", user_location="Delhi")
    g.update_user_info(user_location="Mumbai")
    ok, vtype = g.validate("You live in Delhi.")
    assert ok is False
    assert vtype == "wrong_location"


def test_update_user_info_name():
    g = TruthGuard()
    g.update_user_info(user_name="Arnav")
    assert g.user_name == "Arnav"


# ── Safe reply ────────────────────────────────────────────────


def test_safe_reply_wrong_creator_mentions_user(guard):
    reply = guard.get_safe_reply("wrong_creator")
    assert "ASTRA" in reply


def test_safe_reply_name_hallucination_includes_name(guard):
    reply = guard.get_safe_reply("name_hallucination")
    assert "Arnav" in reply


def test_safe_reply_unknown_violation_returns_default(guard):
    reply = guard.get_safe_reply("nonexistent_type")
    assert len(reply) > 0


# ── Case insensitivity ────────────────────────────────────────


def test_validation_is_case_insensitive(guard):
    ok, vtype = guard.validate("I WAS CREATED BY ANTHROPIC.")
    assert ok is False
    assert vtype == "wrong_creator"
