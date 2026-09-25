"""
clarification_agent.py
Milestone 3 - Multi-Agent Architecture: Clarification Agent

Responsible for:
1. Analyzing ambiguous or underspecified queries.
2. Generating concise, targeted clarification questions based on query intent and available knowledge domains.
3. Generating helpful, context-relevant suggestion chips for the UI.
4. Ensuring questions are concise, non-technical, and free of hallucination or internal agent reasoning.
"""

import re
from typing import Dict, Any, List, Optional, Tuple


class ClarificationAgent:
    """
    Clarification Agent that generates concise, targeted clarification questions
    and relevant suggestions when a user's query is identified as ambiguous or incomplete.
    """

    def __init__(self, available_domains: Optional[List[str]] = None):
        """
        Initializes the Clarification Agent.
        available_domains: Optional list of document names or domain topics present in the knowledge base.
        """
        self.available_domains = available_domains or []

    def generate_clarification(
        self,
        query: str,
        classification_confidence: float = 0.9,
        available_docs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a structured clarification request.

        Parameters:
            query: The original ambiguous query.
            classification_confidence: Confidence score of ambiguity classification.
            available_docs: Optional list of indexed document names.

        Returns:
            {
                "needs_clarification": True,
                "clarification_question": str,
                "reason": str,
                "confidence": float,
                "suggested_options": List[str]
            }
        """
        docs = available_docs or self.available_domains or []
        q_lower = query.strip().lower()

        question, reason, suggestions = self._build_clarification(q_lower, docs)

        return {
            "needs_clarification": True,
            "clarification_question": question,
            "reason": reason,
            "confidence": round(classification_confidence, 2),
            "suggested_options": suggestions,
        }

    def _build_clarification(
        self, q_lower: str, docs: List[str]
    ) -> Tuple[str, str, List[str]]:
        """Helper to tailor the clarification question and suggestions."""

        # 0. Multi-meaning word — specific handlers for common dual-interpretation words
        multi_meaning_map = {
            "python": (
                "Are you asking about Python the programming language, or Python as a topic in biology/general knowledge?",
                "The word 'Python' refers to both a programming language and a type of snake.",
                ["Python programming language", "Python (snake / biology)", "Python libraries / frameworks"]
            ),
            "networks": (
                "Are you asking about Computer Networks (like LAN, WAN, protocols) or Neural Networks (used in Artificial Intelligence)?",
                "The term 'networks' can mean Computer Networks (CSE) or Neural Networks (AI/ML).",
                ["Computer Networks (LAN, WAN, protocols)", "Neural Networks (AI/Deep Learning)", "Network security"]
            ),
            "network": (
                "Are you asking about Computer Networks or Neural Networks (AI/ML)?",
                "The term 'network' can refer to Computer Networks or Neural Networks.",
                ["Computer Network (CSE)", "Neural Network (AI)", "Network topology"]
            ),
            "memory": (
                "Are you asking about Computer Memory (RAM/ROM/cache), Memory Management in Operating Systems, or another context?",
                "The term 'memory' is used differently in hardware, OS, and AI contexts.",
                ["Computer Memory (RAM/ROM)", "OS Memory Management", "Memory in AI/ML"]
            ),
            "learning": (
                "Are you asking about Machine Learning (AI) or learning in an educational/human context?",
                "The term 'learning' could refer to Machine Learning or human education.",
                ["Machine Learning (AI/ML)", "Deep Learning", "Human learning / Education"]
            ),
            "language": (
                "Are you asking about a Programming Language (like Python, Java) or Natural Language (like English)?",
                "The term 'language' could mean programming language or natural language.",
                ["Programming language (Python, Java, C++)", "Natural Language Processing (NLP)", "Language models (AI)"]
            ),
            "model": (
                "Are you asking about an AI/ML model, a database model, or a software design model?",
                "The term 'model' is used in different ways across AI, databases, and software design.",
                ["AI/ML model", "Database model (ER diagram)", "Software design model"]
            ),
            "security": (
                "Are you asking about Cybersecurity, Network Security, or Information Security?",
                "The term 'security' can refer to different domains.",
                ["Cybersecurity fundamentals", "Network Security", "Information Security / data protection"]
            ),
            "intelligence": (
                "Are you asking about Artificial Intelligence (AI) or human/cognitive intelligence?",
                "The term 'intelligence' spans both AI and psychology/cognitive science.",
                ["Artificial Intelligence (AI)", "Human intelligence (Psychology)", "Emotional intelligence"]
            ),
            "architecture": (
                "Are you asking about Computer Architecture, Software Architecture, or Network Architecture?",
                "The term 'architecture' is used in multiple technical domains.",
                ["Computer Architecture (CPU, memory)", "Software Architecture (design patterns)", "Network Architecture"]
            ),
        }

        for keyword, (question, reason, suggestions) in multi_meaning_map.items():
            if keyword in q_lower.split() or f" {keyword}" in q_lower or q_lower.endswith(keyword):
                return question, reason, suggestions


        if any(w in q_lower for w in ["requirement", "prerequisite", "criteria"]):
            return (
                "Which requirements are you asking about — eligibility requirements, documents required, or application requirements?",
                "The query asks about requirements without specifying the context or category.",
                ["Eligibility requirements", "Application requirements", "Documents required"]
            )

        # 2. Application / Apply process ambiguity
        if "application process" in q_lower or "how do i apply" in q_lower or "how to apply" in q_lower or "application procedure" in q_lower:
            return (
                "Could you clarify which application process you mean — for an internship, student admission, or job opening?",
                "The query refers to an application process without indicating the specific program or role.",
                ["Internship application", "Student admission", "Job application"]
            )

        # 3. Process / Workflow ambiguity
        if any(w in q_lower for w in ["process", "procedure", "workflow"]):
            return (
                "Could you clarify which process or workflow you are referring to?",
                "The query mentions a process or procedure without specifying the subject.",
                ["OS Process Management", "Application workflow", "Student registration"]
            )

        # 4. Deadline / Date ambiguity
        if any(w in q_lower for w in ["deadline", "due date", "last date"]):
            return (
                "Could you please specify which deadline you are inquiring about?",
                "The query asks about deadlines without specifying the event or document.",
                ["Application deadline", "Project submission deadline", "Registration deadline"]
            )

        # 5. Generic pronoun ambiguity ("tell me about it", "explain this", "what about that")
        if any(p in q_lower for p in [" it", " this", " that", " them", " these", " those"]) or len(q_lower.split()) <= 4:
            # Check if we have indexed documents we can present as options
            doc_suggestions = []
            for doc in docs[:4]:
                if isinstance(doc, dict):
                    raw_name = doc.get("document_name") or doc.get("name") or ""
                else:
                    raw_name = str(doc)
                if raw_name:
                    clean_name = re.sub(r"\.[a-zA-Z0-9]+$", "", raw_name).replace("_", " ")
                    doc_suggestions.append(clean_name)

            if not doc_suggestions:
                doc_suggestions = [
                    "Operating Systems",
                    "Artificial Intelligence",
                    "Cybersecurity Basics",
                    "Student Records"
                ]

            return (
                "Your query appears ambiguous or underspecified. Could you please specify which topic, document, or concept you would like to know about?",
                "The query relies on vague pronouns or lacks an identifiable subject noun.",
                doc_suggestions[:3]
            )

        # 6. Default general ambiguity
        summary = query_summary(q_lower)
        return (
            f"Could you please provide a little more detail about what you are looking for regarding '{summary}'?",
            "The query lacks sufficient context to retrieve accurate information.",
            ["Eligibility requirements", "Application process", "Operating Systems"]
        )


def query_summary(query: str, max_len: int = 35) -> str:
    """Returns a clean short snippet of query."""
    clean = re.sub(r"[^\w\s]", "", query).strip()
    if len(clean) > max_len:
        return clean[:max_len] + "..."
    return clean or "your question"
