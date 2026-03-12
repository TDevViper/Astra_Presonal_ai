from flask import Blueprint, request, jsonify
from knowledge.graph import (
    get_relations, query_graph, get_stats,
    add_entity, add_relation, build_graph_context
)
from knowledge.entity_extractor import extract_and_store

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.route("/knowledge/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())


@knowledge_bp.route("/knowledge/entity/<name>", methods=["GET"])
def entity(n):
    depth = int(request.args.get("depth", 1))
    return jsonify(get_relations(n, depth=depth))


@knowledge_bp.route("/knowledge/query", methods=["GET"])
def query():
    subject  = request.args.get("subject")
    relation = request.args.get("relation")
    obj      = request.args.get("object")
    return jsonify(query_graph(subject, relation, obj))


@knowledge_bp.route("/knowledge/extract", methods=["POST"])
def extract():
    data      = request.get_json() or {}
    text      = data.get("text", "")
    user_name = data.get("user_name", "Arnav")
    use_llm   = data.get("use_llm", False)
    if not text:
        return jsonify({"error": "No text provided"}), 400
    count = extract_and_store(text, user_name, use_llm=use_llm)
    return jsonify({"triples_stored": count})


@knowledge_bp.route("/knowledge/add", methods=["POST"])
def add():
    data     = request.get_json() or {}
    subject  = data.get("subject")
    relation = data.get("relation")
    obj      = data.get("object")
    if not all([subject, relation, obj]):
        return jsonify({"error": "subject, relation, object required"}), 400
    add_entity(subject)
    add_entity(obj)
    add_relation(subject, relation, obj)
    return jsonify({"ok": True,
                    "triple": f"{subject} → {relation} → {obj}"})
