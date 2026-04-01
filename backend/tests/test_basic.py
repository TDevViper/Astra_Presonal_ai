"""Basic sanity tests for ASTRA core modules."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_memory_extractor_name():
    from memory.memory_extractor import extract_user_fact

    result = extract_user_fact("My name is Arnav")
    assert result is not None
    assert result["type"] == "identity"
    assert "Arnav" in result["value"]


def test_memory_extractor_hobby():
    from memory.memory_extractor import extract_user_fact

    result = extract_user_fact("I love playing chess")
    assert result is not None
    assert result["type"] == "hobby"
    assert result["value"] == "chess"


def test_memory_extractor_location():
    from memory.memory_extractor import extract_user_fact

    result = extract_user_fact("I live in Delhi")
    assert result is not None
    assert result["type"] == "location"


def test_memory_extractor_no_match():
    from memory.memory_extractor import extract_user_fact

    result = extract_user_fact("What is the weather today?")
    assert result is None


def test_is_question_like():
    from intents.classifier import is_question_like

    assert is_question_like("What are my hobbies?")
    assert not is_question_like("I love playing chess")
