"""
query_understanding_agent.py
Milestone 2 - Multi-Agent Architecture: Query Understanding Agent

Analyzes incoming user queries, classifies them into factual, procedural,
comparative, or ambiguous categories, computes classification confidence,
and determines appropriate routing (retrieval vs. clarification).
"""

import re
from typing import Dict, Any, List, Tuple


class QueryUnderstandingAgent:
    """
    Analyzes user queries to understand intent and categorize them into:
    1. factual: definitions, direct facts, concept explanations
    2. procedural: how-to guides, mechanisms, workflows, sequential steps
    3. comparative: differences, comparisons, vs, trade-offs
    4. ambiguous: underspecified, vague pronouns, missing context

    Routes factual, procedural, and comparative to retrieval.
    Routes ambiguous to clarification.
    """

    def __init__(self):
        self.comparative_patterns = [
            r"\bcompare\b",
            r"\bcomparison\b",
            r"\bdifference\s+(between|in|of)\b",
            r"\bhow\s+do\s+.+\s+differ\b",
            r"\bdistinguish\s+(between|from)\b",
            r"\bversus\b",
            r"\bvs\.?\b",
            r"\bbetter\s+than\b",
            r"\bcontrast\b",
            r"\badvantages\s+of\s+.+\s+(over|compared\s+to)\b",
            r"\bsimilarities\s+(between|and)\b",
        ]

        self.procedural_patterns = [
            r"\bhow\s+(do|does|can|to|should|would)\b",
            r"\bsteps?\s+(involved|to|for|in)\b",
            r"\bprocedure\s+(for|to)\b",
            r"\bprocess\s+(of|for)\b",
            r"\bworkflow\b",
            r"\bguide\s+(to|for)\b",
            r"\bhow\s+it\s+works\b",
            r"\binstructions\s+(for|to)\b",
            r"\bway\s+to\b",
            r"\bmethod\s+(for|to)\b",
            r"\bhow\s+is\s+.+\s+(implemented|performed|managed|handled)\b",
        ]

        self.factual_patterns = [
            r"\bwhat\s+(is|are|was|were)\b",
            r"\bdefine\b",
            r"\bdefinition\s+of\b",
            r"\bwho\s+(is|are|was|were)\b",
            r"\bwhich\b",
            r"\bwhen\s+(did|was|is)\b",
            r"\bwhere\s+(is|are)\b",
            r"\bexplain\b",
            r"\bdescribe\b",
            r"\bmeaning\s+of\b",
            r"\bconcept\s+of\b",
            r"\btypes\s+of\b",
            r"\blist\b",
        ]

        self.ambiguous_exact_phrases = [
            "tell me about it",
            "tell me about this",
            "tell me about that",
            "explain that",
            "explain this",
            "explain it",
            "what about this",
            "what about that",
            "what about it",
            "help me with this",
            "help me with that",
            "tell me more",
            "what is this",
            "what is that",
            "what is it",
            "can you explain",
            "can you help",
            "give me details",
            "more information",
            "what does this do",
            "what does that do",
        ]

        # Words with multiple distinct meanings across domains — trigger clarification
        self.multi_meaning_words = {
            "python": ["Python programming language", "Python (the snake / biology)"],
            "networks": ["Computer Networks (CSE)", "Neural Networks (AI/ML)"],
            "network": ["Computer Network", "Neural Network (AI)"],
            "memory": ["Computer Memory (RAM/ROM)", "Memory Management (OS)"],
            "language": ["Programming language", "Natural language / Linguistics"],
            "agent": ["AI Agent (software)", "Agent (general/business context)"],
            "architecture": ["Computer Architecture", "Software Architecture"],
            "security": ["Cybersecurity", "Network Security"],
            "intelligence": ["Artificial Intelligence", "Human Intelligence (Psychology)"],
            "learning": ["Machine Learning (AI)", "Human Learning / Education"],
            "model": ["AI/ML Model", "Database Model"],
            "cloud": ["Cloud Computing", "Cloud Storage"],
            "protocol": ["Network Protocol", "Communication Protocol"],
            "kernel": ["OS Kernel", "Kernel function (Mathematics/ML)"],
            "thread": ["OS Thread (Multithreading)", "Programming Thread"],
            "interface": ["User Interface (UI)", "Network Interface / API"],
        }

    def _is_ambiguous(self, query: str) -> Tuple[bool, float, str]:
        cleaned = query.strip().lower()
        normalized = re.sub(r"[^\w\s]", "", cleaned).strip()

        for phrase in self.ambiguous_exact_phrases:
            phrase_norm = re.sub(r"[^\w\s]", "", phrase)
            if normalized == phrase_norm:
                return True, 0.95, f"Matches known ambiguous pattern: '{phrase}'"

        words = normalized.split()
        if not words:
            return True, 1.0, "Empty query."

        # Check pronoun references lacking substantive antecedent nouns
        # e.g., "tell me about it", "can you help me with this", "explain that"
        vague_tokens = {
            "it", "this", "that", "these", "those", "something", "anything", "stuff",
            "explain", "tell", "show", "what", "how", "why", "about", "more", "please",
            "help", "can", "could", "would", "you", "me", "with", "for", "give", "details",
            "information", "info", "clarify", "describe", "is", "are", "do", "does"
        }
        if all(w in vague_tokens for w in words):
            return True, 0.92, "Query consists only of conversational pronouns and helper words without a domain entity."

        if len(words) <= 6 and any(p in words for p in ["it", "that", "this"]):
            substantive_words = [w for w in words if w not in vague_tokens]
            if not substantive_words:
                return True, 0.88, "Query refers to demonstrative pronoun ('it', 'this', 'that') without an identified domain concept."

        # Check for underspecified domain queries lacking substantive qualifiers or context
        # e.g., "What is the application process?", "Tell me about the requirements", "How do I apply?"
        generic_domain_nouns = {
            "requirements", "requirement", "criteria", "eligibility", "process",
            "procedure", "workflow", "deadline", "deadlines", "details", "steps",
            "rules", "policy", "fees", "prerequisites", "prerequisite", "documents",
            "application", "apply"
        }
        stopwords_and_fillers = {
            "what", "is", "are", "the", "tell", "me", "about", "how", "do", "i",
            "can", "to", "give", "show", "please", "for", "of", "in", "with",
            "a", "an", "any", "some", "my", "our", "all", "need", "needed", "get"
        }

        if len(words) <= 7:
            non_generic = [w for w in words if w not in generic_domain_nouns and w not in stopwords_and_fillers]
            has_generic = any(w in generic_domain_nouns for w in words)
            if has_generic and not non_generic:
                matched = [w for w in words if w in generic_domain_nouns]
                return True, 0.90, f"Query asks about generic domain concept ({', '.join(matched)}) without identifying the program, course, or subject."

        # Check for multi-meaning words — words that have two or more distinct domain interpretations
        # e.g., "tell me about python" → could be programming language OR the snake
        # e.g., "tell me about networks" → could be computer networks OR neural networks
        filler_words = {
            "tell", "me", "about", "explain", "what", "is", "are", "describe",
            "show", "give", "discuss", "the", "a", "an", "please", "can", "you",
            "briefly", "in", "detail", "details", "i", "want", "to", "know",
            "understand", "how", "does", "do", "and", "of", "its"
        }
        for word in words:
            if word in self.multi_meaning_words:
                # Make sure query doesn't already have disambiguating context
                remaining = [w for w in words if w != word and w not in filler_words]
                if not remaining:
                    options = self.multi_meaning_words[word]
                    return (
                        True,
                        0.93,
                        f"'{word}' has multiple domain meanings ({' / '.join(options)}) and the query lacks disambiguating context."
                    )

        return False, 0.0, ""


    def analyze(self, query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            return {
                "query": query,
                "query_type": "ambiguous",
                "classification_confidence": 1.0,
                "route": "clarification",
                "reasoning": "Empty query provided.",
            }

        q_clean = query.strip()
        q_lower = q_clean.lower()

        # 1. Check for ambiguity first
        is_ambig, ambig_conf, ambig_reason = self._is_ambiguous(q_clean)
        if is_ambig:
            return {
                "query": q_clean,
                "query_type": "ambiguous",
                "classification_confidence": ambig_conf,
                "route": "clarification",
                "reasoning": ambig_reason,
            }

        # 2. Check for comparative intent
        for pat in self.comparative_patterns:
            if re.search(pat, q_lower):
                return {
                    "query": q_clean,
                    "query_type": "comparative",
                    "classification_confidence": 0.95,
                    "route": "retrieval",
                    "reasoning": f"Matched comparative pattern '{pat}'",
                }

        # 3. Check for procedural intent
        for pat in self.procedural_patterns:
            if re.search(pat, q_lower):
                return {
                    "query": q_clean,
                    "query_type": "procedural",
                    "classification_confidence": 0.92,
                    "route": "retrieval",
                    "reasoning": f"Matched procedural pattern '{pat}'",
                }

        # 4. Check for factual intent
        for pat in self.factual_patterns:
            if re.search(pat, q_lower):
                return {
                    "query": q_clean,
                    "query_type": "factual",
                    "classification_confidence": 0.90,
                    "route": "retrieval",
                    "reasoning": f"Matched factual pattern '{pat}'",
                }

        # 5. Default fallback
        return {
            "query": q_clean,
            "query_type": "factual",
            "classification_confidence": 0.85,
            "route": "retrieval",
            "reasoning": "Defaulted to factual knowledge inquiry for substantive topical query.",
        }
