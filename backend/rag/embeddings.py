# rag/embeddings.py — Sentence transformer embeddings
import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim, fast, good quality
    return _model


def embed(text: str) -> np.ndarray:
    """Embed a single string. Returns normalized 384-dim vector."""
    model = _get_model()
    vec = model.encode([text], normalize_embeddings=True)
    return vec.astype(np.float32)


def embed_batch(texts: list[str]) -> np.ndarray:
    """Embed a list of strings. Returns (N, 384) array."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.astype(np.float32)
