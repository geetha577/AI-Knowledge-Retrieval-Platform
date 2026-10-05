"""
conversation_manager.py
Milestone 3 - M3.1 + M3.2: Clarification Session Manager + Conversation Memory Agent

Manages:
1. Multi-turn clarification session state (M3.1).
2. Tracking turn limits (max 2 turns) to prevent endless questioning.
3. Intelligent context merging: combining the original query with the user's clarification response.
4. Cross-turn Conversation Memory (M3.2): remembers prior Q&A so follow-up queries
   like "How does paging relate to that?" are resolved using prior context.
"""

import time
import uuid
import re
from typing import Dict, Any, List, Optional


# ─────────────────────────────────────────────────────────────
# M3.2 — Conversation Memory: stores full Q&A history per conv
# ─────────────────────────────────────────────────────────────

class ConversationMemory:
    """
    Stores the complete conversation history for a user session.
    Provides context resolution for follow-up references.
    """

    MAX_TURNS = 10           # store at most 10 prior turns
    CONTEXT_WINDOW = 3       # inject at most last 3 relevant turns into prompts

    # Reference words that indicate a follow-up query
    REFERENCE_WORDS = {
        "it", "this", "that", "them", "these", "those",
        "above", "same", "previously", "earlier",
        "last", "mentioned", "discussed",
    }

    def __init__(self):
        self.turns: List[Dict[str, Any]] = []
        self.conv_id: str = f"conv_{uuid.uuid4().hex[:10]}"
        self.created_at: float = time.time()

    def add_turn(
        self,
        query: str,
        answer: str,
        query_type: str = "factual",
        sources: Optional[List[Dict]] = None,
        resolved_query: Optional[str] = None,
    ) -> None:
        """Record a completed Q&A turn to conversation history."""
        topics = self._extract_topics(resolved_query or query)

        self.turns.append({
            "turn_index": len(self.turns) + 1,
            "query": query,
            "resolved_query": resolved_query,
            "answer": answer[:500],
            "query_type": query_type,
            "sources": (sources or [])[:3],
            "topics": topics,
            "timestamp": time.time(),
        })

        # Trim to MAX_TURNS
        if len(self.turns) > self.MAX_TURNS:
            self.turns = self.turns[-self.MAX_TURNS:]

    def has_memory(self) -> bool:
        """Returns True if at least one prior turn exists."""
        return len(self.turns) > 0

    def is_followup(self, query: str) -> bool:
        """
        Detects whether the current query is a follow-up referring
        to a previous turn (uses pronouns or continuation phrases).
        """
        if not self.has_memory():
            return False

        q_lower = query.lower().strip()

        # Check for reference pronouns/phrases
        for ref in self.REFERENCE_WORDS:
            if re.search(rf"\b{re.escape(ref)}\b", q_lower):
                return True

        # Check for continuation phrases / dependent fragments
        continuation_starters = (
            "what about", "how about", "and ", "why", "how so", "more details",
            "tell me more", "give more", "explain more", "what else", "also"
        )
        if any(q_lower.startswith(cs) for cs in continuation_starters):
            return True

        return False

    def resolve_followup(self, query: str) -> str:
        """
        Enriches a follow-up query with prior context.
        e.g. "How does paging relate to that?" -> adds context about virtual memory
        """
        if not self.has_memory():
            return query

        last_turn = self.turns[-1]
        prior_topics = last_turn.get("topics", [])
        if not prior_topics:
            return query

        q_lower = query.lower()
        main_topic = prior_topics[0]

        # Replace pronouns with the most recent topic
        has_pronoun = False
        for pron in ["it", "this", "that", "them", "these", "those"]:
            if re.search(rf"\b{pron}\b", q_lower):
                query = re.sub(
                    rf"\b{pron}\b",
                    main_topic,
                    query,
                    flags=re.IGNORECASE,
                )
                has_pronoun = True

        if has_pronoun:
            return query.strip()

        # Continuation phrases like "what about paging?" -> "what about paging? (regarding virtual memory)"
        continuation_starters = (
            "what about", "how about", "and ", "why", "how so", "more details",
            "tell me more", "give more", "explain more", "what else", "also"
        )
        if any(q_lower.startswith(cs) for cs in continuation_starters):
            return f"{query.strip()} (regarding {main_topic})"

        return query


    def get_context_summary(self) -> str:
        """
        Returns a brief plain-text summary of recent conversation history
        for LLM context injection.
        """
        if not self.has_memory():
            return ""

        recent = self.turns[-self.CONTEXT_WINDOW:]
        lines = ["[Conversation History]"]
        for t in recent:
            q = t.get("resolved_query") or t.get("query", "")
            a = t.get("answer", "")
            lines.append(f"Q: {q}")
            lines.append(f"A: {a[:300]}{'...' if len(a) > 300 else ''}")
        return "\n".join(lines)

    def get_recent_topics(self) -> List[str]:
        """Returns the top topics from recent turns for context injection."""
        topics = []
        for turn in self.turns[-self.CONTEXT_WINDOW:]:
            topics.extend(turn.get("topics", []))
        seen = set()
        unique = []
        for t in topics:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique[:5]

    def _extract_topics(self, text: str) -> List[str]:
        """Lightweight keyword extraction from a query."""
        stopwords = {
            "what", "how", "why", "when", "where", "who", "which",
            "is", "are", "was", "were", "do", "does", "did",
            "the", "a", "an", "of", "in", "for", "to", "and", "or",
            "can", "could", "should", "would", "tell", "me", "about",
            "explain", "describe", "give", "difference", "between",
        }
        clean_text = re.sub(r"[^\w\s]", " ", text.lower())
        words = [w for w in clean_text.split() if w not in stopwords and len(w) >= 3]
        topics = []
        if len(words) >= 2:
            topics.append(" ".join(words[:2]))
        if "virtual" in words and "memory" in words and "virtual memory" not in topics:
            topics.insert(0, "virtual memory")
        for w in words:
            if w not in topics:
                topics.append(w)
        return topics[:3]

    def clear(self):
        """Resets this conversation's history."""
        self.turns.clear()


