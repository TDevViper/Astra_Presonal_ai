# rag/ingest.py — Multi-source document ingestion
import os
from rag.chunker import chunk_text, chunk_by_paragraph
from rag.embeddings import embed_batch
from rag.vector_store import add_chunks


def ingest_text(text: str, source: str = "manual", tags: list = None):
    chunks = chunk_by_paragraph(text)
    if not chunks:
        return 0
    embeddings = embed_batch(chunks)
    add_chunks(chunks, embeddings, source=source, tags=tags or [])
    return len(chunks)


def ingest_file(path: str, tags: list = None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
    elif ext in [".md", ".txt", ".py", ".js", ".ts"]:
        with open(path) as f:
            text = f.read()
    else:
        print(f"Unsupported: {ext}")
        return 0
    source = os.path.basename(path)
    return ingest_text(text, source=source, tags=tags or [ext.strip(".")])


def ingest_folder(folder: str, extensions: list = None, tags: list = None):
    extensions = extensions or [".md", ".txt", ".pdf"]  # .py excluded by default
    total = 0
    for root, _, files in os.walk(folder):
        for fname in files:
            if any(fname.endswith(ext) for ext in extensions):
                path = os.path.join(root, fname)
                try:
                    n = ingest_file(path, tags=tags)
                    print(f"  ✓ {fname} → {n} chunks")
                    total += n
                except Exception as e:
                    print(f"  ✗ {fname}: {e}")
    return total
