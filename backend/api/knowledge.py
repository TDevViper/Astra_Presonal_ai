import logging
from flask import Blueprint, request, jsonify
from knowledge.graph import (
    get_relations, query_graph, get_stats,
    add_entity, add_relation, build_graph_context
)
from knowledge.entity_extractor import extract_and_store

logger       = logging.getLogger(__name__)
knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.route("/knowledge/stats", methods=["GET"])
def stats():
    try:
        return jsonify(get_stats())
    except Exception as e:
        logger.error("knowledge stats error: %s", e)
        return jsonify({"error": str(e)}), 500


@knowledge_bp.route("/knowledge/entity/<n>", methods=["GET"])
def entity(n):
    try:
        depth = int(request.args.get("depth", 1))
        return jsonify(get_relations(n, depth=depth))
    except Exception as e:
        logger.error("knowledge entity error: %s", e)
        return jsonify({"error": str(e)}), 500


@knowledge_bp.route("/knowledge/query", methods=["GET"])
def query():
    try:
        subject  = request.args.get("subject")
        relation = request.args.get("relation")
        obj      = request.args.get("object")
        return jsonify(query_graph(subject, relation, obj))
    except Exception as e:
        logger.error("knowledge query error: %s", e)
        return jsonify({"error": str(e)}), 500


@knowledge_bp.route("/knowledge/extract", methods=["POST"])
def extract():
    try:
        data      = request.get_json() or {}
        text      = data.get("text", "")
        from memory.memory_engine import load_memory
        mem       = load_memory()
        user_name = data.get("user_name", mem.get("preferences", {}).get("name", "User"))
        use_llm   = data.get("use_llm", False)
        if not text:
            return jsonify({"error": "No text provided"}), 400
        count = extract_and_store(text, user_name, use_llm=use_llm)
        return jsonify({"triples_stored": count})
    except Exception as e:
        logger.error("knowledge extract error: %s", e)
        return jsonify({"error": str(e)}), 500


@knowledge_bp.route("/knowledge/add", methods=["POST"])
def add():
    try:
        data     = request.get_json() or {}
        subject  = data.get("subject")
        relation = data.get("relation")
        obj      = data.get("object")
        if not all([subject, relation, obj]):
            return jsonify({"error": "subject, relation, object required"}), 400
        add_entity(subject)
        add_entity(obj)
        add_relation(subject, relation, obj)
        return jsonify({"ok": True, "triple": f"{subject} → {relation} → {obj}"})
    except Exception as e:
        logger.error("knowledge add error: %s", e)
        return jsonify({"error": str(e)}), 500
