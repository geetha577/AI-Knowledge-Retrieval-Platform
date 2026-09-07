"""
vector_store.py
FAISS-based vector database with persistent disk storage, metadata tracking,
duplicate document handling, and top-k cosine similarity search.
"""

import os
import pickle
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from .models import DocumentChunk


class VectorStore:
    """
    Manages embedding storage and nearest-neighbor semantic search using FAISS.
    Persists vectors (index.faiss) and metadata (metadata.pkl) to disk.
    Also supports deleting/replacing existing documents to handle duplicate uploads cleanly.
    """

    def __init__(self, persist_dir: str = "data/vector_store", dimension: int = 384):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension

        self.index_path = self.persist_dir / "index.faiss"
        self.meta_path = self.persist_dir / "metadata.pkl"

        self.chunks: List[DocumentChunk] = []
        self.faiss_index = None
        self._faiss_available = False

        # Attempt to import faiss
        try:
            import faiss
            self.faiss = faiss
            self._faiss_available = True
        except ImportError:
            print("[INDEX] Warning: faiss-cpu not installed. Operating with numpy cosine index.")
            self.faiss = None

        self._init_or_load()

    def _init_or_load(self):
        """Loads persisted FAISS index and metadata if available, otherwise initializes fresh."""
        if self.index_path.exists() and self.meta_path.exists():
            try:
                print(f"[INDEX] Loading existing vector store from {self.persist_dir}...")
                with open(self.meta_path, "rb") as f:
                    loaded_chunks = pickle.load(f)

                if self._faiss_available:
                    loaded_index = self.faiss.read_index(str(self.index_path))
                    # Validate dimension matches
                    if loaded_index.d != self.dimension:
                        print(f"[INDEX] Dimension mismatch (persisted: {loaded_index.d}, expected: {self.dimension}). Re-initializing index.")
                        self._create_empty_index()
                        return

                    self.faiss_index = loaded_index
                    self.chunks = loaded_chunks
                    print(f"[INDEX] Loaded {self.faiss_index.ntotal} vectors and {len(self.chunks)} chunk metadata records.")
                else:
                    self.vectors = np.load(str(self.persist_dir / "vectors.npy"))
                    self.chunks = loaded_chunks
                return
            except Exception as e:
                print(f"[INDEX] Error loading existing index ({e}). Creating a fresh index.")

        self._create_empty_index()

    def _create_empty_index(self):
        """Creates a fresh empty FAISS index."""
        self.chunks = []
        if self._faiss_available:
            # IndexFlatIP calculates inner product. Because embeddings are L2 normalized,
            # inner product is identical to cosine similarity.
            self.faiss_index = self.faiss.IndexFlatIP(self.dimension)
        else:
            self.vectors = np.empty((0, self.dimension), dtype=np.float32)

    def delete_document(self, document_name: str) -> int:
        """
        Removes all chunks for a specific document name.
        Rebuilds the index with the remaining documents.
        Returns the number of removed chunks.
        """
        indices_to_keep = [i for i, c in enumerate(self.chunks) if c.document_name != document_name]
        removed_count = len(self.chunks) - len(indices_to_keep)

        if removed_count == 0:
            return 0

        print(f"[INDEX] Removing existing {removed_count} chunk(s) for '{document_name}' to prevent duplicate indexing...")

        kept_chunks = [self.chunks[i] for i in indices_to_keep]

        # Reconstruct vector index with remaining items
        if self._faiss_available and self.faiss_index is not None:
            new_index = self.faiss.IndexFlatIP(self.dimension)
            if indices_to_keep:
                # Reconstruct vectors from the existing index
                reconstructed_vectors = np.empty((len(indices_to_keep), self.dimension), dtype=np.float32)
                for new_pos, orig_idx in enumerate(indices_to_keep):
                    reconstructed_vectors[new_pos] = self.faiss_index.reconstruct(orig_idx)
                new_index.add(reconstructed_vectors)
            self.faiss_index = new_index
        elif hasattr(self, "vectors"):
            self.vectors = self.vectors[indices_to_keep] if indices_to_keep else np.empty((0, self.dimension), dtype=np.float32)

        self.chunks = kept_chunks
        self.save()
        return removed_count

    def add_documents(self, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """
        Appends new document chunks and their embeddings to the index and persists to disk.
        If chunks belong to a single document that was previously uploaded, existing
        chunks for that document are removed first to ensure no duplicates.
        """
        if len(chunks) == 0:
            return

        if embeddings.shape[0] != len(chunks):
            raise ValueError(f"Mismatch: {len(chunks)} chunks but {embeddings.shape[0]} embeddings.")

        # Ensure float32
        embeddings = embeddings.astype(np.float32)

        # Check for duplicate document update (if all incoming chunks belong to one document)
        doc_names = set(c.document_name for c in chunks)
        if len(doc_names) == 1:
            doc_name = next(iter(doc_names))
            self.delete_document(doc_name)

        if self._faiss_available:
            self.faiss_index.add(embeddings)
        else:
            self.vectors = np.vstack([self.vectors, embeddings]) if self.vectors.shape[0] > 0 else embeddings

        self.chunks.extend(chunks)
        print(f"[INDEX] Added {len(chunks)} vectors. Total in store: {self.total_chunks}")
        self.save()

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """
        Executes top-k nearest neighbor similarity search.
        Returns a list of (DocumentChunk, similarity_score) sorted descending by similarity.
        """
        if self.total_chunks == 0:
            return []

        top_k = min(top_k, self.total_chunks)
        query_embedding = query_embedding.astype(np.float32)

        if self._faiss_available:
            # distances shape: (1, top_k), indices shape: (1, top_k)
            distances, indices = self.faiss_index.search(query_embedding, top_k)
            scores = distances[0]
            idxs = indices[0]
        else:
            # Numpy cosine similarity fallback
            scores_all = np.dot(self.vectors, query_embedding[0])
            idxs = np.argsort(scores_all)[::-1][:top_k]
            scores = scores_all[idxs]

        results = []
        for idx, score in zip(idxs, scores):
            if idx >= 0 and idx < len(self.chunks):
                # Cosine similarity is in [-1.0, 1.0], clip to [0.0, 1.0] for clarity
                normalized_score = float(np.clip(score, 0.0, 1.0))
                results.append((self.chunks[idx], normalized_score))

        return results

    def save(self):
        """Persists the FAISS index and metadata to disk."""
        try:
            with open(self.meta_path, "wb") as f:
                pickle.dump(self.chunks, f)

            if self._faiss_available and self.faiss_index is not None:
                self.faiss.write_index(self.faiss_index, str(self.index_path))
            elif hasattr(self, "vectors"):
                np.save(str(self.persist_dir / "vectors.npy"), self.vectors)

            print(f"[INDEX] Successfully persisted vector store ({self.total_chunks} chunks).")
        except Exception as e:
            print(f"[INDEX] Error persisting vector store: {e}")

    def clear(self):
        """Clears all vectors and metadata, resetting the index."""
        self._create_empty_index()
        if self.index_path.exists():
            self.index_path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()
        if (self.persist_dir / "vectors.npy").exists():
            (self.persist_dir / "vectors.npy").unlink()
        print("[INDEX] Vector store cleared successfully.")

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    def get_indexed_documents(self) -> List[Dict[str, Any]]:
        """Returns summarized metadata for all indexed documents."""
        docs = {}
        for chunk in self.chunks:
            name = chunk.document_name
            if name not in docs:
                docs[name] = {
                    "document_name": name,
                    "document_type": chunk.document_type,
                    "chunk_count": 0,
                    "pages": set(),
                }
            docs[name]["chunk_count"] += 1
            if chunk.page_number:
                docs[name]["pages"].add(chunk.page_number)

        result = []
        for doc in docs.values():
            result.append({
                "document_name": doc["document_name"],
                "document_type": doc["document_type"],
                "chunk_count": doc["chunk_count"],
                "pages": sorted(list(doc["pages"])) if doc["pages"] else None,
            })
        return result
