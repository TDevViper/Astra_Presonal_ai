# rag/embeddings.py — BGE embeddings with cache
import os
import json
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME  = "BAAI/bge-small-en-v1.5"
CACHE_DIR   = os.path.join(os.path.dirname(__file__), "..", "memory", "embedding_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def embed(text: str) -> np.ndarray:
    key = _cache_key(text)
    cache_path = os.path.join(CACHE_DIR, f"{key}.npy")
    if os.path.exists(cache_path):
        return np.load(cache_path)
    vec = get_model().encode(text, normalize_embeddings=True)
    np.save(cache_path, vec)
    return vec

def embed_batch(texts: list[str]) -> np.ndarray:
    results = []
    to_encode = []
    indices = []
    cached = {}
    for i, text in enumerate(texts):
        key = _cache_key(text)
        cache_path = os.path.join(CACHE_DIR, f"{key}.npy")
        if os.path.exists(cache_path):
            cached[i] = np.load(cache_path)
        else:
            to_encode.append(text)
            indices.append(i)
    if to_encode:
        vecs = get_model().encode(to_encode, normalize_embeddings=True, batch_size=32)
        for j, i in enumerate(indices):
            np.save(os.path.join(CACHE_DIR, f"{_cache_key(texts[i])}.npy"), vecs[j])
            cached[i] = vecs[j]
    return np.array([cached[i] for i in range(len(texts))])
