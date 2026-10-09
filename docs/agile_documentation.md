# Agile Project Management Documentation
## AI-Based Knowledge Retrieval Platform with Query Resolution System

---

## 1. Project Overview & Agile Framework

This project adopted an **Agile (Scrum / Iterative Delivery)** framework to develop an end-to-end multi-agent Retrieval-Augmented Generation (RAG) knowledge platform. Development was structured into four core milestones, each functioning as a major release release/sprint cycle with continuous integration, unit testing, sprint reviews, and iterative refinement.

* **Product Owner / Stakeholder:** Devender Pratap
* **Engineering Team:** AI Knowledge Retrieval Platform Development Team
* **License:** MIT License (Copyright (c) 2025 Vidzai Digital)
* **Repository:** [https://github.com/geetha577/AI-Knowledge-Retrieval-Platform.git](https://github.com/geetha577/AI-Knowledge-Retrieval-Platform.git)

---

## 2. Sprint & Milestone Breakdown

### Sprint 1 (Milestone 1): Ingestion Engine & Baseline RAG Foundation
* **Objective:** Establish the core document ingestion, vector storage, and extractive semantic retrieval.
* **Sprint Backlog / User Stories:**
  * *US-1.1:* As a user, I want to upload PDF, DOCX, TXT, and CSV documents so the platform can parse them.
  * *US-1.2:* As an engineer, I need text segmented into sentence-bounded chunks with overlap to retain context.
  * *US-1.3:* As an engineer, I need dense L2-normalized embeddings (`all-MiniLM-L6-v2`) and FAISS vector indexing for sub-second retrieval.
  * *US-1.4:* As a user, I want answers with grounded document citations to verify sources.
* **Deliverables:** `backend/document_processor.py`, `backend/chunker.py`, `backend/embeddings.py`, `backend/vector_store.py`, `backend/retriever.py`, baseline Flask API.
* **Test Outcome:** 39 baseline unit & integration tests passing.

---

### Sprint 2 (Milestone 2): Multi-Agent Architecture
* **Objective:** Decouple pipeline monolithic logic into specialized collaborative AI agents with sequential coordination.
* **Sprint Backlog / User Stories:**
  * *US-2.1:* As a system, I want a Query Understanding Agent (QUA) to classify queries (factual, procedural, comparative, ambiguous) with intent confidence.
  * *US-2.2:* As a system, I want a dedicated Retrieval Agent (RA) that isolates vector lookup and preserves rich metadata (page, section, score).
  * *US-2.3:* As a user, I want a Response Generation Agent (RGA) that prevents hallucinations by validating context relevance.
  * *US-2.4:* As an engineer, I want an Orchestrator coordinating the execution flow and producing structured trace logs.
* **Deliverables:** `backend/query_understanding_agent.py`, `backend/retrieval_agent.py`, `backend/response_generation_agent.py`, `backend/orchestrator.py`.
* **Test Outcome:** 18 multi-agent orchestration tests passing.

---

### Sprint 3 (Milestone 3): Ambiguity Handling & Conversational Memory
* **Objective:** Enable multi-turn dialogue, disambiguation interactions, and conversation memory.
* **Sprint Backlog / User Stories:**
  * *US-3.1:* As a user asking vague or multi-meaning terms (e.g., "networks", "memory"), I want clarifying questions with selectable suggestion chips.
  * *US-3.2:* As a user, I want follow-up queries ("what are its benefits?", "explain it") to inherit conversational context without cross-domain pollution.
  * *US-3.3:* As a user, I want voice interaction (STT and TTS) for hands-free query submission and listening.
* **Deliverables:** `backend/clarification_agent.py`, `backend/conversation_manager.py`, Web Speech API integration in `static/script.js`.
* **Test Outcome:** 21 clarification & memory tests passing.

---

### Sprint 4 (Milestone 4): Analytics, Multi-Domain Testing & Optimization
* **Objective:** Implement telemetry, knowledge gap detection, cross-domain validation, UI auto-scroll, and documentation.
* **Sprint Backlog / User Stories:**
  * *US-4.1:* As an administrator, I want query telemetry tracked in SQLite (query, latency, score, route, confidence) with CSV export.
  * *US-4.2:* As a content curator, I want a Knowledge Gap Detector to cluster unanswerable queries and recommend content additions.
  * *US-4.3:* As an evaluator, I need 3+ distinct domains tested (OS, AI, Cybersecurity, CSV) without cross-domain bleed.
  * *US-4.4:* As a user, I want answers to scroll into view cleanly with collapsed, simplified citation panels.
* **Deliverables:** `backend/analytics_engine.py`, `backend/knowledge_gap_detector.py`, comprehensive documentation suite, 96 automated tests passing.

---

## 3. Product Backlog & User Story Mapping

| Story ID | Epic | User Story | Priority | Story Points | Status |
|---|---|---|---|---|---|
| **US-01** | Ingestion | Parse PDF, DOCX, TXT, CSV with page/row metadata | High | 5 | ✅ Done |
| **US-02** | Retrieval | FAISS index with sentence-aware chunking and oversampling | High | 5 | ✅ Done |
| **US-03** | Multi-Agent | QUA intent & ambiguity classification | High | 8 | ✅ Done |
| **US-04** | Dialogue | Clarification Agent with UI suggestion chips | Medium | 5 | ✅ Done |
| **US-05** | Memory | Multi-turn contextual resolution without domain bleed | High | 5 | ✅ Done |
| **US-06** | Telemetry | SQLite query logging with 18 fields and CSV export | Medium | 3 | ✅ Done |
| **US-07** | Gap Detection | Cluster ungrounded queries and generate recommendations | Medium | 5 | ✅ Done |
| **US-08** | Accessibility | Speech-to-Text and Text-to-Speech Web API integration | Low | 3 | ✅ Done |
| **US-09** | Quality | Intent-aware extractive synthesis + slide noise filters | High | 5 | ✅ Done |
| **US-10** | Release | Packaging, MIT License, Agile docs, deployment readiness | High | 3 | ✅ Done |

---

## 4. Scrum Ceremonies & Quality Assurance

* **Sprint Planning:** Prioritized user stories according to milestone dependencies (Ingestion $\rightarrow$ Agents $\rightarrow$ Dialogue $\rightarrow$ Analytics).
* **Continuous Integration & Testing:**
  * Automated regression testing executing all 96 unit, integration, and multi-domain test cases via `pytest`.
  * Deterministic offline embedding fallbacks utilized to maintain test reliability across environments.
* **Sprint Retrospectives & Continuous Improvement:**
  * *Observation:* Extractive synthesis previously caused repeated slide titles and syllabus text in outputs.
  * *Action:* Added regex-based slide noise filtering (`_is_slide_noise`), title stripping, and question-type scoring bonuses during Sprint 4.
  * *Observation:* Pronoun injection bleed occurred during domain switching.
  * *Action:* Added follow-up guards requiring at least two substantive content words before triggering topic reuse.

---

## 5. Definition of Done (DoD)

A user story or feature was considered **Done** only when:
1. Implementation met the acceptance criteria and code standards.
2. Code passed unit tests without breaking existing M1–M3 functionality.
3. Provenance/citations were preserved throughout the pipeline.
4. Response generation adhered to strict factual grounding (zero ungrounded hallucination).
5. All code and documentation changes were reviewed and committed to the Git repository.
