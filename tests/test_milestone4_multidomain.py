"""
test_milestone4_multidomain.py
Milestone 4: Multi-Domain Knowledge Base Validation, Query Analytics,
Knowledge Gap Detection, and API Verification Suite.
"""

import unittest
import tempfile
import shutil
import json
import csv
import io
from pathlib import Path

from backend.analytics_engine import AnalyticsEngine
from backend.knowledge_gap_detector import KnowledgeGapDetector
from backend.chunker import DocumentChunker, DocumentChunk
from backend.embeddings import EmbeddingEngine
from backend.vector_store import VectorStore
from backend.retriever import KnowledgeRetriever
from backend.generator import ResponseGenerator
from backend.query_understanding_agent import QueryUnderstandingAgent
from backend.retrieval_agent import RetrievalAgent
from backend.response_generation_agent import ResponseGenerationAgent
from backend.clarification_agent import ClarificationAgent
from backend.conversation_manager import ConversationManager
from backend.orchestrator import MultiAgentOrchestrator
from app import app


class TestAnalyticsEngine(unittest.TestCase):
    """Validates the Query Analytics Engine."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.analytics = AnalyticsEngine(storage_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_and_get_logs(self):
        """Ensure query events are recorded with proper fields."""
        entry = self.analytics.record_query(
            query="What is virtual memory?",
            query_type="factual",
            route="retrieval",
            confidence="High",
            status="answered",
            top_similarity_score=0.88,
            retrieved_chunks_count=3,
            sources=[{"document_name": "os_intro.pdf", "page_number": 1}],
            duration_sec=0.15,
        )
        self.assertIsNotNone(entry["id"])
        self.assertEqual(entry["query"], "What is virtual memory?")
        self.assertEqual(entry["confidence"], "High")
        self.assertEqual(entry["source_documents"], ["os_intro.pdf"])

        logs = self.analytics.get_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["id"], entry["id"])

    def test_filtering_logs(self):
        """Test filtering by status, confidence, and unanswered status."""
        self.analytics.record_query("Q1", "factual", "retrieval", "High", "answered", 0.9, 2)
        self.analytics.record_query("Q2", "ambiguous", "clarification", "None", "clarification_required", 0.0, 0)
        self.analytics.record_query("Q3", "procedural", "retrieval", "Low", "no_results", 0.1, 0)

        high_logs = self.analytics.get_logs(confidence="High")
        self.assertEqual(len(high_logs), 1)
        self.assertEqual(high_logs[0]["query"], "Q1")

        clarify_logs = self.analytics.get_logs(status="clarification_required")
        self.assertEqual(len(clarify_logs), 1)
        self.assertEqual(clarify_logs[0]["query"], "Q2")

        unanswered = self.analytics.get_logs(unanswered_only=True)
        self.assertEqual(len(unanswered), 1)
        self.assertEqual(unanswered[0]["query"], "Q3")

    def test_summary_metrics(self):
        """Verify aggregated summary metrics calculation."""
        self.analytics.record_query("What is paging in operating systems?", "factual", "retrieval", "High", "answered", 0.85, 2, [{"document_name": "os.pdf"}], 0.10)
        self.analytics.record_query("How to configure OSPF routing protocol?", "procedural", "retrieval", "High", "answered", 0.82, 3, [{"document_name": "networks.pdf"}], 0.12)
        self.analytics.record_query("Compare AI and ML models", "comparative", "retrieval", "Medium", "answered", 0.70, 2, [{"document_name": "ai.docx"}], 0.08)
        self.analytics.record_query("Tell me about recipes", "factual", "retrieval", "None", "no_results", 0.12, 0, [], 0.05)

        summary = self.analytics.get_summary()
        self.assertEqual(summary["total_queries"], 4)
        self.assertEqual(summary["answered_count"], 3)
        self.assertEqual(summary["unanswered_count"], 1)
        self.assertEqual(summary["success_rate_percent"], 75.0)
        self.assertIn("os.pdf", summary["domain_access_frequency"])
        self.assertIn("networks.pdf", summary["domain_access_frequency"])

    def test_export_csv(self):
        """Verify CSV export format and contents."""
        self.analytics.record_query("What is TCP?", "factual", "retrieval", "High", "answered", 0.88, 2, [{"document_name": "net.pdf"}])
        csv_str = self.analytics.export_csv()
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 2)
        headers = rows[0]
        self.assertIn("query", headers)
        self.assertIn("confidence", headers)
        self.assertIn("top_similarity_score", headers)
        self.assertEqual(rows[1][headers.index("query")], "What is TCP?")

    def test_clear_logs(self):
        """Verify clearing logs empties the storage."""
        self.analytics.record_query("Test query", "factual", "retrieval", "High", "answered")
        self.assertEqual(len(self.analytics.get_logs()), 1)
        self.analytics.clear()
        self.assertEqual(len(self.analytics.get_logs()), 0)


class TestKnowledgeGapDetector(unittest.TestCase):
    """Validates clustering and recommendation generation for knowledge gaps."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.analytics = AnalyticsEngine(storage_dir=self.temp_dir)
        self.detector = KnowledgeGapDetector(self.analytics)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_gaps_when_all_answered_well(self):
        """High confidence queries should yield no detected gaps."""
        self.analytics.record_query("What is virtual memory?", "factual", "retrieval", "High", "answered", 0.90, 2)
        gaps = self.detector.detect_gaps()
        self.assertEqual(len(gaps), 0)

    def test_detect_and_cluster_gaps(self):
        """Low-confidence/no_results queries on similar topics should cluster together."""
        self.analytics.record_query("Explain quantum entanglement", "factual", "retrieval", "None", "no_results", 0.10, 0)
        self.analytics.record_query("How does quantum cryptography work?", "procedural", "retrieval", "Low", "no_results", 0.15, 0)
        self.analytics.record_query("Tell me about quantum computing algorithms", "factual", "retrieval", "None", "no_results", 0.12, 0)

        gaps = self.detector.detect_gaps()
        self.assertGreaterEqual(len(gaps), 1)
        quantum_gap = next((g for g in gaps if "Quantum" in g["topic"]), None)
        self.assertIsNotNone(quantum_gap)
        self.assertEqual(quantum_gap["frequency"], 3)
        self.assertEqual(quantum_gap["severity"], "High")
        self.assertIn("quantum", quantum_gap["recommendation"].lower())
        self.assertEqual(len(quantum_gap["sample_queries"]), 3)


