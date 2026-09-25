"""
orchestrator.py
Milestones 2 & 3 - Multi-Agent Architecture: Multi-Agent Orchestrator

Sequentially coordinates:
  User Query
      ↓
  Query Understanding Agent (Ambiguity & Intent Classification)
      ↓
  Is Query Ambiguous?
  ├── YES → Clarification Agent → Session Created → User Clarification Prompt
  │         (Multi-turn resolution merges clarification + original query)
  └── NO  → Retrieval Agent → Response Generation Agent → Final Grounded Response

Maintains explainable execution traces, handles multi-turn clarification state,
and produces standardized multi-agent responses for the UI and API.
"""

import time
from typing import Dict, Any, List, Optional
from .query_understanding_agent import QueryUnderstandingAgent
from .retrieval_agent import RetrievalAgent
from .response_generation_agent import ResponseGenerationAgent
from .clarification_agent import ClarificationAgent
from .conversation_manager import ConversationManager


class MultiAgentOrchestrator:
    """
    Coordinates the sequential multi-agent pipeline for query resolution,
    including ambiguity detection, clarification dialogues, and multi-turn resolution.
    """

    def __init__(
        self,
        query_understanding_agent: QueryUnderstandingAgent,
        retrieval_agent: RetrievalAgent,
        response_generation_agent: ResponseGenerationAgent,
        clarification_agent: Optional[ClarificationAgent] = None,
        conversation_manager: Optional[ConversationManager] = None,
    ):
        self.query_understanding_agent = query_understanding_agent
        self.retrieval_agent = retrieval_agent
        self.response_generation_agent = response_generation_agent
        self.clarification_agent = clarification_agent or ClarificationAgent()
        self.conversation_manager = conversation_manager or ConversationManager()

    def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        is_clarification: bool = False,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        available_docs: Optional[List[str]] = None,
        conv_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end multi-agent pipeline for an incoming user query
        or clarification response.

        Parameters:
            query: The user's query or clarification response.
            session_id: Optional active clarification session ID.
            is_clarification: Flag indicating if this is a clarification response.
            top_k: Optional top_k override for retrieval.
            threshold: Optional similarity threshold override.
            available_docs: Optional list of indexed document names.

        Returns:
            Dictionary matching the API contract:
            - For normal / resolved query: status="answered" (or "success")
            - For ambiguous query: status="clarification_required" (or "clarification_needed")
        """
        start_time = time.time()
        pipeline_stages: List[Dict[str, Any]] = []

        print(f"\n{'='*60}")
        print(f"[ORCHESTRATOR] Processing Query: '{query}' | Session: {session_id}")
        print(f"{'='*60}")

        original_query = query
        resolved_query = None
        effective_query = query
        active_session = None

        # -------------------------------------------------------------
        # Step 0: Check if this is a clarification response to an existing session
        # -------------------------------------------------------------
        if session_id:
            active_session = self.conversation_manager.get_session(session_id)

        if active_session:
            original_query = active_session["original_query"]
            clarification_count = active_session["clarification_count"]

            # Check if maximum clarification turns exceeded
            if clarification_count >= self.conversation_manager.max_clarification_turns:
                print(f"[ORCHESTRATOR] Maximum clarification turns ({self.conversation_manager.max_clarification_turns}) reached.")
                self.conversation_manager.clear_session(session_id)
                pipeline_stages.append({
                    "stage": "Clarification Limit",
                    "agent": "ConversationManager",
                    "status": "limit_reached",
                    "reason": "Exceeded maximum allowed clarification attempts.",
                })
                return {
                    "query": query,
                    "original_query": original_query,
                    "resolved_query": query,
                    "query_type": "ambiguous",
                    "classification_confidence": 1.0,
                    "route": "clarification",
                    "answer": "I have collected your clarifications, but the query remains too broad. Please try asking a specific question mentioning the topic or document.",
                    "confidence": "None",
                    "sources": [],
                    "status": "answered",
                    "session_id": None,
                    "pipeline_stages": pipeline_stages,
                    "debug_details": {"error": "Maximum clarification turns reached."},
                }

            # Intelligently resolve query using ConversationManager
            resolved_query = self.conversation_manager.resolve_query(original_query, query)
            effective_query = resolved_query
            print(f"[ORCHESTRATOR] Resolved Query: '{effective_query}' (Original: '{original_query}' + Clarification: '{query}')")

            pipeline_stages.append({
                "stage": "Query Resolution",
                "agent": "ConversationManager",
                "status": "completed",
                "output": {
                    "original_query": original_query,
                    "clarification_response": query,
                    "resolved_query": resolved_query,
                    "turn": clarification_count,
                },
            })

        # -------------------------------------------------------------
        # Step 0b: Check conversation memory for follow-up resolution (M3.2)
        # -------------------------------------------------------------
        if conv_id and not active_session:
            memory = self.conversation_manager.get_or_create_memory(conv_id)
            conv_id = memory.conv_id
            memory_resolved = self.conversation_manager.resolve_followup_query(conv_id, effective_query)
            if memory_resolved != effective_query:
                resolved_query = memory_resolved
                effective_query = memory_resolved
                pipeline_stages.append({
                    "stage": "Conversation Memory",
                    "agent": "ConversationMemoryAgent",
                    "status": "context_resolved",
                    "output": {
                        "original_query": query,
                        "resolved_query": effective_query,
                        "conv_id": conv_id,
                    },
                })

        # -------------------------------------------------------------
        # Stage 1: Query Understanding Agent
        # -------------------------------------------------------------
        stage1_start = time.time()
        try:
            understanding = self.query_understanding_agent.analyze(effective_query)
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
                "query": effective_query,
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
        # Branch: Query is Ambiguous -> Activate Clarification Flow
        # -------------------------------------------------------------
        if route == "clarification" or query_type == "ambiguous":
            print("[ORCHESTRATOR] Ambiguous query detected. Generating clarification question...")
            clarification_data = self.clarification_agent.generate_clarification(
                query=effective_query,
                classification_confidence=classification_confidence,
                available_docs=available_docs,
            )

            clarification_question = clarification_data["clarification_question"]
            suggested_options = clarification_data.get("suggested_options", [])

            # Update or create session
            if active_session:
                self.conversation_manager.record_turn(
                    session_id=session_id,
                    user_response=query,
                    new_clarification_question=clarification_question,
                    suggested_options=suggested_options,
                )
                current_session_id = session_id
            else:
                current_session_id = self.conversation_manager.start_session(
                    original_query=query,
                    clarification_question=clarification_question,
                    suggested_options=suggested_options,
                )

            pipeline_stages.append({
                "stage": "Semantic Retrieval",
                "agent": "RetrievalAgent",
                "status": "skipped",
                "reason": "Query routed for clarification; vector search bypassed.",
            })
            pipeline_stages.append({
                "stage": "Clarification Generation",
                "agent": "ClarificationAgent",
                "status": "completed",
                "output": {
                    "clarification_question": clarification_question,
                    "reason": clarification_data.get("reason"),
                    "suggested_options": suggested_options,
                    "session_id": current_session_id,
                },
            })

            total_duration = round(time.time() - start_time, 4)
            return {
                "query": effective_query,
                "original_query": original_query,
                "resolved_query": resolved_query,
                "query_type": "ambiguous",
                "classification_confidence": classification_confidence,
                "route": "clarification",
                "status": "clarification_required",
                "clarification_question": clarification_question,
                "suggested_options": suggested_options,
                "session_id": current_session_id,
                "conv_id": conv_id,
                "answer": clarification_question,  # Preserves backward compatibility for answer field
                "confidence": "None",
                "sources": [],
                "pipeline_stages": pipeline_stages,
                "debug_details": {
                    "agent": "ClarificationAgent",
                    "route": "clarification",
                    "reason": clarification_data.get("reason"),
                    "session_id": current_session_id,
                    "duration_sec": total_duration,
                },
            }

        # If we arrived here from an active session that is now resolved, complete it
        if active_session:
            self.conversation_manager.complete_session(session_id, effective_query)

        # -------------------------------------------------------------
        # Stage 2: Retrieval Agent
        # -------------------------------------------------------------
        retrieval_output: Dict[str, Any] = {}
        stage2_start = time.time()

        try:
            retrieval_output = self.retrieval_agent.retrieve(
                query=effective_query,
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
                "query": effective_query,
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
                query=effective_query,
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

        debug_payload = {
            "query": effective_query,
            "original_query": original_query,
            "resolved_query": resolved_query,
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

        if conv_id:
            self.conversation_manager.add_memory_turn(
                conv_id=conv_id,
                query=original_query,
                answer=response_output.get("answer", ""),
                query_type=query_type,
                sources=response_output.get("sources", []),
                resolved_query=resolved_query,
            )

        return {
            "query": effective_query,
            "original_query": original_query,
            "resolved_query": resolved_query,
            "query_type": query_type,
            "classification_confidence": classification_confidence,
            "route": route,
            "answer": response_output.get("answer", ""),
            "confidence": response_output.get("confidence", "None"),
            "sources": response_output.get("sources", []),
            "status": response_output.get("status", "success"),
            "session_id": None,
            "conv_id": conv_id,
            "pipeline_stages": pipeline_stages,
            "debug_details": debug_payload,
        }
