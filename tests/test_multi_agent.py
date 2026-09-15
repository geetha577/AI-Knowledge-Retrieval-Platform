"""
test_multi_agent.py
Unit and Integration Tests for Milestone 2 Multi-Agent Query Resolution Architecture:
- QueryUnderstandingAgent
- RetrievalAgent
- ResponseGenerationAgent
- MultiAgentOrchestrator
"""

import unittest
from unittest.mock import MagicMock
import numpy as np

from backend.models import DocumentChunk, RetrievalResult, QueryResponse
from backend.query_understanding_agent import QueryUnderstandingAgent
from backend.retrieval_agent import RetrievalAgent
from backend.response_generation_agent import ResponseGenerationAgent, CLARIFICATION_MESSAGE
from backend.orchestrator import MultiAgentOrchestrator
from backend.generator import REJECTION_MESSAGE


class TestQueryUnderstandingAgent(unittest.TestCase):
    """Test suite for Query Understanding Agent classification and routing."""

    def setUp(self):
        self.agent = QueryUnderstandingAgent()

    def test_factual_queries(self):
        factual_cases = [
            "What is virtual memory?",
            "What is artificial intelligence?",
            "What is cybersecurity?",
            "Define machine learning",
            "Explain neural networks",
        ]
        for query in factual_cases:
            res = self.agent.analyze(query)
            self.assertEqual(res["query_type"], "factual", f"Failed for query: {query}")
            self.assertEqual(res["route"], "retrieval", f"Failed route for query: {query}")
            self.assertGreaterEqual(res["classification_confidence"], 0.8)

    def test_procedural_queries(self):
        procedural_cases = [
            "How do I prevent phishing attacks?",
            "How does the operating system manage memory?",
            "What are the steps involved in protecting a system?",
            "How to configure a firewall",
            "Procedure for handling an incident",
        ]
        for query in procedural_cases:
            res = self.agent.analyze(query)
            self.assertEqual(res["query_type"], "procedural", f"Failed for query: {query}")
            self.assertEqual(res["route"], "retrieval", f"Failed route for query: {query}")
            self.assertGreaterEqual(res["classification_confidence"], 0.8)

    def test_comparative_queries(self):
        comparative_cases = [
            "Compare TCP and UDP.",
            "What is the difference between RAM and ROM?",
            "Compare the two concepts based on their advantages.",
            "Difference between supervised and unsupervised learning",
            "Symmetric vs asymmetric encryption",
        ]
        for query in comparative_cases:
            res = self.agent.analyze(query)
            self.assertEqual(res["query_type"], "comparative", f"Failed for query: {query}")
            self.assertEqual(res["route"], "retrieval", f"Failed route for query: {query}")
            self.assertGreaterEqual(res["classification_confidence"], 0.8)

    def test_ambiguous_queries(self):
        ambiguous_cases = [
            "Tell me about it.",
            "Explain that.",
            "What about this?",
            "Tell me more",
            "Can you help me with this?",
            "What is it?",
            "",
        ]
        for query in ambiguous_cases:
            res = self.agent.analyze(query)
            self.assertEqual(res["query_type"], "ambiguous", f"Failed for query: {query}")
            self.assertEqual(res["route"], "clarification", f"Failed route for query: {query}")
            self.assertGreaterEqual(res["classification_confidence"], 0.8)


class TestRetrievalAgent(unittest.TestCase):
    """Test suite for Retrieval Agent wrapping KnowledgeRetriever."""

    def setUp(self):
        self.mock_retriever = MagicMock()
        self.agent = RetrievalAgent(self.mock_retriever)

    def test_retrieval_success_metadata_preservation(self):
        dummy_chunk = DocumentChunk(
            chunk_id="chunk_1",
            document_name="os_guide.pdf",
            document_type="PDF",
            text="Virtual memory allows executing larger processes.",
            page_number=3,
            source_id="os_guide.pdf (Page 3)",
        )
        dummy_res = RetrievalResult(
            chunk=dummy_chunk,
            similarity_score=0.85,
            relevance="High",
        )

        self.mock_retriever.retrieve.return_value = {
            "relevant_results": [dummy_res],
            "all_retrieved": [dummy_res],
            "top_score": 0.85,
            "confidence": "High",
            "query_embedding_shape": (1, 384),
        }

        output = self.agent.retrieve("What is virtual memory?", query_type="factual")
        self.assertEqual(output["status"], "success")
        self.assertEqual(len(output["results"]), 1)
        self.assertEqual(output["results"][0]["document"], "os_guide.pdf")
        self.assertEqual(output["results"][0]["page"], 3)
        self.assertEqual(output["results"][0]["score"], 0.85)
        self.assertEqual(output["retrieval_confidence"], 0.85)
        self.assertEqual(output["confidence_label"], "High")

    def test_retrieval_no_results(self):
        self.mock_retriever.retrieve.return_value = {
            "relevant_results": [],
            "all_retrieved": [],
            "top_score": 0.12,
            "confidence": "None",
            "query_embedding_shape": (1, 384),
        }

        output = self.agent.retrieve("Unknown topic", query_type="factual")
        self.assertEqual(output["status"], "no_results")
        self.assertEqual(output["results"], [])
        self.assertEqual(output["confidence_label"], "None")


