# tools/doc_ingest_tool.py — Ingest a file path as a ReAct tool
from tools.registry import tool


@tool("ingest_doc", "ingest a file into the knowledge base so ASTRA can answer questions about it")
def ingest_doc(path: str) -> str:
    try:
        from rag.ingest import ingest_file
        path = path.strip().strip("'\"")
        n = ingest_file(path)
        return f"Ingested '{path}' → {n} chunks added to knowledge base."
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Ingest error: {e}"
