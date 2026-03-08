# rag/chunker.py — Semantic overlap chunking
import re

def chunk_text(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:
            chunks.append(chunk)
        start += size - overlap
    return chunks

def chunk_by_paragraph(text: str, max_size: int = 600) -> list[str]:
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
    chunks = []
    current = ""
    for para in paragraphs:
        if len((current + " " + para).split()) <= max_size:
            current = (current + " " + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks if chunks else chunk_text(text)