class TestMultiDomainPipeline(unittest.TestCase):
    """End-to-end multi-agent evaluation across 4 distinct knowledge domains."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.analytics_dir = Path(cls.temp_dir) / "analytics"
        cls.vector_dir = Path(cls.temp_dir) / "vectors"
        cls.analytics_dir.mkdir(parents=True, exist_ok=True)
        cls.vector_dir.mkdir(parents=True, exist_ok=True)

        cls.embedding_engine = EmbeddingEngine()
        cls.vector_store = VectorStore(persist_dir=str(cls.vector_dir), dimension=cls.embedding_engine.dimension)
        cls.retriever = KnowledgeRetriever(
            vector_store=cls.vector_store,
            embedding_engine=cls.embedding_engine,
            top_k=3,
            similarity_threshold=0.25,
        )
        cls.generator = ResponseGenerator()
        cls.analytics_engine = AnalyticsEngine(storage_dir=str(cls.analytics_dir))
        cls.conversation_manager = ConversationManager()

        cls.orchestrator = MultiAgentOrchestrator(
            query_understanding_agent=QueryUnderstandingAgent(),
            retrieval_agent=RetrievalAgent(retriever=cls.retriever),
            response_generation_agent=ResponseGenerationAgent(generator=cls.generator),
            clarification_agent=ClarificationAgent(),
            conversation_manager=cls.conversation_manager,
            analytics_engine=cls.analytics_engine,
        )

        # Ingest 4 distinct domains:
        # Domain 1: Operating Systems
        os_chunks = [
            DocumentChunk(
                chunk_id="os_chunk_1",
                document_name="Operating_Systems.pdf",
                document_type="PDF",
                text="Virtual memory is a memory management capability that provides an idealized abstraction of storage resources. Paging is used to divide memory into fixed-size frames and pages.",
                page_number=1,
            ),
            DocumentChunk(
                chunk_id="os_chunk_2",
                document_name="Operating_Systems.pdf",
                document_type="PDF",
                text="CPU scheduling algorithms include Round Robin, Shortest Job First, and Priority Scheduling. Deadlock occurs when processes hold resources and wait for others.",
                page_number=2,
            ),
        ]

        # Domain 2: Artificial Intelligence
        ai_chunks = [
            DocumentChunk(
                chunk_id="ai_chunk_1",
                document_name="Artificial_Intelligence.docx",
                document_type="DOCX",
                text="Deep learning employs multi-layered artificial neural networks. Transformer models utilize self-attention mechanisms to weigh the significance of different tokens in sequential data.",
                page_number=1,
            ),
            DocumentChunk(
                chunk_id="ai_chunk_2",
                document_name="Artificial_Intelligence.docx",
                document_type="DOCX",
                text="Supervised learning learns a function from labeled training data. Reinforcement learning trains agents to maximize cumulative rewards through environmental interactions.",
                page_number=2,
            ),
        ]

        # Domain 3: Computer Networks
        net_chunks = [
            DocumentChunk(
                chunk_id="net_chunk_1",
                document_name="CSE3003_COMPUTER_NETWORKS.pdf",
                document_type="PDF",
                text="The OSI model consists of seven layers: Physical, Data Link, Network, Transport, Session, Presentation, and Application. TCP provides reliable connection-oriented transport.",
                page_number=1,
            ),
            DocumentChunk(
                chunk_id="net_chunk_2",
                document_name="CSE3003_COMPUTER_NETWORKS.pdf",
                document_type="PDF",
                text="Network topologies include Star, Mesh, Bus, and Ring. In a Star topology, all nodes connect to a central hub or switch.",
                page_number=2,
            ),
        ]

        # Domain 4: Tabular Student Database
        csv_chunks = [
            DocumentChunk(
                chunk_id="csv_chunk_1",
                document_name="students.csv",
                document_type="CSV",
                text="Student ID: S101 | Name: Alice Walker | Department: Computer Science | GPA: 3.92 | Status: Enrolled",
                page_number=1,
            ),
            DocumentChunk(
                chunk_id="csv_chunk_2",
                document_name="students.csv",
                document_type="CSV",
                text="Student ID: S102 | Name: Bob Martinez | Department: Information Technology | GPA: 3.75 | Status: Graduated",
                page_number=1,
            ),
        ]

        all_chunks = os_chunks + ai_chunks + net_chunks + csv_chunks
        texts = [c.text for c in all_chunks]
        embeddings = cls.embedding_engine.generate_embeddings(texts)
        cls.vector_store.add_documents(all_chunks, embeddings)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_domain_1_os_retrieval(self):
        """Querying OS concepts retrieves from Operating_Systems.pdf with High confidence."""
        res = self.orchestrator.process_query("What is virtual memory and paging?")
        self.assertEqual(res["status"], "success")
        self.assertIn(res["confidence"], ["High", "Medium"])
        self.assertTrue(any("Operating_Systems" in s["document_name"] for s in res["sources"]))
        self.assertIn("virtual memory", res["answer"].lower())

    def test_domain_2_ai_retrieval(self):
        """Querying AI concepts retrieves from Artificial_Intelligence.docx."""
        res = self.orchestrator.process_query("How do transformer models and attention work?")
        self.assertEqual(res["status"], "success")
        self.assertIn(res["confidence"], ["High", "Medium"])
        self.assertTrue(any("Artificial_Intelligence" in s["document_name"] for s in res["sources"]))
        self.assertIn("attention", res["answer"].lower())

    def test_domain_3_networks_retrieval(self):
        """Querying Networks concepts retrieves from CSE3003_COMPUTER_NETWORKS.pdf."""
        res = self.orchestrator.process_query("Explain star topology and the OSI model.")
        self.assertEqual(res["status"], "success")
        self.assertIn(res["confidence"], ["High", "Medium"])
        self.assertTrue(any("CSE3003" in s["document_name"] for s in res["sources"]))
        self.assertIn("osi", res["answer"].lower())

    def test_domain_4_csv_tabular_retrieval(self):
        """Querying Tabular CSV records retrieves from students.csv."""
        res = self.orchestrator.process_query("What is Alice Walker's GPA and department?")
        self.assertEqual(res["status"], "success")
        self.assertTrue(any("students.csv" in s["document_name"] for s in res["sources"]))
        self.assertIn("3.92", res["answer"])

    def test_cross_domain_multi_turn_switching(self):
        """Validates that consecutive queries can seamlessly switch across domains."""
        conv_id = "cross_domain_test"
        # Turn 1: OS
        r1 = self.orchestrator.process_query("Tell me about CPU scheduling", conv_id=conv_id)
        self.assertTrue(any("Operating_Systems" in s["document_name"] for s in r1["sources"]))

        # Turn 2: Networks
        r2 = self.orchestrator.process_query("What does TCP do?", conv_id=conv_id)
        self.assertTrue(any("CSE3003" in s["document_name"] for s in r2["sources"]))

        # Turn 3: AI
        r3 = self.orchestrator.process_query("Explain reinforcement learning", conv_id=conv_id)
        self.assertTrue(any("Artificial_Intelligence" in s["document_name"] for s in r3["sources"]))

    def test_out_of_domain_query_triggers_gap_recording(self):
        """Unrelated query produces grounded refusal and is captured by AnalyticsEngine."""
        res = self.orchestrator.process_query("What is the recipe for baking chocolate brownies?")
        self.assertIn(res["confidence"], ["Low", "None"])
        self.assertEqual(len(res["sources"]), 0)

        # Check telemetry
        logs = self.analytics_engine.get_logs(limit=5)
        latest = logs[0]
        self.assertEqual(latest["query"], "What is the recipe for baking chocolate brownies?")
        self.assertTrue(latest["is_unanswered"])


class TestAnalyticsAPIEndpoints(unittest.TestCase):
    """Integration test suite for Flask REST API analytics routes."""

    def setUp(self):
        self.client = app.test_client()

    def test_analytics_summary_endpoint(self):
        """GET /analytics/summary returns 200 and expected schema."""
        res = self.client.get("/analytics/summary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_queries", data)
        self.assertIn("success_rate_percent", data)
        self.assertIn("query_type_distribution", data)
        self.assertIn("confidence_distribution", data)

    def test_analytics_gaps_endpoint(self):
        """GET /analytics/gaps returns 200 and gaps list."""
        res = self.client.get("/analytics/gaps")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("gaps", data)
        self.assertIn("total_gaps", data)

    def test_analytics_queries_endpoint(self):
        """GET /analytics/queries returns 200 and logs."""
        res = self.client.get("/analytics/queries?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("logs", data)

    def test_analytics_export_endpoint(self):
        """GET /analytics/export returns CSV file."""
        res = self.client.get("/analytics/export")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/csv")
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))

    def test_analytics_clear_endpoint(self):
        """POST /analytics/clear returns 200 success."""
        res = self.client.post("/analytics/clear")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))


if __name__ == "__main__":
    unittest.main()