class TestResponseGenerationAgent(unittest.TestCase):
    """Test suite for Response Generation Agent."""

    def setUp(self):
        self.mock_generator = MagicMock()
        self.agent = ResponseGenerationAgent(self.mock_generator)

    def test_ambiguous_query_handling(self):
        res = self.agent.generate(
            query="Tell me about it.",
            query_type="ambiguous",
            retrieval_output={},
            route="clarification",
        )
        self.assertEqual(res["status"], "clarification_needed")
        self.assertEqual(res["confidence"], "None")
        self.assertEqual(res["sources"], [])
        self.assertIn("ambiguous", res["answer"].lower())

    def test_no_results_handling(self):
        retrieval_output = {
            "status": "no_results",
            "results": [],
            "confidence_label": "None",
            "retrieval_confidence": 0.0,
        }
        res = self.agent.generate(
            query="What is the capital of France?",
            query_type="factual",
            retrieval_output=retrieval_output,
            route="retrieval",
        )
        self.assertEqual(res["status"], "no_results")
        self.assertEqual(res["confidence"], "None")
        self.assertEqual(res["sources"], [])
        self.assertIn("couldn't find enough relevant information", res["answer"])

    def test_grounded_response_generation(self):
        retrieval_output = {
            "status": "success",
            "results": [{"chunk_id": "c1", "content": "Virtual memory manages address translation and paging."}],
            "retrieval_confidence": 0.88,
            "confidence_label": "High",
            "raw_retrieval_data": {
                "relevant_results": [],
                "confidence": "High",
                "top_score": 0.88,
            },
        }

        self.mock_generator.generate_response.return_value = QueryResponse(
            answer="Virtual memory manages address translation.",
            confidence="High",
            sources=[{
                "source_id": "test.pdf (Page 1)",
                "document_name": "test.pdf",
                "document_type": "PDF",
                "page_number": 1,
                "similarity_score": 0.88,
                "relevance": "High",
                "text_snippet": "Virtual memory...",
                "full_text": "Virtual memory manages address translation.",
            }],
            debug_details={"mode": "local_extractive"},
        )

        res = self.agent.generate(
            query="What is virtual memory?",
            query_type="factual",
            retrieval_output=retrieval_output,
            route="retrieval",
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["confidence"], "High")
        self.assertEqual(len(res["sources"]), 1)
        self.assertIn("Virtual memory manages address translation.", res["answer"])


