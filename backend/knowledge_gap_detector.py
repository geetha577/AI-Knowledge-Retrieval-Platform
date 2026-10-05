"""
knowledge_gap_detector.py
Milestone 4 - M4.1: Knowledge Gap Detection Engine

Analyzes query analytics, low-confidence responses, and zero-result queries to detect
recurrent knowledge gaps in the knowledge base. Clusters ungrounded queries into actionable
gap records and generates recommendations for content authors and evaluators.
"""

import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from .analytics_engine import AnalyticsEngine


class KnowledgeGapDetector:
    """
    Identifies systemic gaps in the indexed documents by analyzing unanswered
    and low-confidence query patterns over time.
    """

    def __init__(self, analytics_engine: AnalyticsEngine):
        self.analytics_engine = analytics_engine

    def detect_gaps(self, min_confidence_threshold: float = 0.40) -> List[Dict[str, Any]]:
        """
        Scans all recorded query logs and identifies knowledge base gaps.
        Returns a sorted list of gap records ordered by frequency (highest need first).
        """
        logs = self.analytics_engine.get_logs(limit=2000)

        # Filter for queries that struggled: no_results, None/Low confidence, or below threshold
        problem_entries = []
        for entry in logs:
            conf = entry.get("confidence", "None").lower()
            status = entry.get("status", "answered")
            score = entry.get("top_similarity_score", 0.0)

            if status == "no_results" or conf in ["none", "low"] or score < min_confidence_threshold:
                # Exclude queries that were just asking for clarification (ambiguous)
                if status != "clarification_required":
                    problem_entries.append(entry)

        if not problem_entries:
            return []

        # Group problem queries by key thematic nouns/phrases
        topic_clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        stopwords = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "does", "tell", "about", "this", "that", "these", "those", "have", "were",
            "from", "with", "into", "their", "there", "make", "find", "give", "help",
            "explain", "describe", "discuss", "show", "many", "much", "some", "any",
            "could", "would", "should", "your", "mine", "ours", "work", "mean",
        }

        for entry in problem_entries:
            q_text = entry.get("query", "").strip()
            # Extract content words
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", q_text) if w.lower() not in stopwords]
            if not words:
                topic_clusters["General Unknown Questions"].append(entry)
                continue

            # Determine primary cluster label (e.g. 2-word phrase or main noun)
            if len(words) >= 2:
                cluster_label = f"{words[0].capitalize()} {words[1].capitalize()}"
            else:
                cluster_label = words[0].capitalize()

            # Merge similar clusters (e.g., "Phishing Attack" and "Phishing Attacks")
            matched_key = None
            for existing_key in topic_clusters.keys():
                existing_words = set(existing_key.lower().split())
                if any(w in existing_words for w in words[:2]):
                    matched_key = existing_key
                    break

            if matched_key:
                topic_clusters[matched_key].append(entry)
            else:
                topic_clusters[cluster_label].append(entry)

        # Build structured gap records
        gaps = []
        for topic_name, entries in topic_clusters.items():
            freq = len(entries)
            sample_queries = list(dict.fromkeys(e.get("query", "") for e in entries))[:5]
            avg_score = sum(e.get("top_similarity_score", 0.0) for e in entries) / freq

            if freq >= 3:
                severity = "High"
            elif freq == 2:
                severity = "Medium"
            else:
                severity = "Low"

            # Generate friendly actionable recommendation
            recommendation = (
                f"Consider uploading reference documents, documentation, or FAQs covering "
                f"'{topic_name.lower()}' to satisfy user queries in this area."
            )

            gaps.append({
                "gap_id": f"gap_{abs(hash(topic_name)) % 100000}",
                "topic": topic_name,
                "frequency": freq,
                "severity": severity,
                "sample_queries": sample_queries,
                "average_score": round(avg_score, 4),
                "recommendation": recommendation,
                "latest_query_date": entries[-1].get("date_str", ""),
            })

        # Sort gaps by frequency descending, then severity
        severity_order = {"High": 0, "Medium": 1, "Low": 2}
        gaps.sort(key=lambda g: (severity_order.get(g["severity"], 3), -g["frequency"]))

        return gaps