# ─────────────────────────────────────────────────────────────
# M3.1 — Clarification Session Manager
# ─────────────────────────────────────────────────────────────

class ConversationManager:
    """
    M3.1: Manages active clarification sessions for ambiguous queries.
    M3.2: Manages long-term conversation memory stores per conv_id.
    """

    def __init__(self, max_clarification_turns: int = 2):
        self.max_clarification_turns = max_clarification_turns
        # M3.1 - clarification sessions keyed by session_id
        self.sessions: Dict[str, Dict[str, Any]] = {}
        # M3.2 - conversation memories keyed by conv_id
        self.memories: Dict[str, ConversationMemory] = {}

    # ─── M3.2 Conversation Memory API ─────────────────────────

    def get_or_create_memory(self, conv_id: Optional[str] = None) -> ConversationMemory:
        """Returns existing conversation memory or creates a new one."""
        if conv_id and conv_id in self.memories:
            return self.memories[conv_id]
        memory = ConversationMemory()
        if conv_id:
            memory.conv_id = conv_id
        self.memories[memory.conv_id] = memory
        return memory

    def get_memory(self, conv_id: str) -> Optional[ConversationMemory]:
        """Retrieves an existing memory by conv_id."""
        return self.memories.get(conv_id)

    def add_memory_turn(
        self,
        conv_id: str,
        query: str,
        answer: str,
        query_type: str = "factual",
        sources: Optional[List[Dict]] = None,
        resolved_query: Optional[str] = None,
    ) -> None:
        """Records a completed Q&A turn to conversation memory."""
        memory = self.get_memory(conv_id)
        if memory:
            memory.add_turn(
                query=query,
                answer=answer,
                query_type=query_type,
                sources=sources,
                resolved_query=resolved_query,
            )

    def resolve_followup_query(self, conv_id: str, query: str) -> str:
        """
        If the query references prior context, enriches it with memory.
        Returns the original query unchanged if no prior context exists.
        """
        memory = self.get_memory(conv_id)
        if not memory or not memory.is_followup(query):
            return query
        resolved = memory.resolve_followup(query)
        if resolved != query:
            print(f"[MEMORY] Follow-up resolved: '{query}' -> '{resolved}'")
        return resolved

    def get_conversation_context(self, conv_id: str) -> str:
        """Returns conversation history summary for LLM context injection."""
        memory = self.get_memory(conv_id)
        if not memory:
            return ""
        return memory.get_context_summary()

    def get_memory_info(self, conv_id: str) -> Dict[str, Any]:
        """Returns metadata about the current conversation memory."""
        memory = self.get_memory(conv_id)
        if not memory:
            return {"conv_id": conv_id, "turns": 0, "topics": []}
        return {
            "conv_id": conv_id,
            "turns": len(memory.turns),
            "topics": memory.get_recent_topics(),
        }

    # ─── M3.1 Clarification Session API ───────────────────────

    def start_session(
        self,
        original_query: str,
        clarification_question: str,
        suggested_options: Optional[List[str]] = None,
    ) -> str:
        """Creates a new clarification session and returns a unique session_id."""
        session_id = f"clarify_{uuid.uuid4().hex[:12]}"
        self.sessions[session_id] = {
            "session_id": session_id,
            "original_query": original_query.strip(),
            "clarification_history": [
                {
                    "turn": 1,
                    "clarification_question": clarification_question,
                    "suggested_options": suggested_options or [],
                    "timestamp": time.time(),
                }
            ],
            "clarification_count": 1,
            "resolved_query": None,
            "status": "pending_clarification",
            "created_at": time.time(),
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an active clarification session."""
        return self.sessions.get(session_id)

    def record_turn(
        self,
        session_id: str,
        user_response: str,
        new_clarification_question: Optional[str] = None,
        suggested_options: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Records a user's clarification response and updates turn count."""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found."}

        if session["clarification_history"]:
            session["clarification_history"][-1]["user_response"] = user_response.strip()

        session["clarification_count"] += 1

        if new_clarification_question:
            session["clarification_history"].append({
                "turn": session["clarification_count"],
                "clarification_question": new_clarification_question,
                "suggested_options": suggested_options or [],
                "timestamp": time.time(),
            })

        return session

    def resolve_query(self, original_query: str, clarification_response: str) -> str:
        """
        Intelligently merges the original query and the user's clarification response.
        """
        orig = original_query.strip()
        clar = clarification_response.strip()

        if not clar:
            return orig

        orig_clean = orig.rstrip("?.!").strip()
        orig_lower = orig_clean.lower()
        clar_lower = clar.lower()
        clar_clean = clar.rstrip("?.!").strip()

        # Pattern 0: Clarification is already a complete self-contained question (≥6 words with question words)
        if len(clar.split()) >= 6 and (clar.endswith("?") or any(
            w in clar.lower().split()[:3] for w in ["what", "how", "explain", "describe", "tell", "where", "why", "when"]
        )):
            return clar

        # Pattern 1: Pronoun substitution (it, this, that, etc.)
        for pron in ["it", "this", "that", "them", "these", "those"]:
            if re.search(rf"\b{pron}\b", orig_lower):
                c_clean = re.sub(
                    r"^(for|about|with|regarding)\s+", "", clar_clean, flags=re.IGNORECASE
                ).strip()
                resolved = re.sub(rf"\b{pron}\b", c_clean, orig_clean, flags=re.IGNORECASE)
                return self._finalize_sentence(resolved, orig)

        # Pattern 2: Requirements queries
        if "requirements" in orig_lower:
            adj = re.sub(r"^(for|about|of|regarding)\s+", "", clar_clean, flags=re.IGNORECASE).strip()
            if "requirement" in adj.lower():
                resolved = re.sub(r"\b(the\s+)?requirements\b", adj, orig_clean, flags=re.IGNORECASE)
            else:
                resolved = re.sub(r"\b(the\s+)?requirements\b", f"the {adj} requirements", orig_clean, flags=re.IGNORECASE)
            return self._finalize_sentence(resolved, orig)

        # Pattern 3: Process / procedure / workflow / application queries
        if "process" in orig_lower or "procedure" in orig_lower or "workflow" in orig_lower:
            qualifier = re.sub(r"^(for|about|of|in|regarding)\s+", "", clar_clean, flags=re.IGNORECASE).strip()
            if clar_lower.startswith(("for ", "of ", "in ", "regarding ")):
                resolved = f"{orig_clean} {clar_clean}"
            elif "application process" in orig_lower:
                resolved = re.sub(r"\b(the\s+)?application process\b", f"the {qualifier} application process", orig_clean, flags=re.IGNORECASE)
            else:
                resolved = re.sub(r"\b(the\s+)?(process|procedure|workflow)\b", rf"the {qualifier} \2", orig_clean, flags=re.IGNORECASE)
            return self._finalize_sentence(resolved, orig)

        # Pattern 4: Apply queries
        if "apply" in orig_lower:
            if clar_lower.startswith(("for", "to", "in")):
                resolved = f"{orig_clean} {clar_clean}"
            else:
                resolved = f"{orig_clean} for {clar_clean}"
            return self._finalize_sentence(resolved, orig)

        # Pattern 5: Preposition-led clarification
        if clar_lower.startswith(("for ", "in ", "about ", "regarding ", "of ", "with ", "to ")):
            resolved = f"{orig_clean} {clar_clean}"
            return self._finalize_sentence(resolved, orig)

        # Pattern 6: Chip-style topic replacement or multi-meaning keyword replacement
        # e.g., "tell me about networks" + "Computer Networks (LAN, WAN, protocols)" -> "tell me about Computer Networks"
        # e.g., "what is python" + "Python programming language" -> "what is Python programming language"
        # e.g., "explain memory" + "Computer Memory (RAM/ROM)" -> "explain Computer Memory"
        clar_core = re.sub(r"\s*\(.*?\)", "", clar_clean).strip()

        multi_meaning_words = [
            "networks", "network", "python", "memory", "language", "agent",
            "architecture", "security", "intelligence", "learning", "model",
            "cloud", "protocol", "kernel", "thread", "interface"
        ]
        for kw in multi_meaning_words:
            if re.search(rf"\b{kw}\b", orig_lower):
                resolved = re.sub(rf"\b{kw}\b", clar_core, orig_clean, flags=re.IGNORECASE)
                return self._finalize_sentence(resolved, orig)

        # If original has conversational trigger phrases, substitute or append cleanly
        for trigger in ["tell me about", "explain", "describe", "discuss"]:
            if trigger in orig_lower:
                resolved = f"{trigger.capitalize()} {clar_core}"
                return self._finalize_sentence(resolved, orig)

        # Default fallback
        resolved = f"{orig_clean} about {clar_core}"
        return self._finalize_sentence(resolved, orig)



    def _finalize_sentence(self, text: str, original_query: str) -> str:
        """Cleans up spaces and restores question mark if original had one."""
        cleaned = re.sub(r"\s+", " ", text).strip()
        if original_query.strip().endswith("?") and not cleaned.endswith("?"):
            cleaned += "?"
        return cleaned

    def complete_session(self, session_id: str, resolved_query: str):
        """Marks a clarification session as completed."""
        session = self.sessions.get(session_id)
        if session:
            session["resolved_query"] = resolved_query
            session["status"] = "completed"

    def clear_session(self, session_id: str):
        """Removes a clarification session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all(self):
        """Clears all clarification sessions and conversation memories."""
        self.sessions.clear()
        self.memories.clear()

