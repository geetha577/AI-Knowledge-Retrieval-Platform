"""
test_clarification.py
Milestone 3 Test Suite: Ambiguity Detection, Clarification Agent,
Conversation State Management, and Multi-turn Clarification Flow.
"""

import unittest
from unittest.mock import MagicMock
from backend.query_understanding_agent import QueryUnderstandingAgent
from backend.clarification_agent import ClarificationAgent
from backend.conversation_manager import ConversationManager
from backend.orchestrator import MultiAgentOrchestrator
from backend.retrieval_agent import RetrievalAgent
from backend.response_generation_agent import ResponseGenerationAgent
from backend.models import DocumentChunk, RetrievalResult, QueryResponse


class TestAmbiguityDetection(unittest.TestCase):
    """Verifies that QueryUnderstandingAgent accurately distinguishes ambiguous vs non-ambiguous queries."""

    def setUp(self):
        self.agent = QueryUnderstandingAgent()

    def test_underspecified_application_queries(self):
        queries = [
            "What is the application process?",
            "How do I apply?",
            "Tell me about the application process",
            "What is the application procedure?",
        ]
        for q in queries:
            with self.subTest(query=q):
                res = self.agent.analyze(q)
                self.assertEqual(res["query_type"], "ambiguous")
                self.assertEqual(res["route"], "clarification")

    def test_underspecified_requirements_queries(self):
        queries = [
            "Tell me about the requirements.",
            "What are the requirements?",
            "What is the eligibility criteria?",
            "What are the prerequisites?",
        ]
        for q in queries:
            with self.subTest(query=q):
                res = self.agent.analyze(q)
                self.assertEqual(res["query_type"], "ambiguous")
                self.assertEqual(res["route"], "clarification")

    def test_pronoun_ambiguous_queries(self):
        queries = [
            "Tell me about it.",
            "Explain that",
            "What about this?",
            "Can you explain it?",
        ]
        for q in queries:
            with self.subTest(query=q):
                res = self.agent.analyze(q)
                self.assertEqual(res["query_type"], "ambiguous")
                self.assertEqual(res["route"], "clarification")

    def test_substantive_non_ambiguous_queries_preserved(self):
        non_ambiguous = [
            ("What is virtual memory?", "factual"),
            ("How do I prevent phishing attacks?", "procedural"),
            ("What is the difference between RAM and ROM?", "comparative"),
            ("What are the students in CSE?", "factual"),
        ]
        for q, expected_type in non_ambiguous:
            with self.subTest(query=q):
                res = self.agent.analyze(q)
                self.assertEqual(res["query_type"], expected_type)
                self.assertEqual(res["route"], "retrieval")


class TestClarificationAgent(unittest.TestCase):
    """Verifies ClarificationAgent structured output, tailored questions, and suggestions."""

    def setUp(self):
        self.agent = ClarificationAgent(available_domains=["Operating_Systems.pdf", "Cybersecurity_Basics.txt"])

    def test_requirements_clarification(self):
        res = self.agent.generate_clarification("Tell me about the requirements.")
        self.assertTrue(res["needs_clarification"])
        self.assertIn("requirements", res["clarification_question"].lower())
        self.assertGreaterEqual(len(res["suggested_options"]), 2)
        self.assertIn("reason", res)

    def test_application_clarification(self):
        res = self.agent.generate_clarification("What is the application process?")
        self.assertTrue(res["needs_clarification"])
        self.assertIn("application", res["clarification_question"].lower())
        self.assertGreaterEqual(len(res["suggested_options"]), 2)

    def test_pronoun_clarification_suggestions(self):
        res = self.agent.generate_clarification("Tell me about it.")
        self.assertTrue(res["needs_clarification"])
        self.assertIn("specify", res["clarification_question"].lower())
        self.assertTrue(any("operating" in s.lower() or "cybersecurity" in s.lower() for s in res["suggested_options"]))


class TestConversationManager(unittest.TestCase):
    """Verifies conversation state tracking, turn limits, and intelligent context merging."""

    def setUp(self):
        self.manager = ConversationManager(max_clarification_turns=3)

    def test_start_and_get_session(self):
        sid = self.manager.start_session("What are the requirements?", "Which requirements?", ["Eligibility"])
        self.assertIsNotNone(sid)
        session = self.manager.get_session(sid)
        self.assertEqual(session["original_query"], "What are the requirements?")
        self.assertEqual(session["clarification_count"], 1)

    def test_query_merging_requirements(self):
        resolved = self.manager.resolve_query("What are the requirements?", "For eligibility")
        self.assertIn("eligibility", resolved.lower())
        self.assertIn("requirements", resolved.lower())
        self.assertTrue(resolved.endswith("?"))

    def test_query_merging_application_process(self):
        resolved = self.manager.resolve_query("What is the application process?", "internship")
        self.assertIn("internship", resolved.lower())
        self.assertIn("application process", resolved.lower())
        self.assertTrue(resolved.endswith("?"))

    def test_query_merging_pronoun_substitution(self):
        resolved = self.manager.resolve_query("Tell me about it.", "Virtual memory")
        self.assertIn("Virtual memory", resolved)
        self.assertNotIn(" it", resolved.lower())

    def test_query_merging_apply(self):
        resolved = self.manager.resolve_query("How do I apply?", "For the internship")
        self.assertIn("apply", resolved.lower())
        self.assertIn("internship", resolved.lower())


