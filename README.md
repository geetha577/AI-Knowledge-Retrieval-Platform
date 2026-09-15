# AI-Based Knowledge Retrieval Platform with Query Resolution System

## Overview

This is a fully functional **Retrieval-Augmented Generation (RAG)** platform built as part of a Virtual Internship
project spanning **Milestone 1 (Knowledge Retrieval)** and **Milestone 2 (Multi-Agent Query Resolution)**.

The application allows users to upload knowledge documents in multiple formats (PDF, DOCX, TXT, CSV), indexes them
into a persistent vector database, and answers natural-language questions through a **three-agent orchestration
pipeline** that classifies the query, retrieves the most relevant document sections, and generates grounded,
factually accurate answers — all without hallucination.

---

## Problem

Users often need to extract specific information from large collections of documents — research papers, textbooks,
corporate knowledge bases, or structured data files. Traditional keyword search is rigid and misses semantic meaning.
General-purpose AI assistants hallucinate when asked about private or domain-specific content because they were not
trained on it.

---

## Solution

This application implements the RAG (Retrieval-Augmented Generation) pattern:

1. Documents are parsed, chunked, and embedded into dense numerical vectors.
2. Vectors are stored in a FAISS similarity index and persisted to disk.
3. When the user asks a question, the system embeds the query and performs semantic similarity search.
4. The most relevant document sections are retrieved and passed as context to a language model.
5. The model generates a grounded answer supported only by the retrieved context.
6. The answer is returned to the user along with source attribution and a confidence indicator.

---

## Features

- Upload PDF, DOCX, TXT, and CSV files through a drag-and-drop UI
- Automatic text extraction with format-specific parsers (page numbers for PDF, row metadata for CSV)
- Sentence-aware overlapping chunking preserving provenance metadata
- Local dense vector embedding using `sentence-transformers` (all-MiniLM-L6-v2, no API cost)
- FAISS vector index for fast cosine similarity search (persisted to disk)
- Retrieval with configurable top-k and similarity threshold
- High / Medium / Low confidence scoring per result
- Grounded answer generation (LLM API if key provided; intelligent local synthesis fallback if not)
- Source attribution: document name, page number or row number, similarity score
- Expandable source chunk viewer in the UI
- Retrieval Details panel (Explainability Mode) for code walkthroughs
- Pipeline status indicator for every stage of RAG execution
- Clear rejection when no relevant context is found (no hallucination)
- Persistent vector index survives server restarts
- Reset knowledge base functionality
- Pre-built sample documents for instant demonstration
- **[M2] Query Understanding Agent** — classifies every query as `factual`, `procedural`, `comparative`, or `ambiguous`
- **[M2] Retrieval Agent** — wraps semantic search; returns standardized M2 schema with confidence metadata
- **[M2] Response Generation Agent** — groundedness check before synthesis; rejects low-confidence noise
- **[M2] Multi-Agent Orchestrator** — coordinates all three agents; returns `pipeline_stages` for full traceability
- **[M2] Query-type badge** — UI badge shows classification + confidence % on every answer
- **[M2] Ambiguous query handling** — clarification guidance instead of guessing


---

## Architecture

