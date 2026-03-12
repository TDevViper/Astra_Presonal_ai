# ==========================================
# knowledge/graph.py
# NetworkX knowledge graph with persistence
# Stores: entities, relations, attributes
# ==========================================

import os
import json
import logging
import networkx as nx
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from utils.logger import system_logger, log_event

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_FILE   = os.path.join(_BACKEND_DIR, "memory", "data", "knowledge_graph.json")

# Singleton graph
_graph: Optional[nx.DiGraph] = None


def _utcnow() -> str:
    """Return current UTC time as ISO string. Works on Python 3.8+."""
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════
# PERSISTENCE
# ══════════════════════════════════════════

def _get_graph() -> nx.DiGraph:
    global _graph
    if _graph is None:
        _graph = _load_graph()
    return _graph


def _load_graph() -> nx.DiGraph:
    os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
    if not os.path.exists(GRAPH_FILE):
        log_event(system_logger, "graph_created")
        return nx.DiGraph()
    try:
        with open(GRAPH_FILE) as f:
            data = json.load(f)
        G = nx.DiGraph()
        for node in data.get("nodes", []):
            G.add_node(node["id"], **node.get("attrs", {}))
        for edge in data.get("edges", []):
            G.add_edge(edge["src"], edge["dst"],
                       relation=edge["relation"],
                       weight=edge.get("weight", 1.0),
                       ts=edge.get("ts", _utcnow()))
        log_event(system_logger, "graph_loaded",
                  nodes=G.number_of_nodes(),
                  edges=G.number_of_edges())
        return G
    except Exception as e:
        logger.error(f"Graph load error: {e}")
        return nx.DiGraph()