class TestOrchestratorClarificationFlow(unittest.TestCase):
    """Verifies multi-turn clarification resolution coordinated by MultiAgentOrchestrator."""

    def setUp(self):
        self.query_agent = QueryUnderstandingAgent()
        self.mock_retriever = MagicMock()
        self.retrieval_agent = RetrievalAgent(self.mock_retriever)
        self.mock_generator = MagicMock()
        self.response_agent = ResponseGenerationAgent(self.mock_generator)
        self.clarification_agent = ClarificationAgent()
        self.conversation_manager = ConversationManager(max_clarification_turns=2)

        self.orchestrator = MultiAgentOrchestrator(
            query_understanding_agent=self.query_agent,
            retrieval_agent=self.retrieval_agent,
            response_generation_agent=self.response_agent,
            clarification_agent=self.clarification_agent,
            conversation_manager=self.conversation_manager,
        )

    def test_ambiguous_query_triggers_clarification_session(self):
        res = self.orchestrator.process_query("What are the requirements?")
        self.assertEqual(res["status"], "clarification_required")
        self.assertEqual(res["query_type"], "ambiguous")
        self.assertIsNotNone(res["session_id"])
        self.assertIsNotNone(res["clarification_question"])
        self.assertGreaterEqual(len(res["suggested_options"]), 2)
        # Verification that retrieval was skipped
        self.mock_retriever.retrieve.assert_not_called()

    def test_clarification_response_resolves_and_retrieves(self):
        # Step 1: User asks ambiguous query
        step1 = self.orchestrator.process_query("What is the application process?")
        sid = step1["session_id"]
        self.assertEqual(step1["status"], "clarification_required")

        # Mock retrieval & generator for the resolved query
        chunk = DocumentChunk(
            chunk_id="c1",
            document_name="guide.pdf",
            document_type="PDF",
            text="Internship application process requires submitting online form.",
            page_number=1,
            source_id="guide.pdf (Page 1)",
        )
        ret_res = RetrievalResult(chunk=chunk, similarity_score=0.88, relevance="High")
        self.mock_retriever.retrieve.return_value = {
            "relevant_results": [ret_res],
            "all_retrieved": [ret_res],
            "top_score": 0.88,
            "confidence": "High",
        }
        self.mock_generator.generate_response.return_value = QueryResponse(
            answer="Submit the online application form and resume.",
            confidence="High",
            sources=[ret_res.to_dict()],
        )

        # Step 2: User clarifies "for the virtual internship"
        step2 = self.orchestrator.process_query(
            query="for the virtual internship",
            session_id=sid,
            is_clarification=True,
        )

        self.assertIn(step2["status"], ["answered", "success"])
        self.assertIn("resolved_query", step2)
        self.assertIn("internship", step2["resolved_query"].lower())
        self.assertEqual(step2["confidence"], "High")
        self.assertIn("Submit the online application", step2["answer"])
        self.assertEqual(len(step2["sources"]), 1)
        self.mock_retriever.retrieve.assert_called_once()

    def test_maximum_clarification_turns_limit(self):
        # Trigger ambiguous query
        res1 = self.orchestrator.process_query("tell me more")
        sid = res1["session_id"]

        # Turn 2: still vague
        res2 = self.orchestrator.process_query("about it", session_id=sid)
        self.assertEqual(res2["status"], "clarification_required")

        # Turn 3: still vague
        res3 = self.orchestrator.process_query("more details", session_id=sid)
        # Should now reach turn limit and gracefully exit
        self.assertEqual(res3["status"], "answered")
        self.assertIn("too broad", res3["answer"])