```
                         USER
                           |
                           v
                  +------------------+
                  |    Web UI        |
                  | (HTML/CSS/JS)    |
                  +------------------+
                           |
                      HTTP Requests
                           |
                           v
                  +------------------+
                  |   Flask Backend  |
                  |    (app.py)      |
                  +------------------+
                    /               \
                   /                 \
                  v                   v
       +--------------------+    +--------------------+
       | Document Ingestion |    |  Query Processing  |
       |   Pipeline         |    |     Pipeline       |
       +--------------------+    +--------------------+
          |                              |
          v                             v
    document_processor.py         retriever.py
    (Extract text w/ metadata)    (Embed query + FAISS search)
          |                              |
          v                             v
    chunker.py                    vector_store.py
    (Split into chunks)           (Top-k cosine similarity)
          |                              |
          v                             v
    embeddings.py                 generator.py
    (Dense float32 vectors)       (Grounded answer from context)
          |                              |
          v                             v
    vector_store.py               Final Answer + Sources
    (FAISS persist to disk)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Web Framework** | Python 3.11, Flask | RESTful API endpoints and static file serving |
| **Frontend UI** | HTML5, CSS3, Vanilla JS | Lightweight, zero-dependency responsive client |
| **Document Processing** | `pypdf`, `python-docx`, Python `csv` | Format-specific text extraction with page/row metadata |
| **Chunking Engine** | Custom sliding-window (`backend/chunker.py`) | Sentence-aware chunking with overlap & provenance tagging |
| **Dense Embeddings** | `sentence-transformers` (`all-MiniLM-L6-v2`) | 384-dim normalized dense vector embeddings |
| **Vector Index** | `faiss-cpu` (`IndexFlatIP`) | Fast exact cosine similarity nearest-neighbor lookup |
| **Multi-Agent Design** | Modular Agent Roles (`backend/models.py`) | Query Understanding, Retrieval, Generation, Clarification, Memory |
| **Grounded Generation** | Dual Mode: Hybrid Extractive Synthesis + LLM API | Grounded responses with source attribution & zero hallucination |

---

## Installation

### Prerequisites
- Python 3.10 or higher
- pip

### Steps

**1. Clone or download the project:**
```
cd C:\path\to\knowledge-retrieval-platform
```

**2. (Recommended) Create a virtual environment:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**3. Install dependencies:**
```powershell
pip install -r requirements.txt
```
> Note: This installs PyTorch and sentence-transformers (~500 MB). First run will also download the embedding model (~90 MB) from HuggingFace.

**4. Configure environment variables:**
```powershell
copy .env.example .env
```
Edit `.env` if you want to use an LLM API (optional). Without a key, the local grounded synthesis fallback is used automatically.

**5. Generate sample documents (one-time setup):**
```powershell
python create_sample_docs.py
```

---

## Environment Variables

Copy `.env.example` to `.env` and customize as needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_MODEL` | Sentence Transformer model name | `all-MiniLM-L6-v2` |
| `CHUNK_SIZE` | Maximum characters per chunk | `500` |
| `CHUNK_OVERLAP` | Overlap between adjacent chunks | `100` |
| `TOP_K` | Number of results to retrieve per query | `5` |
| `SIMILARITY_THRESHOLD` | Minimum cosine similarity to include a result | `0.35` |
| `OPENAI_API_KEY` | OpenAI API key (optional) | _(empty)_ |
| `GEMINI_API_KEY` | Google Gemini API key (optional) | _(empty)_ |
| `GROQ_API_KEY` | Groq API key (optional) | _(empty)_ |
| `PORT` | Flask server port | `5000` |

> **Important**: Never commit your real `.env` file. It is already included in `.gitignore`.

---

## Running the Application

```powershell
python app.py
```

Open your browser at:
```
http://127.0.0.1:5000
```

---

## Usage

### 1. Upload a Document
- Click **Choose File** or drag and drop a PDF, DOCX, TXT, or CSV file.
- Watch the status bar: Uploading → Extracting → Generating Embeddings → Indexed.
- The document appears in the **Knowledge Base** panel.

### 2. Or Load a Sample Document
- Click **Load** next to any pre-built sample document (bottom of the left panel).

### 3. Ask a Question
- Type your question in the text area.
- Click **Ask Question** or press `Ctrl+Enter`.
- Watch the pipeline steps: Received Query → Generating Embedding → Semantic Search → Relevance Filtering → Generating Answer.

### 4. Inspect the Answer
- The **Answer** card shows the generated response.
- The **Confidence** badge shows High / Medium / Low / None.

### 5. Inspect Sources
- The **Sources Used** section lists all retrieved document sections with page/row info and similarity scores.
- Click **+** on any source card to expand and read the full retrieved chunk text.

### 6. Inspect Retrieval Details (Explainability Mode)
- Click **Retrieval Details (Explainability Mode)** to expand the pipeline visualization.
- This shows: User Query → Query Embedding Shape → All Retrieved Chunks → Similarity Scores → Selected Context → Generator Mode → Final Answer.
- Use this during your code walkthrough to demonstrate that real RAG is happening.

---

## Project Structure

```
knowledge-retrieval-platform/
│
├── app.py                      # Flask routes and application entry point
├── requirements.txt            # Pinned Python dependencies
├── README.md                   # This file
├── .env.example                # Configuration template
├── .gitignore                  # Git exclusions (venv, .env, uploads, index)
├── create_sample_docs.py       # One-time script to generate demo documents
│
├── backend/
│   ├── __init__.py             # Exports all backend components (M1 + M2)
│   ├── models.py               # DocumentChunk, RetrievalResult, QueryResponse, AgentMessage
│   ├── document_processor.py   # PDF/DOCX/TXT/CSV parsers + file validation
│   ├── chunker.py              # Sliding window sentence-aware chunker
│   ├── embeddings.py           # Sentence-Transformers embedding engine
│   ├── vector_store.py         # FAISS index + disk persistence + search
│   ├── retriever.py            # [M1] Semantic retrieval + threshold filtering
│   ├── generator.py            # [M1] Grounded answer generation (LLM + local fallback)
│   ├── query_understanding_agent.py  # [M2] Classifies queries: factual/procedural/comparative/ambiguous
│   ├── retrieval_agent.py      # [M2] Retrieval Agent wrapping KnowledgeRetriever
│   ├── response_generation_agent.py  # [M2] Response Agent with groundedness validation
│   └── orchestrator.py         # [M2] Multi-Agent Orchestrator coordinating all three agents
│
├── data/
│   ├── uploads/                # Saved uploaded documents
│   ├── vector_store/           # Persisted FAISS index and metadata
│   └── sample_docs/            # Pre-built demo documents
│       ├── Operating_Systems.pdf
│       ├── students.csv
│       ├── Artificial_Intelligence.docx
│       └── Cybersecurity_Basics.txt
│
├── templates/
│   └── index.html              # Main dashboard HTML
│
├── static/
│   ├── style.css               # Academic dashboard styles
│   └── script.js               # Frontend async controller
│
└── tests/
    ├── test_pipeline.py        # [M1] Unit + integration tests (39 tests)
    └── test_multi_agent.py     # [M2] Multi-agent unit + integration tests (18 tests)
```

