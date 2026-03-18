"""Expanded tests for memory_extractor and intent classifier."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory.memory_extractor import extract_user_fact
from intents.classifier import is_question_like


# ── Identity / name ───────────────────────────────────────────

def test_name_my_name_is():
    r = extract_user_fact("My name is Arnav")
    assert r is not None
    assert r["type"] == "identity"
    assert "Arnav" in r["value"]

def test_name_call_me():
    r = extract_user_fact("Call me Arnav")
    assert r is not None
    assert r["type"] == "identity"

def test_name_i_am_not_supported():
    # "I am X" is ambiguous ("I am happy") — extractor intentionally excludes it
    r = extract_user_fact("I am Arnav")
    assert r is None


# ── Location ──────────────────────────────────────────────────

def test_location_i_live_in():
    r = extract_user_fact("I live in Delhi")
    assert r is not None
    assert r["type"] == "location"

def test_location_i_am_from():
    r = extract_user_fact("I am from Mumbai")
    assert r is not None
    assert r["type"] == "location"


# ── Hobby ─────────────────────────────────────────────────────

def test_hobby_i_love():
    r = extract_user_fact("I love playing chess")
    assert r is not None
    assert r["type"] == "hobby"
    assert r["value"] == "chess"

def test_hobby_i_enjoy():
    r = extract_user_fact("I enjoy reading books")
    assert r is not None
    assert r["type"] == "hobby"

def test_hobby_i_like():
    r = extract_user_fact("I like hiking")
    assert r is not None
    assert r["type"] == "hobby"


# ── No match ──────────────────────────────────────────────────

def test_no_match_question():
    assert extract_user_fact("What is the weather today?") is None

def test_no_match_generic_statement():
    assert extract_user_fact("The sky is blue") is None

def test_no_match_empty_string():
    assert extract_user_fact("") is None

def test_no_match_greeting():
    assert extract_user_fact("Hello, how are you?") is None


# ── Return structure ──────────────────────────────────────────

def test_result_has_required_keys():
    r = extract_user_fact("My name is Arnav")
    assert r is not None
    assert "type" in r
    assert "value" in r

def test_result_value_is_string():
    r = extract_user_fact("I live in Delhi")
    assert r is not None
    assert isinstance(r["value"], str)


# ── Intent classifier ─────────────────────────────────────────

def test_question_with_mark():
    assert is_question_like("What are my hobbies?") is True

def test_question_word_what():
    assert is_question_like("What time is it") is True

def test_question_word_how():
    assert is_question_like("How do I reset my password") is True

def test_question_word_where():
    assert is_question_like("Where do I live") is True

def test_question_word_who():
    assert is_question_like("Who am I") is True

def test_question_word_when():
    assert is_question_like("When is my birthday") is True

def test_statement_not_question():
    assert is_question_like("I love playing chess") is False

def test_statement_name_not_question():
    assert is_question_like("My name is Arnav") is False

def test_empty_string_not_question():
    assert is_question_like("") is False