def save_graph() -> bool:
    try:
        G = _get_graph()
        data = {
            "nodes": [
                {"id": n, "attrs": dict(G.nodes[n])}
                for n in G.nodes
            ],
            "edges": [
                {
                    "src":      u,
                    "dst":      v,
                    "relation": d.get("relation", "related_to"),
                    "weight":   d.get("weight", 1.0),
                    "ts":       d.get("ts", _utcnow()),
                }
                for u, v, d in G.edges(data=True)
            ],
        }
        with open(GRAPH_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Graph save error: {e}")
        return False


# ══════════════════════════════════════════
# WRITE
# ══════════════════════════════════════════

def add_entity(name: str, entity_type: str = "concept",
               **attrs) -> str:
    """
    Add or update a node.
    node_id = lowercase name, spaces → underscores
    """
    G       = _get_graph()
    node_id = name.lower().replace(" ", "_")

    if G.has_node(node_id):
        G.nodes[node_id].update(attrs)
        G.nodes[node_id]["updated_at"] = _utcnow()
    else:
        G.add_node(node_id,
                   label       = name,
                   entity_type = entity_type,
                   created_at  = _utcnow(),
                   **attrs)

    log_event(system_logger, "graph_add_entity",
              node=node_id, type=entity_type)
    return node_id


def add_relation(subject: str, relation: str, obj: str,
                 weight: float = 1.0) -> bool:
    """
    Add directed edge: subject –[relation]→ object
    Example: add_relation("arnav", "works_on", "astra")
    """
    G   = _get_graph()
    src = subject.lower().replace(" ", "_")
    dst = obj.lower().replace(" ", "_")

    # Auto-create nodes if missing
    if not G.has_node(src):
        add_entity(subject)
    if not G.has_node(dst):
        add_entity(obj)

    # Strengthen weight if relation already exists
    if G.has_edge(src, dst):
        existing = G[src][dst]
        if existing.get("relation") == relation:
            G[src][dst]["weight"] = min(existing["weight"] + 0.1, 2.0)
            G[src][dst]["ts"]     = _utcnow()
            return True

    G.add_edge(src, dst,
               relation = relation,
               weight   = weight,
               ts       = _utcnow())

    log_event(system_logger, "graph_add_relation",
              src=src, relation=relation, dst=dst)
    save_graph()
    return True


# ══════════════════════════════════════════
# READ
# ══════════════════════════════════════════

def get_relations(entity: str, depth: int = 1) -> List[Dict]:
    """
    Get all relations for an entity up to `depth` hops.
    Returns list of {subject, relation, object, weight} dicts.
    """
    G       = _get_graph()
    node_id = entity.lower().replace(" ", "_")

    if not G.has_node(node_id):
        return []

    results = []

    # Outgoing edges
    for _, dst, data in G.out_edges(node_id, data=True):
        dst_label = G.nodes[dst].get("label", dst)
        results.append({
            "subject":  entity,
            "relation": data.get("relation", "related_to"),
            "object":   dst_label,
            "weight":   data.get("weight", 1.0),
            "dir":      "out",
        })

    # Incoming edges
    for src, _, data in G.in_edges(node_id, data=True):
        src_label = G.nodes[src].get("label", src)
        results.append({
            "subject":  src_label,
            "relation": data.get("relation", "related_to"),
            "object":   entity,
            "weight":   data.get("weight", 1.0),
            "dir":      "in",
        })

    # Depth 2 — neighbours of neighbours
    if depth >= 2:
        neighbours = [r["object"].lower().replace(" ", "_")
                      for r in results if r["dir"] == "out"]
        for nb in neighbours[:3]:  # cap at 3 to avoid explosion
            for _, dst, data in G.out_edges(nb, data=True):
                if dst != node_id:
                    dst_label = G.nodes[dst].get("label", dst)
                    nb_label  = G.nodes[nb].get("label", nb)
                    results.append({
                        "subject":  nb_label,
                        "relation": data.get("relation", "related_to"),
                        "object":   dst_label,
                        "weight":   data.get("weight", 1.0),
                        "dir":      "out2",
                    })

    results.sort(key=lambda x: x["weight"], reverse=True)
    return results


def query_graph(subject: Optional[str] = None,
                relation: Optional[str] = None,
                obj: Optional[str] = None) -> List[Dict]:
    """
    Flexible graph query — any combination of subject/relation/object.
    Pass None to match anything.
    """
    G       = _get_graph()
    results = []

    for u, v, data in G.edges(data=True):
        r = data.get("relation", "")
        match_subject  = (subject  is None) or (subject.lower().replace(" ", "_")  == u)
        match_relation = (relation is None) or (relation.lower() == r.lower())
        match_object   = (obj      is None) or (obj.lower().replace(" ", "_")      == v)

        if match_subject and match_relation and match_object:
            results.append({
                "subject":  G.nodes[u].get("label", u),
                "relation": r,
                "object":   G.nodes[v].get("label", v),
                "weight":   data.get("weight", 1.0),
            })

    results.sort(key=lambda x: x["weight"], reverse=True)
    return results


def build_graph_context(user_input: str,
                        user_name: str = "User") -> str:
    """
    Given user input, find relevant graph facts and
    return as a natural language context string.
    """
    G = _get_graph()
    if G.number_of_nodes() == 0:
        return ""

    words   = [w.lower().strip(".,?!") for w in user_input.split() if len(w) > 3]
    hits: List[Dict] = []

    for word in words:
        node_id = word.replace(" ", "_")
        if G.has_node(node_id):
            rels = get_relations(word, depth=1)
            hits.extend(rels[:3])

    # Always include user relations
    user_rels = get_relations(user_name, depth=1)
    hits.extend(user_rels[:4])

    if not hits:
        return ""

    # Deduplicate
    seen    = set()
    unique  = []
    for h in hits:
        key = f"{h['subject']}_{h['relation']}_{h['object']}"
        if key not in seen:
            seen.add(key)
            unique.append(h)

    lines = [f"• {h['subject']} {h['relation'].replace('_', ' ')} {h['object']}"
             for h in unique[:8]]

    return "Knowledge graph context:\n" + "\n".join(lines)


def get_stats() -> Dict:
    G = _get_graph()
    relation_counts: Dict[str, int] = {}
    for _, _, data in G.edges(data=True):
        r = data.get("relation", "related_to")
        relation_counts[r] = relation_counts.get(r, 0) + 1

    degrees: Dict[str, int] = dict(G.degree())
    top_nodes = sorted(
        [{"node": n, "degree": degrees[n]} for n in G.nodes],
        key=lambda x: x["degree"],
        reverse=True
    )[:5]

    return {
        "nodes":      G.number_of_nodes(),
        "edges":      G.number_of_edges(),
        "relations":  relation_counts,
        "top_nodes":  top_nodes,
}