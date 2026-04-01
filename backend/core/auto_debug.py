# core/auto_debug.py
# JARVIS-level: detect error → search → reason → propose fix
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def run_auto_debug(
    error_text: str, user_name: str = "User", model: str = "phi3:mini"
) -> Dict:
    """
    Full auto-debug pipeline:
    1. Extract clean error message
    2. Web search for solution
    3. ReAct to reason about fix
    4. Propose git commit with fix (if code change needed)
    Returns dict with reply, fix_proposed, commit_proposal
    """
    logger.info("🔍 Auto-debug: %s", error_text[:60])
    results = {
        "error": error_text,
        "reply": "",
        "fix_proposed": False,
        "commit_proposal": None,
        "search_results": None,
    }

    # Step 1 — clean up the error
    clean_error = _extract_core_error(error_text)

    # Step 2 — web search
    try:
        from websearch.search_agent import WebSearchAgent

        search_result = WebSearchAgent(model=model).run(
            f"{clean_error} fix solution", user_name
        )
        results["search_results"] = search_result.get("reply", "")
        logger.info("✅ Search complete")
    except Exception as e:
        logger.warning("auto_debug search failed: %s", e)
        results["search_results"] = ""

    # Step 3 — ReAct reasoning
    try:
        from agents.react_agent import react_solve

        context = f"Error found on screen: {clean_error}\nSearch results: {results['search_results'][:500]}"
        react_result = react_solve(
            f"How do I fix this error: {clean_error}",
            model=model,
            context=context,
            user_name=user_name,
        )
        if react_result["success"]:
            results["reply"] = react_result["answer"]
            logger.info("✅ ReAct reasoning complete")
    except Exception as e:
        logger.warning("auto_debug react failed: %s", e)
        # Fallback to search result
        results["reply"] = (
            f"Found this error: **{clean_error}**\n\n{results['search_results'][:400]}"
        )

    # Step 4 — check if a code fix is applicable
    if _looks_like_code_error(clean_error):
        try:
            from tools.git_tool import is_git_repo, git_diff

            if is_git_repo():
                diff = git_diff()
                if diff["success"] and diff["output"]:
                    from tools.git_tool import propose_git_commit

                    proposal = propose_git_commit(f"fix: {clean_error[:50]}")
                    if proposal["success"]:
                        results["fix_proposed"] = True
                        results["commit_proposal"] = proposal
                        results["reply"] += (
                            "\n\n💡 I've prepared a commit proposal with the fix."
                        )
        except Exception as e:
            logger.debug("commit proposal skipped: %s", e)

    return results


def _extract_core_error(text: str) -> str:
    """Pull the most meaningful line from an error block."""
    import re

    # Try to get the last traceback line
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    for line in reversed(lines):
        if any(
            w in line
            for w in [
                "Error:",
                "Exception:",
                "TypeError",
                "ValueError",
                "AttributeError",
                "ImportError",
                "KeyError",
                "NameError",
                "SyntaxError",
                "RuntimeError",
            ]
        ):
            return line[:200]
    # Fallback: first non-trivial line
    for line in lines:
        if len(line) > 10:
            return line[:200]
    return text[:200]


def _looks_like_code_error(error: str) -> bool:
    code_indicators = [
        "Error:",
        "Exception",
        "Traceback",
        "undefined",
        "cannot find module",
        "import error",
        "syntax error",
        "is not defined",
        "has no attribute",
    ]
    return any(w.lower() in error.lower() for w in code_indicators)