---

## RAG Pipeline Explained

```
Documents
    |
    v
[document_processor.py]
 — Validates file type and size
 — Parses PDF (page-by-page), DOCX (paragraphs + tables),
   TXT (UTF-8/Latin-1), CSV (key-value row format)
 — Cleans whitespace and control characters
    |
    v
[chunker.py]
 — Splits text using sentence-aware sliding window
 — Attaches chunk_id, document_name, page/row metadata
 — Preserves source attribution for every chunk
    |
    v
[embeddings.py]
 — Encodes chunks using all-MiniLM-L6-v2 (384-dim dense vectors)
 — L2-normalized for cosine similarity via inner product
    |
    v
[vector_store.py]
 — Stores vectors in FAISS IndexFlatIP
 — Persists index + metadata to disk (survives server restarts)
    |
    v
[retriever.py]
 — Embeds user query with same model
 — Searches FAISS for top-k similar chunks
 — Filters by similarity threshold
 — Assigns High/Medium/Low relevance labels
    |
    v
[generator.py]
 — Builds grounded prompt from retrieved chunks
 — Calls LLM API if configured, else uses local synthesis
 — Returns answer + sources + confidence
    |
    v
User sees: Answer + Sources + Confidence + Explainability Details
```

---

## Running Tests

### Milestone 1 Tests (39 tests)
```powershell
python -m unittest tests/test_pipeline.py -v
```

Tests cover:
- Data model creation and serialization
- TXT, CSV, PDF, DOCX text extraction
- Chunk size, overlap, metadata, uniqueness
- Embedding shape, dtype, normalization
- Vector store add, search, persistence, clear
- Retrieval relevance labeling and threshold filtering
- Response generator grounding and rejection behavior
- Flask API endpoints (/health, /documents, /query, /)

### Milestone 2 Tests (18 tests)
```powershell
python -m unittest tests/test_multi_agent.py -v
```

Tests cover:
- `QueryUnderstandingAgent`: factual, procedural, comparative, ambiguous classification
- `RetrievalAgent`: success with metadata schema, no-results handling
- `ResponseGenerationAgent`: ambiguous clarification, no-results rejection, grounded success
- `MultiAgentOrchestrator`: ambiguous flow, factual flow, unavailable-information flow
- Flask integration: health endpoint agents list, query_type badge in responses, pipeline_stages, clarification routing

### Full Combined Suite (57 tests)
```powershell
python -m unittest discover -s tests
```

---

## Milestone 2 — Multi-Agent Query Resolution

### Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                  Multi-Agent Orchestrator                │
│                    (orchestrator.py)                     │
│                                                          │
│  ┌─────────────────────┐                                 │
│  │  Query Understanding │  Stage 1: Classify query       │
│  │       Agent          │  → factual / procedural /      │
│  │ (query_understanding │    comparative / ambiguous      │
│  │    _agent.py)        │  → route: retrieval /          │
│  └──────────┬──────────┘    clarification               │
│             │                                            │
│     (if route == retrieval)                              │
│             │                                            │
│  ┌──────────▼──────────┐                                 │
│  │   Retrieval Agent    │  Stage 2: Semantic search      │
│  │  (retrieval_agent.py)│  → top-k FAISS results         │
│  │                      │  → confidence_label            │
│  └──────────┬──────────┘                                 │
│             │                                            │
│  ┌──────────▼──────────┐                                 │
│  │  Response Generation │  Stage 3: Groundedness check   │
│  │       Agent          │  + synthesis or rejection      │
│  │ (response_generation │  → answer + sources            │
│  │    _agent.py)        │  → final confidence            │
│  └─────────────────────┘                                 │
└─────────────────────────────────────────────────────────┘
    │
    ▼
 /query endpoint returns:
  {answer, query_type, classification_confidence, route,
   confidence, sources, status, pipeline_stages}
