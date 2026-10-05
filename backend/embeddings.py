"""
embeddings.py
Generates normalized dense vector representations for text chunks and queries
using Sentence-Transformers (local model: all-MiniLM-L6-v2).
"""

from typing import List
import numpy as np


class EmbeddingEngine:
    """
    Manages loading the embedding model and computing normalized vector embeddings.
    """
    _cached_models = {}

    def __init__(self, model_name: str = None):
        # Load default model name from configuration if not supplied
        from .config import config
        self.model_name = model_name if model_name is not None else config.embedding_model
        self.dimension = 384  # Default dimension; may be updated after model load


    @property
    def model(self):
        """Lazy loader with class-level caching to speed up test and component initialization."""
        if self.model_name not in self._cached_models:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[EMBEDDING] Loading embedding model: {self.model_name}...")
                loaded_model = SentenceTransformer(self.model_name)
                # Verify dimension
                test_vec = loaded_model.encode(["test"])
                self.dimension = int(test_vec.shape[1])
                print(f"[EMBEDDING] Model loaded successfully (dimension: {self.dimension})")
                self._cached_models[self.model_name] = loaded_model
            except Exception as e:
                print(f"[EMBEDDING] Warning: Could not load SentenceTransformer ({str(e)}). Using local fallback.")
                self._cached_models[self.model_name] = "fallback"

        active_model = self._cached_models[self.model_name]
        if active_model != "fallback":
            dim_fn = getattr(active_model, "get_embedding_dimension", getattr(active_model, "get_sentence_embedding_dimension", None))
            if callable(dim_fn):
                self.dimension = dim_fn()
        return active_model



    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Converts a list of strings into an L2-normalized numpy array of shape (N, dimension)
        with float32 dtype for direct FAISS compatibility.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        # Sanitize texts (replace empty strings with single space)
        sanitized = [t.strip() if t.strip() else " " for t in texts]

        if self.model != "fallback":
            try:
                # encode returns ndarray or tensor
                embeddings = self.model.encode(
                    sanitized,
                    batch_size=32,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )
                return embeddings.astype(np.float32)
            except Exception as e:
                print(f"[EMBEDDING] Error during model encoding: {e}. Utilizing fallback hash vectors.")

        # Deterministic lightweight fallback (e.g. for offline testing / sandbox networks)
        return self._generate_fallback_embeddings(sanitized)

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Encodes a single query string into a 2D array of shape (1, dimension).
        """
        return self.generate_embeddings([query])

    def _generate_fallback_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Deterministic TF-IDF like feature hashing fallback embedding generator
        ensuring the pipeline never halts even if completely offline without model weights.
        """
        import hashlib
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for i, text in enumerate(texts):
            words = text.lower().split()
            if not words:
                continue
            for word in words:
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                idx = h % self.dimension
                vectors[i, idx] += 1.0
            norm = np.linalg.norm(vectors[i])
            if norm > 0:
                vectors[i] = vectors[i] / norm
        return vectors
