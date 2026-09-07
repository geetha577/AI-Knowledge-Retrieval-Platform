"""
retriever.py
Dedicated semantic retrieval module that orchestrates query embedding,
nearest-neighbor lookup via FAISS, relevance scoring, and threshold filtering.
"""

import re
from typing import List, Dict, Any, Tuple
import numpy as np
from .models import DocumentChunk, RetrievalResult
from .embeddings import EmbeddingEngine
from .vector_store import VectorStore




class KnowledgeRetriever:
    """
    Performs semantic retrieval over indexed document chunks with configurable
    similarity thresholding and qualitative relevance tagging.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_engine: EmbeddingEngine,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
    ):
        self.vector_store = vector_store
        self.embedding_engine = embedding_engine
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    def calculate_relevance_label(self, score: float) -> str:
        """Categorizes raw cosine similarity score into qualitative label."""
        if score >= 0.65:
            return "High"
        elif score >= 0.45:
            return "Medium"
        else:
            return "Low"

    def retrieve(self, query: str, top_k: int = None, threshold: float = None) -> Dict[str, Any]:
        """
        Executes end-to-end semantic retrieval for a user question.

        Returns a dictionary containing:
        - "relevant_results": List of RetrievalResult above threshold
        - "all_retrieved": List of raw RetrievalResult (for explainability mode)
        - "top_score": Highest similarity score (float)
        - "confidence": Overall confidence string ("High", "Medium", "Low", "None")
        """
        k = top_k if top_k is not None else self.top_k
        min_threshold = threshold if threshold is not None else self.similarity_threshold

        print(f"\n[RETRIEVAL] ===== Starting retrieval for query: '{query}' =====")
        print(f"[RETRIEVAL] top_k={k}, threshold={min_threshold}")

        # Generate query vector
        query_vector = self.embedding_engine.generate_query_embedding(query)
        print(f"[RETRIEVAL] Query embedding shape: {query_vector.shape}, norm={float(np.linalg.norm(query_vector)):.4f}")

        # Search FAISS index with candidate oversampling to support hybrid lexical/domain reranking
        fetch_k = max(k * 4, 20)
        raw_matches: List[Tuple[DocumentChunk, float]] = self.vector_store.search(
            query_vector, top_k=fetch_k
        )
        print(f"[RETRIEVAL] FAISS returned {len(raw_matches)} raw candidate(s) (fetch_k={fetch_k}):")

        # Lexical matching & query term boost
        query_terms = [w.lower() for w in re.findall(r"\b\w{3,}\b", query.lower())]
        stopwords = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how",
                     "does", "tell", "about", "this", "that", "these", "those", "have", "were"}
        content_terms = [w for w in query_terms if w not in stopwords]

        scored_candidates = []
        for chunk, score in raw_matches:
            final_score = score
            doc_lower = chunk.document_name.lower()
            text_lower = chunk.text.lower()

            # If user query specifically mentions keywords that appear in document name or content
            for term in content_terms:
                if term in doc_lower:
                    final_score += 0.15  # Document name match boost
                if term in text_lower:
                    final_score += 0.05  # Direct term hit boost

            final_score = min(final_score, 1.0)
            scored_candidates.append((chunk, final_score, score))

        # Re-sort by adjusted score descending and truncate to top_k
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_candidates[:k]

        all_results: List[RetrievalResult] = []
        relevant_results: List[RetrievalResult] = []

        for i, (chunk, adjusted_score, raw_score) in enumerate(top_candidates):
            label = self.calculate_relevance_label(adjusted_score)
            passes = "[PASS]" if adjusted_score >= min_threshold else "[FILTERED]"
            safe_text = chunk.text[:60].strip().encode("ascii", errors="replace").decode("ascii")
            print(f"  [{i+1}] score={adjusted_score:.4f} (raw={raw_score:.4f}) {passes} | {chunk.document_name} | {safe_text!r}")
            res = RetrievalResult(chunk=chunk, similarity_score=adjusted_score, relevance=label)
            all_results.append(res)
            if adjusted_score >= min_threshold:
                relevant_results.append(res)

        print(f"[RETRIEVAL] {len(relevant_results)}/{len(top_candidates)} chunks passed threshold {min_threshold}.")

        # Determine overall confidence
        if not relevant_results:
            confidence = "None"
            top_score = 0.0
            print(f"[RETRIEVAL] Confidence: NONE -- no chunks above threshold.")

        else:
            top_score = relevant_results[0].similarity_score
            confidence = relevant_results[0].relevance
            print(f"[RETRIEVAL] Confidence: {confidence} (top score: {top_score:.4f})")

        print(f"[RETRIEVAL] ===== Done =====\n")

        return {
            "relevant_results": relevant_results,
            "all_retrieved": all_results,
            "top_score": round(top_score, 4),
            "confidence": confidence,
            "query_embedding_shape": list(query_vector.shape),
        }