class TestFlaskClarificationIntegration(unittest.TestCase):
    """End-to-end integration tests on Flask API with full clarification flow."""

    @classmethod
    def setUpClass(cls):
        from app import app
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_flask_ambiguous_query_and_clarification_cycle(self):
        # 1. Ask ambiguous query
        resp1 = self.client.post("/query", json={"question": "What is the application process?"})
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.get_json()
        self.assertEqual(data1["status"], "clarification_required")
        self.assertEqual(data1["query_type"], "ambiguous")
        self.assertIsNotNone(data1["session_id"])
        self.assertIsNotNone(data1["clarification_question"])
        self.assertGreaterEqual(len(data1["suggested_options"]), 2)

        # 2. Provide clarification
        sid = data1["session_id"]
        resp2 = self.client.post("/query", json={
            "clarification": "for the internship program",
            "session_id": sid,
            "is_clarification": True,
        })
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertIn(data2["status"], ["answered", "success"])
        self.assertIsNotNone(data2["resolved_query"])
        self.assertIn("internship", data2["resolved_query"].lower())
        self.assertIn("answer", data2)
        self.assertIsNotNone(data2.get("conv_id"))


class TestConversationMemoryAgent(unittest.TestCase):
    """M3.2 Tests: Conversation Memory Agent, cross-turn history, and follow-up query resolution."""

    def setUp(self):
        self.conv_mgr = ConversationManager()

    def test_memory_creation_and_recording(self):
        mem = self.conv_mgr.get_or_create_memory()
        self.assertIsNotNone(mem.conv_id)
        self.assertFalse(mem.has_memory())

        mem.add_turn(
            query="What is virtual memory?",
            answer="Virtual memory is a memory management technique.",
            query_type="factual",
            sources=[{"document_name": "os.pdf", "page_number": 1}],
        )
        self.assertTrue(mem.has_memory())
        self.assertEqual(len(mem.turns), 1)
        self.assertIn("memory", mem.turns[0]["topics"])

    def test_followup_detection(self):
        mem = self.conv_mgr.get_or_create_memory()
        mem.add_turn(
            query="What is virtual memory?",
            answer="Virtual memory allows executing processes larger than physical memory.",
            query_type="factual",
        )
        # Pronoun follow-ups
        self.assertTrue(mem.is_followup("How does that work?"))
        self.assertTrue(mem.is_followup("Tell me more about it"))
        self.assertTrue(mem.is_followup("Explain this"))
        # Very short queries
        self.assertTrue(mem.is_followup("what about paging?"))
        # Non-follow-up independent query
        self.assertFalse(mem.is_followup("What is artificial intelligence and machine learning?"))

    def test_followup_resolution(self):
        mem = self.conv_mgr.get_or_create_memory()
        mem.add_turn(
            query="What is virtual memory?",
            answer="Virtual memory allows execution of partially loaded processes.",
            query_type="factual",
        )
        # Should substitute pronoun with primary topic
        resolved = mem.resolve_followup("How does that work?")
        self.assertNotIn("that", resolved.lower())
        self.assertIn("memory", resolved.lower())

    def test_context_summary_generation(self):
        mem = self.conv_mgr.get_or_create_memory()
        mem.add_turn("What is CPU scheduling?", "CPU scheduling decides which process runs.", "factual")
        mem.add_turn("What is FCFS?", "First-Come First-Served is non-preemptive.", "factual")

        summary = mem.get_context_summary()
        self.assertIn("[Conversation History]", summary)
        self.assertIn("What is CPU scheduling?", summary)
        self.assertIn("What is FCFS?", summary)

    def test_orchestrator_multi_turn_memory(self):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = {
            "status": "success",
            "results": [
                {
                    "document": "os.pdf",
                    "chunk_id": "c1",
                    "content": "Virtual memory uses paging.",
                    "score": 0.88,
                    "relevance": "High",
                }
            ],
            "retrieval_confidence": 0.88,
            "confidence_label": "High",
        }

        mock_generator = MagicMock()
        mock_generator.generate.return_value = {
            "answer": "Virtual memory is a system feature.",
            "sources": [{"document_name": "os.pdf", "page_number": 1, "similarity_score": 0.88}],
            "confidence": "High",
            "status": "success",
        }

        orchestrator = MultiAgentOrchestrator(
            query_understanding_agent=QueryUnderstandingAgent(),
            retrieval_agent=mock_retriever,
            response_generation_agent=mock_generator,
            clarification_agent=ClarificationAgent(),
            conversation_manager=self.conv_mgr,
        )

        # Turn 1
        res1 = orchestrator.process_query("What is virtual memory?", conv_id="test_conv_1")
        self.assertEqual(res1["status"], "success")
        self.assertEqual(res1["conv_id"], "test_conv_1")

        # Turn 2: Follow-up using "that"
        res2 = orchestrator.process_query("How does that work?", conv_id="test_conv_1")
        self.assertEqual(res2["status"], "success")
        # Memory agent stage should have run
        memory_stages = [s for s in res2["pipeline_stages"] if s.get("agent") == "ConversationMemoryAgent"]
        self.assertEqual(len(memory_stages), 1)


if __name__ == "__main__":
    unittest.main()