```

### Query Classification Rules

| Query Type | Signal Words / Patterns | Route |
|---|---|---|
| **factual** | `what is`, `who is`, `define`, `explain` | retrieval |
| **procedural** | `how do`, `how to`, `steps to`, `guide` | retrieval |
| **comparative** | `difference between`, `compare`, `vs`, `which is better` | retrieval |
| **ambiguous** | Short (<4 tokens), vague pronouns, no clear subject | clarification |

### Agent Responsibilities

| Agent | File | Responsibility |
|---|---|---|
| `QueryUnderstandingAgent` | `query_understanding_agent.py` | Classify + route every query |
| `RetrievalAgent` | `retrieval_agent.py` | Semantic search + standardized M2 schema |
| `ResponseGenerationAgent` | `response_generation_agent.py` | Groundedness check + grounded synthesis |
| `MultiAgentOrchestrator` | `orchestrator.py` | Sequential coordination of all 3 agents |

### Example Queries and Expected Behavior

| Query | Type | Confidence | Behavior |
|---|---|---|---|
| `What is virtual memory?` | factual | High | Answers from OS textbook |
| `How do I prevent phishing attacks?` | procedural | Medium | Step-by-step from Cybersecurity doc |
| `What is the difference between RAM and ROM?` | comparative | Medium | Comparative answer from OS doc |
| `Tell me about it.` | ambiguous | None | Clarification guidance message |
| `What is the capital of France?` | factual | None | Rejection (not in knowledge base) |

### Demo Scenarios (Milestone 2)

#### Demo 6 — Factual Query with Type Badge
1. Load `Artificial_Intelligence.docx`
2. Ask: `What is machine learning?`
3. Expected: Answer from AI doc, **[factual]** badge shown with classification confidence %

#### Demo 7 — Procedural Query
1. Load `Cybersecurity_Basics.txt`
2. Ask: `How do I prevent phishing attacks?`
3. Expected: Step-by-step answer, **[procedural]** badge shown, 3 pipeline stages visible

#### Demo 8 — Comparative Query
1. Load `Operating_Systems.pdf`
2. Ask: `What is the difference between RAM and ROM?`
3. Expected: Comparative answer, **[comparative]** badge shown in orange

#### Demo 9 — Ambiguous Query (Clarification)
1. With any documents loaded, ask: `Tell me about it.`
2. Expected: **[ambiguous]** badge, clarification guidance message, no sources, Confidence: None

#### Demo 10 — Out-of-Domain Rejection (M2 Groundedness Check)
1. With any documents loaded, ask: `What is the capital of France?`
2. Expected: Pipeline completes all 3 stages, Retrieval Agent returns no results, rejection message

---

## Code Walkthrough Order (For Evaluation)

### Milestone 1 Core Pipeline
1. **`app.py`** — Flask routes, RAG pipeline initialization, logging
2. **`backend/document_processor.py`** — Format detection, text extraction, metadata
3. **`backend/chunker.py`** — Sentence-aware sliding window chunking
4. **`backend/embeddings.py`** — Local Sentence-Transformer encoding
5. **`backend/vector_store.py`** — FAISS index management and disk persistence
6. **`backend/retriever.py`** — Query embedding, similarity search, threshold filtering
7. **`backend/generator.py`** — Grounded prompt and LLM/fallback generation
8. **`static/script.js`** — Async API communication and dynamic UI rendering

### Milestone 2 Multi-Agent Layer
9. **`backend/query_understanding_agent.py`** — Query classification logic (regex + vague-token detection)
10. **`backend/retrieval_agent.py`** — Retrieval Agent adapting M1 retriever to M2 schema
11. **`backend/response_generation_agent.py`** — Groundedness validation before synthesis
12. **`backend/orchestrator.py`** — Sequential multi-agent orchestration + `pipeline_stages` logging
13. **`tests/test_multi_agent.py`** — M2 unit tests for all four components

---

## Future Scope — Milestone 3

Milestone 3 will extend this platform with:

- **Clarification Agent** — Interactive follow-up questions for ambiguous queries (already flagged in M2)
- **Memory Agent** — Session-level conversation history and context carryover
- **Multi-domain Routing** — Automatic knowledge domain detection and targeted retrieval
- **Voice Interface** — Full end-to-end voice Q&A using Web Speech API (STT + TTS)
- **Evaluation Dashboard** — Retrieval precision@k, answer faithfulness, and MRR metrics

The modular agent architecture of Milestone 2 is designed specifically to support these extensions.
