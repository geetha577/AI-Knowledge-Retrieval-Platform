"""
orchestrator.py
Milestone 2 - Multi-Agent Architecture: Multi-Agent Orchestrator

Sequentially coordinates:
  User Query
      ↓
  Query Understanding Agent
      ↓
  Retrieval Agent
      ↓
  Response Generation Agent
      ↓
  Final Structured Response

Maintains explainable execution traces, handles exceptions at each stage,
and produces standardized multi-agent responses for the UI and API.
"""

import time
from typing import Dict, Any, List, Optional
from .query_understanding_agent import QueryUnderstandingAgent
from .retrieval_agent import RetrievalAgent
from .response_generation_agent import ResponseGenerationAgent


class MultiAgentOrchestrator:
    """
    Coordinates the sequential multi-agent pipeline for query resolution.
    """

    def __init__(
        self,
        query_understanding_agent: QueryUnderstandingAgent,
        retrieval_agent: RetrievalAgent,
        response_generation_agent: ResponseGenerationAgent,
    ):
        self.query_understanding_agent = query_understanding_agent
        self.retrieval_agent = retrieval_agent
        self.response_generation_agent = response_generation_agent

    def process_query(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end multi-agent pipeline for an incoming user query.

        Returns a comprehensive dictionary containing:
        - query: str
        - query_type: str ('factual', 'procedural', 'comparative', 'ambiguous')
        - classification_confidence: float
        - route: str ('retrieval', 'clarification')
        - answer: str
        - confidence: str ('High', 'Medium', 'Low', 'None')
        - sources: list of dicts
        - status: str ('success', 'no_results', 'clarification_needed', 'error')
        - pipeline_stages: list of execution trace records
        - debug_details: detailed explainability dictionary
        """
        start_time = time.time()
        pipeline_stages: List[Dict[str, Any]] = []

        print(f"\n{'='*60}")
        print(f"[ORCHESTRATOR] Starting Multi-Agent Pipeline for Query: '{query}'")
        print(f"{'='*60}")

        # -------------------------------------------------------------
        # Stage 1: Query Understanding Agent
        # -------------------------------------------------------------
        stage1_start = time.time()
        try:
            understanding = self.query_understanding_agent.analyze(query)
            stage1_duration = round(time.time() - stage1_start, 4)
            pipeline_stages.append({
                "stage": "Query Understanding",
                "agent": "QueryUnderstandingAgent",
                "status": "completed",
                "duration_sec": stage1_duration,
                "output": {
                    "query_type": understanding.get("query_type"),
                    "confidence": understanding.get("classification_confidence"),
                    "route": understanding.get("route"),
                    "reasoning": understanding.get("reasoning"),
                },
            })
            print(f"[STAGE 1 DONE] Type: {understanding.get('query_type')}, Route: {understanding.get('route')}")
        except Exception as e:
            print(f"[STAGE 1 FAILED] Query Understanding Agent error: {str(e)}")
            understanding = {
                "query": query,
                "query_type": "factual",
                "classification_confidence": 0.5,
                "route": "retrieval",
                "reasoning": f"Fallback due to exception: {str(e)}",
            }
            pipeline_stages.append({
                "stage": "Query Understanding",
                "agent": "QueryUnderstandingAgent",
                "status": "fallback",
                "error": str(e),
            })

        query_type = understanding.get("query_type", "factual")
        route = understanding.get("route", "retrieval")
        classification_confidence = understanding.get("classification_confidence", 0.85)

        # -------------------------------------------------------------
        # Stage 2: Retrieval Agent
        # -------------------------------------------------------------
        retrieval_output: Dict[str, Any] = {}
        stage2_start = time.time()

        if route == "clarification":
            print("[STAGE 2 SKIPPED] Ambiguous query routed directly to clarification guidance.")
            retrieval_output = {
                "query": query,
                "query_type": query_type,
                "results": [],
                "retrieval_confidence": 0.0,
                "confidence_label": "None",
                "status": "skipped_ambiguous",
            }
            pipeline_stages.append({
                "stage": "Semantic Retrieval",
                "agent": "RetrievalAgent",
                "status": "skipped",
                "reason": "Query routed for clarification; vector search bypassed.",
            })
        else:
            try:
                retrieval_output = self.retrieval_agent.retrieve(
                    query=query,
                    query_type=query_type,
                    top_k=top_k,
                    threshold=threshold,
                )
                stage2_duration = round(time.time() - stage2_start, 4)
                pipeline_stages.append({
                    "stage": "Semantic Retrieval",
                    "agent": "RetrievalAgent",
                    "status": "completed",
                    "duration_sec": stage2_duration,
                    "output": {
                        "status": retrieval_output.get("status"),
                        "chunks_retrieved": len(retrieval_output.get("results", [])),
                        "retrieval_confidence": retrieval_output.get("retrieval_confidence"),
                        "confidence_label": retrieval_output.get("confidence_label"),
                    },
                })
                print(f"[STAGE 2 DONE] Chunks: {len(retrieval_output.get('results', []))}, Status: {retrieval_output.get('status')}")
            except Exception as e:
                print(f"[STAGE 2 FAILED] Retrieval Agent error: {str(e)}")
                retrieval_output = {
                    "query": query,
                    "query_type": query_type,
                    "results": [],
                    "retrieval_confidence": 0.0,
                    "confidence_label": "None",
                    "status": "no_results",
                    "error": str(e),
                }
                pipeline_stages.append({
                    "stage": "Semantic Retrieval",
                    "agent": "RetrievalAgent",
                    "status": "error",
                    "error": str(e),
                })

        # -------------------------------------------------------------
        # Stage 3: Response Generation Agent
        # -------------------------------------------------------------
        stage3_start = time.time()
        try:
            response_output = self.response_generation_agent.generate(
                query=query,
                query_type=query_type,
                retrieval_output=retrieval_output,
                route=route,
            )
            stage3_duration = round(time.time() - stage3_start, 4)
            pipeline_stages.append({
                "stage": "Response Generation",
                "agent": "ResponseGenerationAgent",
                "status": "completed",
                "duration_sec": stage3_duration,
                "output": {
                    "status": response_output.get("status"),
                    "confidence": response_output.get("confidence"),
                    "sources_count": len(response_output.get("sources", [])),
                },
            })
            print(f"[STAGE 3 DONE] Final Confidence: {response_output.get('confidence')}")
        except Exception as e:
            print(f"[STAGE 3 FAILED] Response Generation Agent error: {str(e)}")
            response_output = {
                "answer": f"An error occurred while generating the response: {str(e)}",
                "sources": [],
                "confidence": "None",
                "status": "error",
                "debug_details": {"error": str(e)},
            }
            pipeline_stages.append({
                "stage": "Response Generation",
                "agent": "ResponseGenerationAgent",
                "status": "error",
                "error": str(e),
            })

        total_duration = round(time.time() - start_time, 4)
        print(f"[ORCHESTRATOR] Multi-Agent Pipeline completed in {total_duration}s")
        print(f"{'='*60}\n")

        # Compile comprehensive response
        debug_payload = {
            "query": query,
            "query_type": query_type,
            "classification_confidence": classification_confidence,
            "route": route,
            "total_duration_sec": total_duration,
            "pipeline_stages": pipeline_stages,
            "retrieval_status": retrieval_output.get("status"),
            "top_similarity_score": retrieval_output.get("retrieval_confidence", 0.0),
            "generation_debug": response_output.get("debug_details", {}),
            "retrieved_results": retrieval_output.get("results", []),
        }

        return {
            "query": query,
            "query_type": query_type,
            "classification_confidence": classification_confidence,
            "route": route,
            "answer": response_output.get("answer", ""),
            "confidence": response_output.get("confidence", "None"),
            "sources": response_output.get("sources", []),
            "status": response_output.get("status", "success"),
            "pipeline_stages": pipeline_stages,
            "debug_details": debug_payload,
        }
