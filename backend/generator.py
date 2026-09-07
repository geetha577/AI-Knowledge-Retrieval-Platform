"""
generator.py
Grounded answer generation engine.
Supports modular external LLM APIs (OpenAI, Gemini, Groq) with an intelligent
local extractive synthesis fallback when no API key is provided.
Strictly prevents hallucination when context is missing.
Supports different question types (Definition, Explanation, List/Advantages,
Comparison, Procedural).
"""

import os
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from .models import RetrievalResult, QueryResponse


SYSTEM_PROMPT = (
    "You are a factual knowledge assistant. Answer the user's question using ONLY "
    "the provided retrieved context. Do NOT use outside knowledge or speculate. "
    "If the answer cannot be found directly in the retrieved context, clearly state: "
    "'I couldn't find enough relevant information in the uploaded documents to answer this question.'"
)

REJECTION_MESSAGE = (
    "I couldn't find enough relevant information in the uploaded documents to answer this question."
)


class ResponseGenerator:
    """
    Constructs a grounded answer from retrieved context.
    Utilizes external LLM if an API key is available; otherwise, uses a local
    extractive synthesis algorithm that extracts, ranks, and structures matching
    factual sentences and lists from the retrieved context.
    """

    def __init__(self, provider: Optional[str] = None):
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()

        # Determine active provider
        if provider:
            self.provider = provider.lower()
        elif self.gemini_key:
            self.provider = "gemini"
        elif self.openai_key:
            self.provider = "openai"
        elif self.groq_key:
            self.provider = "groq"
        else:
            self.provider = "local_fallback"

    def generate_response(
        self,
        query: str,
        retrieval_data: Dict[str, Any],
    ) -> QueryResponse:
        """
        Main entry point for answer generation from retrieved context.
        """
        relevant_results: List[RetrievalResult] = retrieval_data.get("relevant_results", [])
        overall_confidence: str = retrieval_data.get("confidence", "None")

        # Case 1: No relevant chunks found or below threshold
        if not relevant_results:
            print("[GENERATION] No relevant context found. Returning grounded rejection.")
            return QueryResponse(
                answer=REJECTION_MESSAGE,
                confidence="None",
                sources=[],
                debug_details={
                    "mode": "rejection_no_context",
                    "retrieved_count": 0,
                    "prompt_used": None,
                },
            )

        # Build context text from relevant chunks
        context_blocks = []
        sources = []
        for i, res in enumerate(relevant_results):
            chunk = res.chunk
            header = f"[Source {i+1}: {chunk.source_id}]"
            context_blocks.append(f"{header}\n{chunk.text}")

            sources.append({
                "source_id": chunk.source_id,
                "document_name": chunk.document_name,
                "document_type": chunk.document_type,
                "page_number": chunk.page_number,
                "row_number": chunk.row_number,
                "similarity_score": round(res.similarity_score, 4),
                "relevance": res.relevance,
                "text_snippet": chunk.text[:220] + "..." if len(chunk.text) > 220 else chunk.text,
                "full_text": chunk.text,
            })

        combined_context = "\n\n".join(context_blocks)
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- RETRIEVED CONTEXT ---\n{combined_context}\n\n"
            f"--- USER QUESTION ---\n{query}\n\n"
            f"--- ANSWER ---"
        )

        # Case 2: Attempt generation via LLM API if configured
        answer = None
        generation_mode = self.provider

        if self.provider == "openai" and self.openai_key:
            answer = self._call_openai(query, combined_context)
        elif self.provider == "gemini" and self.gemini_key:
            answer = self._call_gemini(query, combined_context)
        elif self.provider == "groq" and self.groq_key:
            answer = self._call_groq(query, combined_context)

        # Case 3: Local grounded synthesis fallback
        if not answer:
            generation_mode = "Local Grounded Synthesis (Demo Fallback)"
            answer = self._local_grounded_synthesis(query, relevant_results)

        print("[GENERATION] Response generated successfully.")

        return QueryResponse(
            answer=answer,
            confidence=overall_confidence,
            sources=sources,
            debug_details={
                "mode": generation_mode,
                "retrieved_count": len(relevant_results),
                "context_length_chars": len(combined_context),
                "prompt_used": prompt,
            },
        )

    def _classify_question_type(self, query: str) -> str:
        """Classifies the query intent to shape the extractive response format."""
        q = query.lower()
        if any(w in q for w in ["compare", "difference between", "versus", " vs ", " vs."]):
            return "comparison"
        elif any(w in q for w in ["advantages", "benefits", "features", "types of", "list", "steps", "disadvantages"]):
            return "list"
        elif any(w in q for w in ["how does", "how do", "how is", "steps to", "process of"]):
            return "procedural"
        elif any(w in q for w in ["why is", "why does", "why do"]):
            return "conceptual"
        elif any(w in q for w in ["what is", "what are", "define", "definition"]):
            return "definition"
        elif any(w in q for w in ["explain", "describe", "discuss"]):
            return "explanation"
        return "general"

    def _local_grounded_synthesis(self, query: str, results: List[RetrievalResult]) -> str:
        """
        A pure Python grounded synthesis engine that extracts key factual statements
        from retrieved chunks that best correspond to the query terms, synthesizing
        a clean, readable response without making up facts.
        """
        q_type = self._classify_question_type(query)
        query_words = set(re.findall(r"\b\w{3,}\b", query.lower()))
        stop_words = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "does", "explain", "tell", "describe", "discuss", "compare", "between",
            "about", "with", "from", "that", "this", "these", "those", "have", "were",
            "could", "would", "should"
        }
        meaningful_words = query_words - stop_words

        # Check if query targets structured CSV records
        csv_results = [r for r in results if r.chunk.document_type == "CSV" or ("|" in r.chunk.text and ":" in r.chunk.text)]
        csv_keywords = {"student", "students", "roll", "rollno", "cgpa", "department", "marks", "grade", "table", "csv", "record"}
        query_is_csv_related = bool(meaningful_words.intersection(csv_keywords))

        if csv_results and (query_is_csv_related or len(csv_results) == len(results)):
            matched_rows = []
            for r in csv_results:
                row_text = r.chunk.text
                row_words = set(re.findall(r"\b\w{2,}\b", row_text.lower()))
                if meaningful_words and meaningful_words.intersection(row_words):
                    matched_rows.append(row_text)
                elif not meaningful_words or query_is_csv_related:
                    matched_rows.append(row_text)

            if matched_rows:
                # Return distinct top matching CSV rows formatted nicely
                unique_rows = list(dict.fromkeys(matched_rows))[:4]
                return "\n".join(f"• {row}" for row in unique_rows)

        # For prose documents: Extract and score candidate sentences across retrieved chunks
        candidate_sentences: List[Tuple[float, str, int]] = []
        seen_sentences: Set[str] = set()

        for chunk_rank, res in enumerate(results):
            text = res.chunk.text
            # Skip CSV formatted text in general prose flow
            if "|" in text and ":" in text:
                continue

            sentences = re.split(r"(?<=[.!?\n])\s+", text)
            for s_idx, sentence in enumerate(sentences):
                s_clean = sentence.strip()
                # Clean up markdown / heading markers
                s_clean = re.sub(r"^[#\-=*]+\s*", "", s_clean).strip()
                if len(s_clean) < 18 or s_clean in seen_sentences:
                    continue

                s_words = set(re.findall(r"\b\w{3,}\b", s_clean.lower()))
                overlap = len(meaningful_words.intersection(s_words))

                # Boost score based on:
                # 1. Direct keyword overlap
                # 2. Earlier chunk rank (higher similarity chunk)
                # 3. Leading position in chunk (often definitions / topic sentences)
                base_score = overlap * 2.0
                if s_idx == 0:
                    base_score += 1.0  # Topic sentence bonus
                base_score += max(0.0, 1.0 - (chunk_rank * 0.2))

                # Question-type specific boosting
                if q_type == "definition" and any(k in s_clean.lower() for k in [" is a ", " is an ", " refers to ", " is defined as "]):
                    base_score += 3.0
                elif q_type == "list" and any(k in s_clean.lower() for k in ["include", "such as", "types of", "advantages", "benefits"]):
                    base_score += 2.0
                elif q_type == "comparison" and any(k in s_clean.lower() for k in ["while", "whereas", "difference", "contrast", "in contrast"]):
                    base_score += 2.5

                if overlap > 0 or chunk_rank == 0:
                    candidate_sentences.append((base_score, s_clean, chunk_rank))
                    seen_sentences.add(s_clean)

        if not candidate_sentences:
            return results[0].chunk.text

        # Sort candidate sentences by score descending
        candidate_sentences.sort(key=lambda x: x[0], reverse=True)

        # Select top non-redundant sentences
        selected = []
        for _, s_text, _ in candidate_sentences:
            # Check lexical similarity with already selected to avoid near-duplicates
            words_curr = set(re.findall(r"\b\w{3,}\b", s_text.lower()))
            is_redundant = False
            for prev in selected:
                words_prev = set(re.findall(r"\b\w{3,}\b", prev.lower()))
                if len(words_curr) > 0 and len(words_curr.intersection(words_prev)) / len(words_curr) > 0.75:
                    is_redundant = True
                    break
            if not is_redundant:
                selected.append(s_text)
            if len(selected) >= 3:
                break

        if not selected:
            return results[0].chunk.text

        # Format output: if question was a list, format as bullets; otherwise as a cohesive paragraph
        if q_type == "list" and len(selected) > 1:
            return "\n".join(f"• {s}" for s in selected)

        return " ".join(selected)

    def _call_openai(self, query: str, context: str) -> Optional[str]:
        """Calls OpenAI Chat Completion API if openai package and key exist."""
        try:
            import urllib.request
            import json

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_key}",
                },
                data=json.dumps({
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                    ],
                    "temperature": 0.2,
                }).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[GENERATION] OpenAI API call failed ({e}). Falling back to local synthesis.")
            return None

    def _call_gemini(self, query: str, context: str) -> Optional[str]:
        """Calls Google Gemini API if key exists."""
        try:
            import urllib.request
            import json

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            prompt = f"{SYSTEM_PROMPT}\n\nRetrieved Context:\n{context}\n\nUser Question:\n{query}"

            req = urllib.request.Request(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}]
                }).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[GENERATION] Gemini API call failed ({e}). Falling back to local synthesis.")
            return None

    def _call_groq(self, query: str, context: str) -> Optional[str]:
        """Calls Groq API if key exists."""
        try:
            import urllib.request
            import json

            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.groq_key}",
                },
                data=json.dumps({
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                    ],
                    "temperature": 0.2,
                }).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[GENERATION] Groq API call failed ({e}). Falling back to local synthesis.")
            return None