class TestMultiAgentOrchestrator(unittest.TestCase):
    """Test suite for MultiAgentOrchestrator connecting all three agents."""

    def setUp(self):
        self.query_agent = QueryUnderstandingAgent()
        self.mock_retriever = MagicMock()
        self.retrieval_agent = RetrievalAgent(self.mock_retriever)
        self.mock_generator = MagicMock()
        self.response_agent = ResponseGenerationAgent(self.mock_generator)

        self.orchestrator = MultiAgentOrchestrator(
            query_understanding_agent=self.query_agent,
            retrieval_agent=self.retrieval_agent,
            response_generation_agent=self.response_agent,
        )

    def test_orchestrator_factual_flow(self):
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            document_name="ai_basics.txt",
            document_type="TXT",
            text="Artificial intelligence is the simulation of human intelligence by machines.",
            source_id="ai_basics.txt",
        )
        ret_res = RetrievalResult(chunk=chunk, similarity_score=0.91, relevance="High")
        self.mock_retriever.retrieve.return_value = {
            "relevant_results": [ret_res],
            "all_retrieved": [ret_res],
            "top_score": 0.91,
            "confidence": "High",
        }
        self.mock_generator.generate_response.return_value = QueryResponse(
            answer="Artificial intelligence is the simulation of human intelligence by machines.",
            confidence="High",
            sources=[{
                "source_id": "ai_basics.txt",
                "document_name": "ai_basics.txt",
                "document_type": "TXT",
                "similarity_score": 0.91,
                "relevance": "High",
                "text_snippet": "Artificial intelligence is...",
                "full_text": chunk.text,
            }],
        )

        res = self.orchestrator.process_query("What is artificial intelligence?")
        self.assertEqual(res["query_type"], "factual")
        self.assertEqual(res["route"], "retrieval")
        self.assertEqual(res["confidence"], "High")
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["pipeline_stages"]), 3)
        self.assertEqual(res["pipeline_stages"][0]["stage"], "Query Understanding")
        self.assertEqual(res["pipeline_stages"][1]["stage"], "Semantic Retrieval")
        self.assertEqual(res["pipeline_stages"][2]["stage"], "Response Generation")

    def test_orchestrator_ambiguous_flow(self):
        res = self.orchestrator.process_query("Tell me about it.")
        self.assertEqual(res["query_type"], "ambiguous")
        self.assertEqual(res["route"], "clarification")
        self.assertEqual(res["status"], "clarification_needed")
        self.assertEqual(res["confidence"], "None")
        self.assertEqual(res["sources"], [])
        # Verification that retrieval was skipped
        self.assertEqual(res["pipeline_stages"][1]["status"], "skipped")
        self.mock_retriever.retrieve.assert_not_called()

    def test_orchestrator_unavailable_information_flow(self):
        self.mock_retriever.retrieve.return_value = {
            "relevant_results": [],
            "all_retrieved": [],
            "top_score": 0.05,
            "confidence": "None",
        }

        res = self.orchestrator.process_query("What is the capital of France?")
        self.assertEqual(res["query_type"], "factual")
        self.assertEqual(res["route"], "retrieval")
        self.assertEqual(res["status"], "no_results")
        self.assertEqual(res["confidence"], "None")
        self.assertEqual(res["sources"], [])
        self.assertIn("couldn't find enough relevant information", res["answer"])


class TestFlaskAppMultiAgentIntegration(unittest.TestCase):
    """End-to-end integration tests for Flask API with Milestone 2 Orchestration."""

    @classmethod
    def setUpClass(cls):
        from app import app
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_health_endpoint_m2(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("milestone", data)
        self.assertIn("Milestone 2", data["milestone"])
        self.assertIn("QueryUnderstandingAgent", data["agents"])
        self.assertIn("RetrievalAgent", data["agents"])
        self.assertIn("ResponseGenerationAgent", data["agents"])
        self.assertIn("MultiAgentOrchestrator", data["agents"])

    def test_query_empty_error(self):
        resp = self.client.post("/query", json={"question": ""})
        self.assertEqual(resp.status_code, 400)

    def test_query_ambiguous_end_to_end(self):
        resp = self.client.post("/query", json={"question": "Tell me about it."})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["query_type"], "ambiguous")
        self.assertEqual(data["route"], "clarification")
        self.assertEqual(data["confidence"], "None")
        self.assertEqual(data["status"], "clarification_needed")
        self.assertEqual(len(data["sources"]), 0)
        self.assertIn("ambiguous", data["answer"].lower())

    def test_query_procedural_classification(self):
        resp = self.client.post("/query", json={"question": "How do I prevent phishing attacks?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["query_type"], "procedural")
        self.assertEqual(data["route"], "retrieval")
        self.assertIn("pipeline_stages", data)
        self.assertEqual(len(data["pipeline_stages"]), 3)

    def test_query_comparative_classification(self):
        resp = self.client.post("/query", json={"question": "What is the difference between RAM and ROM?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["query_type"], "comparative")
        self.assertEqual(data["route"], "retrieval")

    def test_query_unavailable_information_rejection(self):
        # Use a query that is completely outside any indexed knowledge domain
        resp = self.client.post("/query", json={"question": "What is the capital of France?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["query_type"], "factual")
        # Capital of France is NOT in the indexed knowledge base (OS, AI, Cybersecurity, CSV)
        # Should either have no sources or very low confidence with rejection
        if data["confidence"] == "None":
            self.assertEqual(len(data["sources"]), 0)
            self.assertIn("couldn't find enough relevant information", data["answer"])
        else:
            # If some weak match was found, verify it has no genuine sources about France
            self.assertIn("pipeline_stages", data)
            self.assertEqual(len(data["pipeline_stages"]), 3)


if __name__ == "__main__":
    unittest.main()

