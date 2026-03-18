"""
tests/eval/harness.py — AI quality eval harness for ASTRA.

Runs Brain.process() against a set of test cases and scores each response
against expected criteria. No Ollama required — uses the same mocks as
test_brain.py but with quality assertions instead of structural ones.

Scoring:
  PASS   — response meets all criteria
  FAIL   — response fails one or more criteria
  SKIP   — response was blocked/cached (not an LLM response)

Usage:
  pytest tests/eval/ -v
  pytest tests/eval/ -v --tb=short   # CI mode
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class EvalCase:
    id:          str
    input:       str
    checks:      List[Callable[[str], bool]]
    description: str = ""
    tags:        List[str] = field(default_factory=list)

    def run(self, reply: str) -> dict:
        results = []
        for check in self.checks:
            try:
                passed = check(reply)
            except Exception as e:
                passed = False
            results.append({"check": check.__name__, "passed": passed})
        passed_all = all(r["passed"] for r in results)
        return {
            "id":          self.id,
            "input":       self.input,
            "reply":       reply,
            "passed":      passed_all,
            "checks":      results,
            "description": self.description,
        }


# ── Check helpers ─────────────────────────────────────────────────────────────

def not_empty(reply: str) -> bool:
    """Reply is not empty."""
    return bool(reply and reply.strip())

def not_error(reply: str) -> bool:
    """Reply is not an error message."""
    return "something went wrong" not in reply.lower()

def not_blocked(reply: str) -> bool:
    """Reply was not blocked by injection filter."""
    return "[blocked" not in reply.lower()

def min_length(n: int):
    def check(reply: str) -> bool:
        return len(reply.strip()) >= n
    check.__name__ = f"min_length_{n}"
    return check

def contains_any(*phrases: str):
    def check(reply: str) -> bool:
        r = reply.lower()
        return any(p.lower() in r for p in phrases)
    check.__name__ = f"contains_any({', '.join(phrases[:2])})"
    return check

def contains_none(*phrases: str):
    def check(reply: str) -> bool:
        r = reply.lower()
        return not any(p.lower() in r for p in phrases)
    check.__name__ = f"contains_none({', '.join(phrases[:2])})"
    return check

def matches_pattern(pattern: str):
    def check(reply: str) -> bool:
        return bool(re.search(pattern, reply, re.IGNORECASE))
    check.__name__ = f"matches_pattern({pattern[:30]})"
    return check

def confidence_above(threshold: float):
    """Not a reply check — used separately on result dict."""
    def check(reply: str) -> bool:
        return True  # placeholder; confidence checked in test body
    check.__name__ = f"confidence_above_{threshold}"
    return check
