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

    def _is_slide_noise(self, text: str) -> bool:
        """Filters out slide headers, professor names, page numbers, and presentation artifacts."""
        lower = text.lower()
        if re.search(r"\b(dr\.|professor|assistant professor|faculty|dept\.|department of|scope|vit\b|university)\b", lower):
            return True
        if re.search(r"^(module\s*[-–]\s*\d+|unit\s*[-–]\s*\d+|chapter\s*[-–]\s*\d+|slide\s*\d+|page\s*\d+)\b", lower):
            return True
        # Lines with only numbers or single words
        words = text.split()
        if len(words) < 4:
            return True
        return False

    def _extract_list_items(self, text: str) -> List[str]:
        """Extracts bullet or numbered list items from text chunks."""
        items = []
        # Pattern 1: explicit bullet points or numbered lists
        lines = text.split("\n")
        for line in lines:
            line_str = line.strip()
            # Match bullets or numbers like "1.", "1)", "-", "*", "•"
            m = re.match(r"^(?:[\•\-\*\–\—]|\d+[\.\)])\s*(.+)", line_str)
            if m:
                item = m.group(1).strip()
                if len(item) > 10 and not self._is_slide_noise(item):
                    items.append(item)
            elif ":" in line_str and len(line_str) < 120 and not line_str.startswith("http"):
                # Subheaders like "Narrow AI: Designed for specific tasks"
                parts = line_str.split(":", 1)
                header = parts[0].strip()
                body = parts[1].strip()
                if len(header) < 40 and len(body) > 10 and not self._is_slide_noise(line_str):
                    items.append(f"**{header}:** {body}")

        # Pattern 2: inline lists like "types include 1. ... 2. ..." or "such as X, Y, and Z"
        if not items:
            inline_matches = re.findall(r"(?:^|\s)(?:\d+[\.\)]|[a-c][\.\)])\s*([A-Z][^.\n]+(?:\.|$))", text)
            for im in inline_matches:
                im_clean = im.strip()
                if len(im_clean) > 12 and not self._is_slide_noise(im_clean):
                    items.append(im_clean)

        return items

    def _local_grounded_synthesis(self, query: str, results: List[RetrievalResult]) -> str:
        """
        Intelligent grounded synthesis engine that analyzes query intent, extracts
        key factual definitions and categorized items from retrieved chunks, filters
        out presentation slide noise, and formats a coherent, structured response.
        """
        q_lower = query.lower()
        q_type = self._classify_question_type(query)

        wants_definition = any(w in q_lower for w in ["what is", "what are", "define", "meaning", "definition", "explain"])
        wants_list = any(w in q_lower for w in ["types", "kinds", "categories", "advantages", "benefits", "features", "list", "disadvantages", "steps"])
        wants_comparison = any(w in q_lower for w in ["difference", "compare", "versus", " vs ", " vs."])
        wants_procedural = any(w in q_lower for w in ["how to", "how do", "how does", "steps to", "process of"])

        query_words = set(re.findall(r"\b\w{3,}\b", q_lower))
        stop_words = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "does", "explain", "tell", "describe", "discuss", "compare", "between",
            "about", "with", "from", "that", "this", "these", "those", "have", "were",
            "could", "would", "should", "then", "also", "some", "give", "types"
        }
        meaningful_words = query_words - stop_words

        # Case 1: Structured CSV records
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
                unique_rows = list(dict.fromkeys(matched_rows))[:4]
                return "\n".join(f"• {row}" for row in unique_rows)

        # Case 2: Prose & Presentation Documents
        # Step A: Collect and clean candidate sentences & list items
        candidate_sentences: List[Tuple[float, str, int]] = []
        extracted_list_items: List[str] = []
        seen_sentences: Set[str] = set()

        for chunk_rank, res in enumerate(results):
            text = res.chunk.text
            if "|" in text and ":" in text and "student id" in text.lower():
                continue

            # Extract any bullet/item points directly from chunk formatting
            if wants_list or wants_procedural:
                items = self._extract_list_items(text)
                for item in items:
                    if item not in extracted_list_items:
                        extracted_list_items.append(item)

            # Split into clean prose sentences
            sentences = re.split(r"(?<=[.!?\n])\s+", text)
            for s_idx, sentence in enumerate(sentences):
                s_clean = sentence.strip()
                s_clean = re.sub(r"^[#\-=*•]+\s*", "", s_clean).strip()

                if len(s_clean) < 18 or s_clean in seen_sentences:
                    continue
                if self._is_slide_noise(s_clean):
                    continue

                s_words = set(re.findall(r"\b\w{3,}\b", s_clean.lower()))
                overlap = len(meaningful_words.intersection(s_words))

                base_score = overlap * 2.5
                if s_idx == 0:
                    base_score += 1.0  # Topic sentence bonus
                base_score += max(0.0, 1.0 - (chunk_rank * 0.2))

                # Question-type specific scoring
                s_lower = s_clean.lower()
                if wants_definition and any(k in s_lower for k in [" is a ", " is an ", " refers to ", " is defined as ", " is the "]):
                    base_score += 3.5
                if wants_list and any(k in s_lower for k in ["include", "such as", "types of", "consists of", "categories", "advantages"]):
                    base_score += 2.5
                if wants_comparison and any(k in s_lower for k in ["while", "whereas", "difference", "contrast", "in contrast", "unlike"]):
                    base_score += 3.0

                if overlap > 0 or chunk_rank == 0:
                    candidate_sentences.append((base_score, s_clean, chunk_rank))
                    seen_sentences.add(s_clean)

        if not candidate_sentences:
            return results[0].chunk.text

        # Sort sentences by relevance
        candidate_sentences.sort(key=lambda x: x[0], reverse=True)

        # Select top non-redundant definition/prose sentences
        selected_sentences: List[str] = []
        for _, s_text, _ in candidate_sentences:
            words_curr = set(re.findall(r"\b\w{3,}\b", s_text.lower()))
            is_redundant = False
            for prev in selected_sentences:
                words_prev = set(re.findall(r"\b\w{3,}\b", prev.lower()))
                if len(words_curr) > 0 and len(words_curr.intersection(words_prev)) / len(words_curr) > 0.75:
                    is_redundant = True
                    break
            if not is_redundant:
                selected_sentences.append(s_text)
            if len(selected_sentences) >= 3:
                break

        # Step B: Structured Output Construction
        # Subcase 2.1: Compound Query (Definition + Types/List)
        if (wants_definition and wants_list) or (wants_list and len(extracted_list_items) >= 2):
            definition_part = selected_sentences[0] if selected_sentences else ""
            # Ensure definition part isn't already a list header
            if definition_part.endswith(":"):
                definition_part = definition_part[:-1] + "."

            items_to_show = extracted_list_items[:5] if extracted_list_items else [
                s for s in selected_sentences[1:] if len(s) < 160
            ]

            parts = []
            if definition_part:
                parts.append(definition_part)

            if items_to_show:
                list_title = "Key Types / Categories:" if "type" in q_lower or "kind" in q_lower else (
                    "Key Advantages:" if "advantage" in q_lower or "benefit" in q_lower else "Key Points:"
                )
                bullet_lines = [f"• {item if item.startswith('**') or item.startswith('•') else item}" for item in items_to_show]
                parts.append(f"{list_title}\n" + "\n".join(bullet_lines))

            if parts:
                return "\n\n".join(parts)

        # Subcase 2.2: Pure List or Procedural
        if (wants_list or q_type == "list") and len(extracted_list_items) >= 2:
            return "\n".join(f"• {it}" for it in extracted_list_items[:5])

        if wants_procedural or q_type == "procedural":
            if extracted_list_items:
                return "\n".join(f"{i+1}. {it}" for i, it in enumerate(extracted_list_items[:5]))
            return "\n".join(f"{i+1}. {s}" for i, s in enumerate(selected_sentences[:4]))

        # Subcase 2.3: Comparison
        if wants_comparison or q_type == "comparison":
            contrast_sentences = [s for s in selected_sentences if any(w in s.lower() for w in ["while", "whereas", "difference", "unlike", "contrast", "in contrast"])]
            if contrast_sentences:
                return " ".join(selected_sentences[:3])

        # Subcase 2.4: Standard Definition / Factual Summary
        if selected_sentences:
            return " ".join(selected_sentences[:3])

        return results[0].chunk.text

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
