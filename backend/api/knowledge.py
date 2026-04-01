import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from knowledge.graph import (
    get_relations,
    query_graph,
    get_stats,
    add_entity,
    add_relation,
    build_graph_context,
)
from knowledge.entity_extractor import extract_and_store

logger = logging.getLogger(__name__)
knowledge_bp = APIRouter()


@knowledge_bp.get("/knowledge/stats")
def stats(request: Request):
    try:
        return JSONResponse(content=get_stats())
    except Exception as e:
        logger.error("knowledge stats error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@knowledge_bp.get("/knowledge/entity/<n>")
def entity(n):
    try:
        depth = int(request.query_params.get("depth", 1))
        return JSONResponse(content=get_relations(n, depth=depth))
    except Exception as e:
        logger.error("knowledge entity error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@knowledge_bp.get("/knowledge/query")
def query(request: Request):
    try:
        subject = request.query_params.get("subject")
        relation = request.query_params.get("relation")
        obj = request.query_params.get("object")
        return JSONResponse(content=query_graph(subject, relation, obj))
    except Exception as e:
        logger.error("knowledge query error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@knowledge_bp.post("/knowledge/extract")
def extract(request: Request):
    try:
        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        text = data.get("text", "")
        from memory.memory_engine import load_memory

        mem = load_memory()
        user_name = data.get(
            "user_name", mem.get("preferences", {}).get("name", "User")
        )
        use_llm = data.get("use_llm", False)
        if not text:
            return JSONResponse(content={"error": "No text provided"}, status_code=400)
        count = extract_and_store(text, user_name, use_llm=use_llm)
        return JSONResponse(content={"triples_stored": count})
    except Exception as e:
        logger.error("knowledge extract error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@knowledge_bp.post("/knowledge/add")
def add(request: Request):
    try:
        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        subject = data.get("subject")
        relation = data.get("relation")
        obj = data.get("object")
        if not all([subject, relation, obj]):
            return JSONResponse(content={"error": "subject, relation, object required"}, status_code=400)
        add_entity(subject)
        add_entity(obj)
        add_relation(subject, relation, obj)
        return JSONResponse(content={"ok": True, "triple": f"{subject} → {relation} → {obj}"})
    except Exception as e:
        logger.error("knowledge add error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500