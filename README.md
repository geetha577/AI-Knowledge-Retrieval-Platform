# AI-Based Knowledge Retrieval Platform with Query Resolution System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![FAISS](https://img.shields.io/badge/FAISS-1.15.1-orange.svg)](https://github.com/facebookresearch/faiss)
[![Tests](https://img.shields.io/badge/Tests-96%20Passing-brightgreen.svg)](#testing)
[![Live Demo](https://img.shields.io/badge/Render-Live%20Demo-brightgreen.svg)](https://ai-knowledge-retrieval-platform.onrender.com)

**🌐 Live Public URL:** [https://ai-knowledge-retrieval-platform.onrender.com](https://ai-knowledge-retrieval-platform.onrender.com)

A full-stack, multi-agent Retrieval-Augmented Generation (RAG) platform that enables intelligent, grounded Q&A over user-uploaded documents. Built across four milestones, it supports PDF, DOCX, TXT, and CSV file formats.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Running the Application](#running-the-application)
- [How to Use the Application](#how-to-use-the-application)
- [Configuration](#configuration)
- [Adding an LLM API Key (Recommended)](#adding-an-llm-api-key-recommended)
- [Testing](#testing)
- [Committing to GitHub](#committing-to-github)
- [Milestones](#milestones)
- [Architecture Overview](#architecture-overview)
- [Documentation](#documentation)

---

## Features

- **Multi-format document ingestion**: PDF (page-by-page), DOCX (paragraphs + tables), TXT (UTF-8/Latin-1), CSV (row-level records)
- **Semantic chunking**: Sentence-boundary-aware sliding window with configurable size and overlap
- **Vector embeddings**: `all-MiniLM-L6-v2` via Sentence-Transformers — L2-normalized, 384-dimensional
- **FAISS vector store**: Persistent flat-index for exact similarity search with lexical re-ranking
- **Multi-agent pipeline**: Query Understanding → (Clarification?) → Retrieval → Response Generation
- **Smart answer synthesis**: Intent-aware local synthesis + optional Gemini/OpenAI/Groq LLM generation
- **Conversation memory**: Multi-turn context tracking with pronoun and follow-up resolution
- **Clarification dialogues**: Ambiguity detection with smart clarification questions and clickable option chips
- **Analytics dashboard**: Real-time query logging (SQLite), query type breakdown, confidence trends
- **Knowledge gap detection**: Clustering of unanswered queries into actionable gap records
- **Voice interaction**: Web Speech API — speak queries and listen to answers
- **Citation transparency**: Collapsed source panel with per-source snippet expansion
- **90 automated tests** across four test suites

---

## Project Structure

```
knowledge-retrieval-platform/
├── app.py                          # Flask entry point & all API routes
├── config.yaml                     # Centralized configuration
├── .env                            # Environment variables (API keys, thresholds)
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── SYSTEM_ARCHITECTURE.md          # Architecture reference
├── create_sample_docs.py           # Sample knowledge base creator
│
├── backend/
│   ├── __init__.py
│   ├── config.py                   # Config loader (reads config.yaml)
│   ├── models.py                   # Data classes: DocumentChunk, RetrievalResult, QueryResponse
│   ├── document_processor.py       # File validation, parsing (PDF/DOCX/TXT/CSV)
│   ├── chunker.py                  # Sentence-aware text chunking with overlap
│   ├── embeddings.py               # EmbeddingEngine (SentenceTransformers + fallback)
│   ├── vector_store.py             # FAISS index + pickle metadata persistence
│   ├── retriever.py                # KnowledgeRetriever: FAISS search + lexical reranking
│   ├── generator.py                # ResponseGenerator: LLM + local grounded synthesis
│   ├── query_understanding_agent.py # QUA: intent classification + ambiguity detection
│   ├── retrieval_agent.py          # RetrievalAgent: wraps KnowledgeRetriever for pipeline
│   ├── response_generation_agent.py # RGA: wraps ResponseGenerator for pipeline
│   ├── clarification_agent.py      # ClarificationAgent: generates clarification Q&A
│   ├── conversation_manager.py     # ConversationManager: multi-turn memory + session
│   ├── orchestrator.py             # MultiAgentOrchestrator: routes and coordinates agents
│   ├── analytics_engine.py         # Analytics: SQLite storage, logging, CSV export
│   └── knowledge_gap_detector.py   # KnowledgeGapDetector: gap clustering from logs
│
├── static/
│   ├── script.js                   # Frontend logic (1285+ lines)
│   └── style.css                   # Application styles
│
├── templates/
│   └── index.html                  # Main UI template
│
├── data/
│   ├── uploads/                    # Saved uploaded documents
│   ├── vector_store/               # FAISS index.faiss + metadata.pkl
│   ├── analytics/                  # analytics.db (SQLite) + query_logs.json
│   └── sample_docs/                # Pre-built sample knowledge base documents
│
├── tests/
│   ├── test_pipeline.py            # 39 M1 pipeline tests
│   ├── test_clarification.py       # 21 clarification agent tests
│   ├── test_multi_agent.py         # 18 multi-agent orchestrator tests
│   └── test_milestone4_multidomain.py  # 12 M4 multi-domain tests
│
└── docs/
    ├── technical_documentation.md
    ├── m4_implementation_report.md
    ├── testing_report.md
    ├── optimization_report.md
    ├── final_project_report.md
    └── demo_guide.md
```

---

## Quick Start

### Prerequisites

- Python **3.10 or higher**
- Git
- Internet connection (first run downloads the embedding model ~90 MB)

### 1. Clone the Repository

```bash
git clone https://github.com/geetha577/AI-Knowledge-Retrieval-Platform.git
cd AI-Knowledge-Retrieval-Platform
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example and fill in values:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` and add your LLM API key (see [Adding an LLM API Key](#adding-an-llm-api-key-recommended)).

### 5. Run the Application

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## Running the Application

### Starting Fresh (No Prior Data)

If you want to start completely fresh with no prior indexed documents:

```powershell
# Delete existing vector store and uploads
Remove-Item -Recurse -Force data\vector_store\* -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force data\uploads\* -ErrorAction SilentlyContinue

# Then start the app
python app.py
```

You will see **"Knowledge Base: 0 chunks"** — upload your own documents.

### Loading the Sample Knowledge Base

To load the pre-built multi-domain sample knowledge base (AI, OS, Cybersecurity, Students):

1. Start the app: `python app.py`
2. Open the browser at **http://127.0.0.1:5000**
3. Click **"Sample Knowledge Bases"** in the Upload panel
4. Click **"Load pre-built multi-domain test data"**

Or run from the command line:

```bash
python create_sample_docs.py
```

Then restart the app and upload documents from `data/sample_docs/`.

### Re-Indexing Documents

Documents are **automatically indexed on upload**. If you delete the vector store and want to re-index existing uploaded files:

1. Stop the app
2. Delete `data/vector_store/index.faiss` and `data/vector_store/metadata.pkl`
3. Restart the app — the index starts empty
4. Re-upload your documents via the browser

---

## How to Use the Application

### Uploading Documents

1. Drag & drop a **PDF, DOCX, TXT, or CSV** file onto the upload zone (max 25 MB)
2. Or click **"Browse File"** and select a file
3. The document is parsed, chunked, embedded, and indexed automatically
4. The **Knowledge Base** counter updates (e.g., "495 chunks")

### Asking Questions

1. Type your question in the input box and press **Enter** or click **Send**
2. The multi-agent pipeline runs (typically < 1 second)
3. The answer appears in the chat with:
   - **Query type** badge (Factual / Procedural / Comparative / Clarification)
   - **Confidence level** (High / Medium / Low)
   - **📄 Sources** panel — click to expand and see which documents were used
   - **Agent Pipeline Trace** — click `+` to view which agents ran and their durations
4. Use the 🔊 **Listen** button to hear the answer via text-to-speech
5. Use the 🎤 **microphone** button (bottom of chat) to speak your question

### Handling Ambiguous Queries

When the Query Understanding Agent detects ambiguity (e.g., "tell me about networks"):
- A clarification question appears with **clickable option chips**
- Click a chip or type your clarification to continue
- The system merges your clarification with the original query and retrieves the answer

### Analytics Dashboard

Click **"Analytics & Gaps"** at the top to view:
- Total queries, answered rate, confidence breakdown
- Recent query log with type, status, similarity score
- Knowledge gap clusters — topics the knowledge base doesn't cover well

---

## Configuration

Edit `config.yaml` to tune the system:

```yaml
ingestion:
  chunk_size: 400          # Characters per chunk
  chunk_overlap: 50        # Overlap between adjacent chunks

retrieval:
  embedding_model: "all-MiniLM-L6-v2"   # Sentence-Transformers model name
  faiss_index_type: "flat"               # FAISS index type
  index_path: "data/vector_store/index.faiss"

analytics:
  storage: "sqlite"                      # "sqlite" or "json"
  db_path: "data/analytics/analytics.db"

server:
  host: "127.0.0.1"
  port: 5000
```

You can also override key settings via `.env`:

```env
CHUNK_SIZE=500
CHUNK_OVERLAP=100
TOP_K=5
SIMILARITY_THRESHOLD=0.25
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

## Adding an LLM API Key (Recommended)

Without an API key, the system uses the **Local Grounded Synthesis** fallback — an extractive sentence ranker that cannot paraphrase or reason. With an LLM API key, answers are generated by a real language model grounded in your documents.

**Supported providers (in priority order):**

| Provider | Environment Variable | Free Tier |
|----------|----------------------|-----------|
| Google Gemini | `GEMINI_API_KEY` | Yes — [aistudio.google.com](https://aistudio.google.com/) |
| OpenAI | `OPENAI_API_KEY` | Paid |
| Groq | `GROQ_API_KEY` | Yes — [console.groq.com](https://console.groq.com/) |

**Steps:**

1. Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Open `.env` in the project root
3. Add your key on line 17:
   ```
   GEMINI_API_KEY=your_key_here
   ```
4. Restart the app: `python app.py`

The system auto-detects the key and switches to Gemini generation. It tries these models in order: `gemini-1.5-flash` → `gemini-2.0-flash` → `gemini-1.5-pro`.

---

## Testing

### Run All Tests

```powershell
venv\Scripts\python.exe -m pytest tests/ -v
```

### Run a Specific Test Suite

```powershell
# M1 Pipeline tests (39 tests)
venv\Scripts\python.exe -m pytest tests/test_pipeline.py -v

# Clarification agent tests (21 tests)
venv\Scripts\python.exe -m pytest tests/test_clarification.py -v

# Multi-agent orchestrator tests (18 tests)
venv\Scripts\python.exe -m pytest tests/test_multi_agent.py -v

# M4 Multi-domain tests (12 tests)
venv\Scripts\python.exe -m pytest tests/test_milestone4_multidomain.py -v
```

**Expected result:** 90 tests passing, 0 failures.

---

## Committing to GitHub

### First-Time Setup

```bash
git init   # Only if not already a git repo
git remote add origin https://github.com/geetha577/AI-Knowledge-Retrieval-Platform.git
```

### Standard Commit & Push Workflow

```bash
# Stage all changes
git add .

# Commit with a descriptive message
git commit -m "feat: add M4 documentation and optimization improvements"

# Push to GitHub
git push origin main
```

### Getting a Shareable GitHub Link

After pushing, your project is live at:
```
https://github.com/geetha577/AI-Knowledge-Retrieval-Platform
```

To share a specific file:
```
https://github.com/geetha577/AI-Knowledge-Retrieval-Platform/blob/main/README.md
```

To get the raw clone URL for graders:
```
https://github.com/geetha577/AI-Knowledge-Retrieval-Platform.git
```

---

## Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| **M1** | Document ingestion, chunking, embeddings, FAISS vector store, semantic retrieval, grounded response generation | ✅ Complete |
| **M2** | Multi-agent architecture: Query Understanding Agent, Retrieval Agent, Response Generation Agent, Orchestrator | ✅ Complete |
| **M3** | Clarification Agent, multi-turn dialogue, Conversation Memory, follow-up resolution | ✅ Complete |
| **M4** | Analytics Engine, Knowledge Gap Detector, voice interaction, multi-domain testing, optimization | ✅ Complete |

---

## Architecture Overview

```
User Query
    │
    ▼
ConversationManager (follow-up resolution)
    │
    ▼
QueryUnderstandingAgent
    ├── ambiguous → ClarificationAgent → UI chips
    └── factual/procedural/comparative
            │
            ▼
        RetrievalAgent
        (FAISS search + lexical reranking)
            │
            ▼
        ResponseGenerationAgent
        (Gemini/OpenAI/Groq LLM  OR  Local Grounded Synthesis)
            │
            ▼
        Final Answer + Sources + Pipeline Trace
            │
            └── AnalyticsEngine (SQLite logging)
                └── KnowledgeGapDetector (gap analysis)
```

**Embedding model:** `all-MiniLM-L6-v2` (384-dimensional, L2-normalized)  
**Vector index:** FAISS Flat (exact cosine similarity)  
**Top-K retrieval:** 5 chunks (oversample ×4 for reranking)  
**Similarity threshold:** 0.25

---

## Documentation

| Document | Description |
|----------|-------------|
| [Agile Documentation](docs/agile_documentation.md) | Agile framework, Scrum sprints, user stories, DoD, and retrospective |
| [Technical Documentation](docs/technical_documentation.md) | Full system architecture, API reference, data flow diagrams |
| [M4 Implementation Report](docs/m4_implementation_report.md) | Milestone 4 feature implementation details |
| [Testing Report](docs/testing_report.md) | Test coverage, results, and analysis |
| [Optimization Report](docs/optimization_report.md) | Performance improvements and benchmarks |
| [Final Project Report](docs/final_project_report.md) | End-to-end project summary |
| [Demo Guide](docs/demo_guide.md) | Step-by-step demo walkthrough for submission |
| [System Architecture](SYSTEM_ARCHITECTURE.md) | Architecture reference document |

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Vidzai Digital.

---

*Built with Flask, FAISS, Sentence-Transformers, and multi-agent RAG architecture.*
