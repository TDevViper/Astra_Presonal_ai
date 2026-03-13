import os
# ==========================================
# knowledge/entity_extractor.py
# Extracts (subject, relation, object) triples
# from conversation turns using local LLM
# ==========================================

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Relations ASTRA understands
KNOWN_RELATIONS = [
    "works_on", "likes", "dislikes", "prefers", "uses",
    "knows", "lives_in", "works_at", "studies", "created",
    "built_with", "related_to", "part_of", "has", "wants",
    "is_a", "located_in", "friend_of", "works_with",
]

# Rule-based patterns — fast, no LLM needed
PATTERNS = [
    # "I am working on ASTRA"
    (r"i(?:'m| am) working on (.+)",           "__USER__", "works_on",   1),
    (r"i(?:'m| am) building (.+)",             "__USER__", "works_on",   1),
    (r"i(?:'m| am) creating (.+)",             "__USER__", "works_on",   1),
    # "I like / love / enjoy Python"
    (r"i (?:like|love|enjoy|prefer) (.+)",     "__USER__", "likes",      1),
    (r"i (?:hate|dislike|don't like) (.+)",    "__USER__", "dislikes",   1),
    # "I use FastAPI / VSCode"
    (r"i use (.+)",                            "__USER__", "uses",       1),
    (r"i(?:'m| am) using (.+)",                "__USER__", "uses",       1),
    # "I live in Mumbai"
    (r"i live in (.+)",                        "__USER__", "lives_in",   1),
    (r"i(?:'m| am) (?:from|in) (.+)",          "__USER__", "lives_in",   1),
    # "I study / learn X"
    (r"i(?:'m| am)? ?(?:studying|learning) (.+)", "__USER__", "studies", 1),
    # "I work at X"
    (r"i work (?:at|for) (.+)",                "__USER__", "works_at",   1),
    # "My name is X"
    (r"my name is (\w+)",                      "__USER__", "is_a",       1),
    # "X is built with Y"
    (r"(\w+) is built (?:with|using) (.+)",    None,    "built_with", None),
    # "X uses Y"
    (r"(\w+) uses (.+)",                       None,    "uses",       None),
]


def extract_triples_rules(text: str,
                           user_name: str = "Arnav") -> List[Tuple[str, str, str]]:
    """
    Fast rule-based extraction — no LLM.
    Returns list of (subject, relation, object) tuples.
    """
    triples = []
    t       = text.lower().strip()

    for pattern, fixed_subj, relation, obj_group in PATTERNS:
        m = re.search(pattern, t)
        if not m:
            continue

        if fixed_subj is not None:
            subject = user_name
            obj     = m.group(obj_group).strip(" .,!?") if obj_group else ""
        else:
            groups = m.groups()
            if len(groups) < 2:
                continue
            subject = groups[0].strip()
            obj     = groups[1].strip(" .,!?")

        # Clean up
        obj = obj.split(" and ")[0]   # "Python and Flask" → "Python"
        obj = obj.split(",")[0]        # "Python, Flask" → "Python"
        obj = obj[:40]                 # cap length

        if subject and obj and len(obj) > 1:
            triples.append((subject, relation, obj))

    return triples


def extract_triples_llm(text: str,
                         user_name: str = "Arnav") -> List[Tuple[str, str, str]]:
    """
    LLM-powered extraction for complex sentences.
    Falls back to empty list on failure.
    """
    try:
        import ollama
        import requests

        LOCAL_HOST = "http://localhost:11434"
        GPU_HOST   = os.getenv("REMOTE_GPU_HOST", "")

        try:
            alive = requests.get(GPU_HOST, timeout=1).status_code == 200
        except Exception:
            alive = False

        client = ollama.Client(host=GPU_HOST if alive else LOCAL_HOST)
        model  = "phi3:mini"  # Use fast model for extraction

        known = ", ".join(KNOWN_RELATIONS)
        prompt = f"""Extract knowledge graph triples from this sentence.
Output ONLY lines in this exact format (one per line):
subject | relation | object

Relations to use: {known}
Use "{user_name}" as subject when the person refers to themselves.

Sentence: {text}

Triples (or NONE if nothing to extract):"""

        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0, "num_predict": 100}
        )
        raw = response["message"]["content"].strip()

        if raw.upper() == "NONE" or not raw:
            return []

        triples = []
        for line in raw.split("\n"):
            line = line.strip()
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                continue
            subject, relation, obj = parts
            relation = relation.lower().replace(" ", "_")
            # Only accept known relations
            if relation not in KNOWN_RELATIONS:
                relation = "related_to"
            if subject and relation and obj:
                triples.append((subject, relation, obj))

        return triples

    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
        return []


def extract_and_store(text: str, user_name: str = "Arnav",
                      use_llm: bool = False) -> int:
    """
    Main entry point — extract triples and store in graph.
    Returns number of triples stored.
    """
    from knowledge.graph import add_entity, add_relation

    # Always run rule-based (fast)
    triples = extract_triples_rules(text, user_name)

    # Optionally run LLM extraction for complex sentences
    if use_llm and len(text.split()) > 8:
        llm_triples = extract_triples_llm(text, user_name)
        # Merge, deduplicate
        existing = {(s, r, o) for s, r, o in triples}
        for t in llm_triples:
            if t not in existing:
                triples.append(t)

    count = 0
    for subject, relation, obj in triples:
        # Ensure entities exist
        add_entity(subject, entity_type="person" if subject.lower() == user_name.lower() else "concept")
        add_entity(obj)
        add_relation(subject, relation, obj)
        count += 1

    if count:
        logger.info(f"📊 Stored {count} graph triples from: {text[:60]}")

    return count
