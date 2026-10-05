"""
analytics_engine.py
Milestone 4 - M4.1: Query Analytics Module

Tracks query events, classification routes, retrieval scores, response confidence,
unanswered queries, and latency. Persists analytics data separately from the vector store.
Provides filtering, grouping, and statistical summaries for reporting and gap detection.
"""

import os
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from threading import Lock


class AnalyticsEngine:
    """
    Thread-safe analytics engine that records query resolution telemetry,
    maintains query logs, and calculates performance metrics and domain coverage.
    """

    def __init__(self, storage_dir: str = "data/analytics"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logs_file = self.storage_dir / "query_logs.json"
        self.lock = Lock()
        self._init_storage()
        # Load configuration
        from .config import config
        self.storage_type = config.analytics.get("storage", "json").lower()
        if self.storage_type == "sqlite":
            if str(storage_dir) == "data/analytics":
                self.db_path = config.analytics_db_path
            else:
                self.db_path = self.storage_dir / "analytics.db"
            self._init_sqlite()

    def _init_storage(self):
        """Initializes empty storage files if not already present."""
        if not self.logs_file.exists():
            try:
                with open(self.logs_file, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
            except Exception as e:
                print(f"[ANALYTICS] Warning: Could not initialize analytics log file: {e}")

    def _init_sqlite(self):
        """Initializes SQLite database and creates the queries table if it doesn't exist."""
        import sqlite3
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS queries (
            id TEXT PRIMARY KEY,
            timestamp REAL,
            date_str TEXT,
            query TEXT,
            resolved_query TEXT,
            query_type TEXT,
            route TEXT,
            confidence TEXT,
            status TEXT,
            top_similarity_score REAL,
            retrieved_chunks_count INTEGER,
            source_documents TEXT,
            duration_sec REAL,
            session_id TEXT,
            conv_id TEXT,
            clarification_question TEXT,
            is_unanswered INTEGER,
            error TEXT
        );
        """
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(create_table_sql)
            self.conn.commit()

    # --- Overridden methods for SQLite vs JSON storage ---
    def record_query(
        self,
        query: str,
        query_type: str,
        route: str,
        confidence: str,
        status: str,
        top_similarity_score: float = 0.0,
        retrieved_chunks_count: int = 0,
        sources: Optional[List[Dict[str, Any]]] = None,
        duration_sec: float = 0.0,
        session_id: Optional[str] = None,
        conv_id: Optional[str] = None,
        resolved_query: Optional[str] = None,
        clarification_question: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a query event using either SQLite or JSON storage based on configuration."""
        source_docs = []
        if sources:
            for s in sources:
                doc_name = s.get("document_name") or s.get("document") or ""
                if doc_name and doc_name not in source_docs:
                    source_docs.append(doc_name)

        entry = {
            "id": f"q_{int(time.time() * 1000)}",
            "timestamp": time.time(),
            "date_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "query": query.strip(),
            "resolved_query": resolved_query.strip() if resolved_query else None,
            "query_type": query_type or "factual",
            "route": route or "retrieval",
            "confidence": confidence or "None",
            "status": status,
            "top_similarity_score": round(float(top_similarity_score), 4),
            "retrieved_chunks_count": int(retrieved_chunks_count),
            "source_documents": source_docs,
            "duration_sec": round(float(duration_sec), 4),
            "session_id": session_id,
            "conv_id": conv_id,
            "clarification_question": clarification_question,
            "is_unanswered": bool(status == "no_results" or (status != "clarification_required" and confidence.lower() in ["none", "low"])),
            "error": error,
        }

        if getattr(self, "storage_type", "json") == "sqlite":
            # Insert into SQLite
            insert_sql = """
                INSERT OR REPLACE INTO queries (
                    id, timestamp, date_str, query, resolved_query, query_type, route,
                    confidence, status, top_similarity_score, retrieved_chunks_count,
                    source_documents, duration_sec, session_id, conv_id,
                    clarification_question, is_unanswered, error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """
            values = (
                entry["id"], entry["timestamp"], entry["date_str"], entry["query"], entry["resolved_query"],
                entry["query_type"], entry["route"], entry["confidence"], entry["status"], entry["top_similarity_score"],
                entry["retrieved_chunks_count"], json.dumps(entry["source_documents"]), entry["duration_sec"],
                entry["session_id"], entry["conv_id"], entry["clarification_question"], 1 if entry["is_unanswered"] else 0, entry["error"]
            )
            with self.lock:
                cur = self.conn.cursor()
                cur.execute(insert_sql, values)
                self.conn.commit()
        else:
            # Existing JSON implementation
            with self.lock:
                logs = self._read_logs()
                logs.append(entry)
                # Retain last 2000 records
                if len(logs) > 2000:
                    logs = logs[-2000:]
                self._write_logs(logs)
        return entry

    def _fetch_all_rows(self) -> List[Dict[str, Any]]:
        """Utility to fetch all rows from SQLite as dicts (used by other methods)."""
        rows = []
        select_sql = "SELECT * FROM queries ORDER BY timestamp"
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(select_sql)
            col_names = [description[0] for description in cur.description]
            for row in cur.fetchall():
                row_dict = dict(zip(col_names, row))
                # JSON‑decode source_documents
                if isinstance(row_dict.get("source_documents"), str):
                    try:
                        row_dict["source_documents"] = json.loads(row_dict["source_documents"])
                    except Exception:
                        row_dict["source_documents"] = []
                # Convert integer flag to bool for consistency
                row_dict["is_unanswered"] = bool(row_dict.get("is_unanswered"))
                rows.append(row_dict)
        return rows

    def get_logs(
        self,
        domain: Optional[str] = None,
        query_type: Optional[str] = None,
        confidence: Optional[str] = None,
        status: Optional[str] = None,
        unanswered_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve logs from SQLite or JSON storage with the same filtering semantics as before."""
        if getattr(self, "storage_type", "json") == "sqlite":
            # Build WHERE clauses based on parameters
            clauses = []
            params = []
            if domain and domain.lower() != "all":
                clauses.append("source_documents LIKE ?")
                params.append(f"%{domain.lower()}%")
            if query_type and query_type.lower() != "all":
                clauses.append("LOWER(query_type) = ?")
                params.append(query_type.lower())
            if confidence and confidence.lower() != "all":
                clauses.append("LOWER(confidence) = ?")
                params.append(confidence.lower())
            if status and status.lower() != "all":
                clauses.append("LOWER(status) = ?")
                params.append(status.lower())
            if unanswered_only:
                clauses.append("is_unanswered = 1")

            where_clause = " WHERE " + " AND ".join(clauses) if clauses else ""
            query_sql = f"SELECT * FROM queries{where_clause} ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            with self.lock:
                cur = self.conn.cursor()
                cur.execute(query_sql, tuple(params))
                col_names = [desc[0] for desc in cur.description]
                results = []
                for row in cur.fetchall():
                    row_dict = dict(zip(col_names, row))
                    if isinstance(row_dict.get("source_documents"), str):
                        try:
                            row_dict["source_documents"] = json.loads(row_dict["source_documents"])
                        except Exception:
                            row_dict["source_documents"] = []
                    row_dict["is_unanswered"] = bool(row_dict.get("is_unanswered"))
                    results.append(row_dict)
            return results
        else:
            # Existing JSON path (unchanged)
            with self.lock:
                logs = self._read_logs()
            results = []
            for entry in reversed(logs):
                if domain and domain.lower() != "all":
                    if not any(domain.lower() in d.lower() for d in entry.get("source_documents", [])):
                        continue
                if query_type and query_type.lower() != "all":
                    if entry.get("query_type", "").lower() != query_type.lower():
                        continue
                if confidence and confidence.lower() != "all":
                    if entry.get("confidence", "").lower() != confidence.lower():
                        continue
                if status and status.lower() != "all":
                    if entry.get("status", "").lower() != status.lower():
                        continue
                if unanswered_only and not entry.get("is_unanswered"):
                    continue
                results.append(entry)
                if len(results) >= limit:
                    break
            return results

    def get_summary(self) -> Dict[str, Any]:
        """Compute aggregated statistics using SQLite when configured, else fall back to JSON logic."""
        if getattr(self, "storage_type", "json") == "sqlite":
            # Use SQL aggregates for efficiency
            summary = {
                "total_queries": 0,
                "answered_count": 0,
                "unanswered_count": 0,
                "clarification_count": 0,
                "success_rate_percent": 0.0,
                "average_latency_sec": 0.0,
                "average_top_score": 0.0,
                "query_type_distribution": {"factual": 0, "procedural": 0, "comparative": 0, "ambiguous": 0},
                "confidence_distribution": {"High": 0, "Medium": 0, "Low": 0, "None": 0},
                "domain_access_frequency": {},
                "top_recurring_themes": [],
            }
            with self.lock:
                cur = self.conn.cursor()
                cur.execute("SELECT COUNT(*) FROM queries")
                total = cur.fetchone()[0]
                if total == 0:
                    return summary
                summary["total_queries"] = total

                # Answered vs unanswered vs clarification
                cur.execute("SELECT COUNT(*) FROM queries WHERE status = 'clarification_required'")
                summary["clarification_count"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM queries WHERE is_unanswered = 1")
                summary["unanswered_count"] = cur.fetchone()[0]
                summary["answered_count"] = total - summary["clarification_count"] - summary["unanswered_count"]

                # Success rate (answered / total)
                summary["success_rate_percent"] = round((summary["answered_count"] / total) * 100, 1)

                # Average latency and top score
                cur.execute("SELECT AVG(duration_sec), AVG(top_similarity_score) FROM queries")
                avg_latency, avg_score = cur.fetchone()
                summary["average_latency_sec"] = round(avg_latency or 0.0, 3)
                summary["average_top_score"] = round(avg_score or 0.0, 3)

                # Query type distribution
                cur.execute("SELECT query_type, COUNT(*) FROM queries GROUP BY query_type")
                for qtype, cnt in cur.fetchall():
                    summary["query_type_distribution"][qtype.lower()] = cnt

                # Confidence distribution
                cur.execute("SELECT confidence, COUNT(*) FROM queries GROUP BY confidence")
                for conf, cnt in cur.fetchall():
                    summary["confidence_distribution"][conf] = cnt

                # Domain (source_documents) frequency – we need to expand JSON array strings
                cur.execute("SELECT source_documents FROM queries")
                domain_counts = {}
                for (src_json,) in cur.fetchall():
                    try:
                        src_list = json.loads(src_json)
                    except Exception:
                        src_list = []
                    for d in src_list:
                        domain_counts[d] = domain_counts.get(d, 0) + 1
                # Take top 6
                summary["domain_access_frequency"] = dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:6])

                # Top recurring themes – simple word frequency from queries
                cur.execute("SELECT query FROM queries")
                words_freq = {}
                stopwords = {"what","is","are","the","a","an","how","do","i","to","for","in","of","and","or","about","tell","me","does","can","you","explain","between","difference","compare","this","that","it"}
                for (qtext,) in cur.fetchall():
                    for w in re.findall(r"\b[a-zA-Z]{4,}\b", qtext.lower()):
                        if w not in stopwords:
                            words_freq[w] = words_freq.get(w, 0) + 1
                top_themes = sorted(words_freq.items(), key=lambda x: x[1], reverse=True)[:8]
                summary["top_recurring_themes"] = [{"theme": t, "count": c} for t, c in top_themes]
            return summary
        else:
            # Existing JSON implementation (unchanged from earlier lines 141‑229)
            # We'll call the original logic by delegating to a helper method to avoid duplication.
            return self._get_summary_json()

    def _get_summary_json(self) -> Dict[str, Any]:
        """Original JSON‑based summary implementation (extracted from existing code)."""
        with self.lock:
            logs = self._read_logs()
        total = len(logs)
        if total == 0:
            return {
                "total_queries": 0,
                "answered_count": 0,
                "unanswered_count": 0,
                "clarification_count": 0,
                "success_rate_percent": 0.0,
                "average_latency_sec": 0.0,
                "average_top_score": 0.0,
                "query_type_distribution": {"factual": 0, "procedural": 0, "comparative": 0, "ambiguous": 0},
                "confidence_distribution": {"High": 0, "Medium": 0, "Low": 0, "None": 0},
                "domain_access_frequency": {},
                "top_recurring_themes": [],
            }
        q_types = {"factual": 0, "procedural": 0, "comparative": 0, "ambiguous": 0}
        conf_dist = {"High": 0, "Medium": 0, "Low": 0, "None": 0}
        domain_counts = {}
        answered_count = 0
        unanswered_count = 0
        clarification_count = 0
        total_latency = 0.0
        total_score = 0.0
        words_frequency = {}
        stopwords = {"what", "is", "are", "the", "a", "an", "how", "do", "i", "to", "for", "in", "of", "and", "or", "about", "tell", "me", "does", "can", "you", "explain", "between", "difference", "compare", "this", "that", "it"}
        for entry in logs:
            qt = entry.get("query_type", "factual").lower()
            q_types[qt] = q_types.get(qt, 0) + 1
            c = entry.get("confidence", "None")
            conf_dist[c] = conf_dist.get(c, 0) + 1
            status = entry.get("status", "answered")
            if status == "clarification_required":
                clarification_count += 1
            elif entry.get("is_unanswered"):
                unanswered_count += 1
            else:
                answered_count += 1
            total_latency += entry.get("duration_sec", 0.0)
            total_score += entry.get("top_similarity_score", 0.0)
            for d in entry.get("source_documents", []):
                domain_counts[d] = domain_counts.get(d, 0) + 1
            q_text = entry.get("query", "").lower()
            for w in re.findall(r"\b[a-zA-Z]{4,}\b", q_text):
                if w not in stopwords:
                    words_frequency[w] = words_frequency.get(w, 0) + 1
        top_themes = sorted(words_frequency.items(), key=lambda x: x[1], reverse=True)[:8]
        return {
            "total_queries": total,
            "answered_count": answered_count,
            "unanswered_count": unanswered_count,
            "clarification_count": clarification_count,
            "success_rate_percent": round((answered_count / total) * 100, 1),
            "average_latency_sec": round(total_latency / total, 3),
            "average_top_score": round(total_score / total, 3),
            "query_type_distribution": q_types,
            "confidence_distribution": conf_dist,
            "domain_access_frequency": dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:6]),
            "top_recurring_themes": [{"theme": t, "count": c} for t, c in top_themes],
        }

    def clear(self):
        """Reset analytics storage – clears SQLite table or JSON file based on configuration."""
        if getattr(self, "storage_type", "json") == "sqlite":
            with self.lock:
                cur = self.conn.cursor()
                cur.execute("DELETE FROM queries")
                self.conn.commit()
        else:
            with self.lock:
                self._write_logs([])

    def export_csv(self) -> str:
        """Export analytics data to CSV using the active storage backend."""
        import csv
        import io
        fieldnames = [
            "id", "date_str", "query", "resolved_query", "query_type",
            "route", "confidence", "status", "top_similarity_score",
            "retrieved_chunks_count", "source_documents", "duration_sec", "is_unanswered"
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        if getattr(self, "storage_type", "json") == "sqlite":
            with self.lock:
                cur = self.conn.cursor()
                cur.execute("SELECT * FROM queries")
                col_names = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
            for row in rows:
                row_dict = dict(zip(col_names, row))
                # Decode source_documents JSON string
                if isinstance(row_dict.get("source_documents"), str):
                    try:
                        row_dict["source_documents"] = "; ".join(json.loads(row_dict["source_documents"]))
                    except Exception:
                        row_dict["source_documents"] = ""
                else:
                    row_dict["source_documents"] = ""
                writer.writerow(row_dict)
        else:
            with self.lock:
                logs = self._read_logs()
            for entry in logs:
                row = dict(entry)
                row["source_documents"] = "; ".join(row.get("source_documents", []))
                writer.writerow(row)
        return output.getvalue()

    def _read_logs(self) -> List[Dict[str, Any]]:
        """Reads JSON logs safely."""
        try:
            if self.logs_file.exists():
                with open(self.logs_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _write_logs(self, logs: List[Dict[str, Any]]):
        """Writes JSON logs atomically."""
        try:
            tmp_file = self.logs_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
            if tmp_file.exists():
                tmp_file.replace(self.logs_file)
        except Exception as e:
            print(f"[ANALYTICS ERROR] Failed to write analytics: {e}")
