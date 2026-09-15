"""
retrieval_agent.py
Milestone 2 - Multi-Agent Architecture: Retrieval Agent

Builds on top of the Milestone 1 KnowledgeRetriever without duplicating
embedding or vector-store functionality. Performs semantic retrieval,
ranking, confidence thresholding, and metadata preservation.
"""

from typing import Dict, Any, List, Optional
from .retriever import KnowledgeRetriever


class RetrievalAgent:
    """
    Retrieval Agent responsible for executing vector similarity search
    over the indexed FAISS knowledge base using contextual classification
    parameters from the Query Understanding Agent.
    """

    def __init__(self, retriever: KnowledgeRetriever):
        """
        Initializes the Retrieval Agent with the existing M1 KnowledgeRetriever.
        """
        self.retriever = retriever

    def retrieve(
        self,
        query: str,
        query_type: str = "factual",
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes semantic retrieval for the query, preserving all source metadata
        and returning standardized structured data for downstream agents.

        Returns:
            {
                "query": str,
                "query_type": str,
                "results": [
                    {
                        "content": str,
                        "document": str,
                        "page": Optional[int],
                        "section": str,
                        "chunk_id": str,
                        "score": float,
                        "relevance": str,
                    }
                ],
                "retrieval_confidence": float,
                "confidence_label": str,
                "status": "success" | "no_results",
                "raw_retrieval_data": dict,
            }
        """
        print(f"\n[RETRIEVAL AGENT] Query: '{query}' (Type: {query_type})")

        # Query existing M1 retriever
        raw_data = self.retriever.retrieve(query=query, top_k=top_k, threshold=threshold)

        relevant_results = raw_data.get("relevant_results", [])
        top_score = raw_data.get("top_score", 0.0)
        confidence_label = raw_data.get("confidence", "None")

        formatted_results: List[Dict[str, Any]] = []
        for res in relevant_results:
            chunk = res.chunk
            section_name = (
                chunk.extra_metadata.get("section")
                or f"page_{chunk.page_number}"
                if chunk.page_number is not None
                else f"chunk_{chunk.chunk_id}"
            )

            formatted_results.append({
                "content": chunk.text,
                "document": chunk.document_name,
                "page": chunk.page_number,
                "row_number": chunk.row_number,
                "section": section_name,
                "chunk_id": chunk.chunk_id,
                "score": round(res.similarity_score, 4),
                "relevance": res.relevance,
                "source_id": chunk.source_id,
            })

        if not formatted_results:
            print(f"[RETRIEVAL AGENT] No relevant chunks found above threshold for query: '{query}'")
            return {
                "query": query,
                "query_type": query_type,
                "results": [],
                "retrieval_confidence": round(top_score, 4),
                "confidence_label": "None",
                "status": "no_results",
                "raw_retrieval_data": raw_data,
            }

        print(f"[RETRIEVAL AGENT] Retrieved {len(formatted_results)} relevant chunks (Top Score: {top_score:.4f})")
        return {
            "query": query,
            "query_type": query_type,
            "results": formatted_results,
            "retrieval_confidence": round(top_score, 4),
            "confidence_label": confidence_label,
            "status": "success",
            "raw_retrieval_data": raw_data,
        }
