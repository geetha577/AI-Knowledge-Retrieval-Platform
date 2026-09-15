"""
response_generation_agent.py
Milestone 2 - Multi-Agent Architecture: Response Generation Agent

Wraps the Milestone 1 ResponseGenerator to produce strictly grounded answers
from retrieved knowledge-base context, preventing hallucinations.
Handles factual, procedural, comparative, ambiguous, and no-result queries.
"""

import re
from typing import Dict, Any, List, Optional
from .generator import ResponseGenerator, REJECTION_MESSAGE


CLARIFICATION_MESSAGE = (
    "Your query appears ambiguous or underspecified. Could you please specify which topic, "
    "document, or concept you would like to know about?"
)


class ResponseGenerationAgent:
    """
    Response Generation Agent responsible for synthesizing grounded answers
    using ONLY the context retrieved by the Retrieval Agent.
    Strictly prevents hallucination and handles confidence attribution.
    """

    def __init__(self, generator: ResponseGenerator):
        """
        Initializes the Response Generation Agent with the existing M1 ResponseGenerator.
        """
        self.generator = generator

    def generate(
        self,
        query: str,
        query_type: str,
        retrieval_output: Dict[str, Any],
        route: str = "retrieval",
    ) -> Dict[str, Any]:
        """
        Generates a grounded response based on retrieval output and query route.

        Parameters:
            query: User's original query.
            query_type: Classified query type ('factual', 'procedural', 'comparative', 'ambiguous').
            retrieval_output: Structured dictionary from RetrievalAgent.
            route: 'retrieval' or 'clarification'.

        Returns:
            {
                "answer": str,
                "sources": List[dict],
                "confidence": str ("High", "Medium", "Low", "None"),
                "status": str ("success", "no_results", "clarification_needed"),
                "debug_details": dict,
            }
        """
        print(f"\n[RESPONSE AGENT] Generating response for query_type='{query_type}', route='{route}'")

        # Case 1: Ambiguous queries routed for clarification
        if route == "clarification" or query_type == "ambiguous":
            print("[RESPONSE AGENT] Handling ambiguous query via clarification guidance.")
            return {
                "answer": CLARIFICATION_MESSAGE,
                "sources": [],
                "confidence": "None",
                "status": "clarification_needed",
                "debug_details": {
                    "agent": "ResponseGenerationAgent",
                    "route": "clarification",
                    "reason": "Query was classified as ambiguous; clarification required.",
                },
            }

        # Case 2: Retrieval returned no results or was filtered out
        retrieval_status = retrieval_output.get("status")
        results = retrieval_output.get("results", [])

        if retrieval_status == "no_results" or not results:
            print("[RESPONSE AGENT] No relevant context available. Generating grounded rejection.")
            return {
                "answer": REJECTION_MESSAGE,
                "sources": [],
                "confidence": "None",
                "status": "no_results",
                "debug_details": {
                    "agent": "ResponseGenerationAgent",
                    "route": "retrieval",
                    "reason": "No retrieved chunks met the similarity threshold.",
                },
            }

        # Validate groundedness: prevent false positives / noise from massive indices
        query_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", query.lower()))
        stopwords = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "does", "tell", "about", "this", "that", "these", "those", "have", "were",
            "from", "with", "into", "their", "there", "make", "find", "give", "help"
        }
        content_words = {w for w in query_words if w not in stopwords}
        retrieval_conf = retrieval_output.get("retrieval_confidence", 0.0)

        if content_words and retrieval_conf < 0.40:
            has_keyword_match = False
            for r in results:
                chunk_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", r.get("content", "").lower()))
                if content_words & chunk_words:
                    has_keyword_match = True
                    break
            if not has_keyword_match:
                print("[RESPONSE AGENT] Retrieved context lacks supporting terms and similarity is low. Rejecting to prevent hallucination.")
                return {
                    "answer": REJECTION_MESSAGE,
                    "sources": [],
                    "confidence": "None",
                    "status": "no_results",
                    "debug_details": {
                        "agent": "ResponseGenerationAgent",
                        "route": "retrieval",
                        "reason": "Insufficient grounding: retrieved chunks lack query keywords and score is below grounding threshold.",
                    },
                }

        # Case 3: Grounded synthesis using retrieved chunks
        raw_retrieval_data = retrieval_output.get("raw_retrieval_data")
        if not raw_retrieval_data:
            # Fallback if raw_retrieval_data is absent: construct from results
            raw_retrieval_data = {
                "relevant_results": [],
                "confidence": retrieval_output.get("confidence_label", "Medium"),
                "top_score": retrieval_output.get("retrieval_confidence", 0.5),
            }

        query_response = self.generator.generate_response(query, raw_retrieval_data)

        # Build clean source attribution list
        sources: List[Dict[str, Any]] = []
        for s in query_response.sources:
            sources.append({
                "source_id": s.get("source_id", ""),
                "document_name": s.get("document_name", ""),
                "document_type": s.get("document_type", ""),
                "page_number": s.get("page_number"),
                "row_number": s.get("row_number"),
                "similarity_score": s.get("similarity_score", 0.0),
                "relevance": s.get("relevance", "Medium"),
                "text_snippet": s.get("text_snippet", ""),
                "full_text": s.get("full_text", ""),
            })

        print(f"[RESPONSE AGENT] Successfully generated response (Confidence: {query_response.confidence})")

        return {
            "answer": query_response.answer,
            "sources": sources,
            "confidence": query_response.confidence,
            "status": "success",
            "debug_details": query_response.debug_details,
        }
