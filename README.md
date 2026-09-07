# AI-Based Knowledge Retrieval Platform with Query Resolution System

## Overview

This is a fully functional Retrieval-Augmented Generation (RAG) platform built as part of a Virtual Internship
Milestone 1 project. The application allows users to upload knowledge documents in multiple formats (PDF, DOCX, TXT,
CSV), indexes them into a persistent vector database, and answers natural-language questions by retrieving the most
relevant document sections and generating grounded, factually accurate answers.

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
| **Speech-to-Text (STT)** | Web Speech API (`SpeechRecognition`) | Native browser-level voice input for queries |
| **Text-to-Speech (TTS)** | Web Speech API (`SpeechSynthesis`) | Browser-native voice readout of grounded answers |
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
│   ├── __init__.py             # Exports all backend components
│   ├── models.py               # DocumentChunk, RetrievalResult, QueryResponse
│   ├── document_processor.py   # PDF/DOCX/TXT/CSV parsers + file validation
│   ├── chunker.py              # Sliding window sentence-aware chunker
│   ├── embeddings.py           # Sentence-Transformers embedding engine
│   ├── vector_store.py         # FAISS index + disk persistence + search
│   ├── retriever.py            # Semantic retrieval + threshold filtering
│   └── generator.py            # Grounded answer generation (LLM + local fallback)
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
    └── test_pipeline.py        # Unit + integration tests for all pipeline stages
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

---

## Demo Scenarios

### Demo 1 — Operating Systems (PDF)
1. Load: `Operating_Systems.pdf` (via Sample Documents panel)
2. Ask: `What is virtual memory?`
3. Expected: Answer about virtual memory as a memory management technique, sources show page 4.

### Demo 2 — Structured Data (CSV)
1. Load: `students.csv`
2. Ask: `What is Ravi Kumar's CGPA and department?`
3. Expected: Retrieves exact row, answer shows Name: Ravi Kumar | Department: CSE | CGPA: 8.7

### Demo 3 — Artificial Intelligence (DOCX)
1. Load: `Artificial_Intelligence.docx`
2. Ask: `How does the attention mechanism work in transformers?`
3. Expected: Answer from the transformer chapter, correct source attribution.

### Demo 4 — Out-of-Domain / Unknown Question
1. With any documents loaded, ask: `How do I bake sourdough bread?`
2. Expected: System clearly states the information is not available in the uploaded knowledge base. No hallucination.

### Demo 5 — Persistence Test
1. Upload or load any document.
2. Stop the server (`Ctrl+C`).
3. Restart: `python app.py`
4. Ask the same question — answers should still work without re-uploading.

---

## Code Walkthrough Order (For Evaluation)

1. **`app.py`** — Flask routes, RAG pipeline initialization, logging
2. **`backend/document_processor.py`** — Format detection, text extraction, metadata
3. **`backend/chunker.py`** — Sentence-aware sliding window chunking
4. **`backend/embeddings.py`** — Local Sentence-Transformer encoding
5. **`backend/vector_store.py`** — FAISS index management and disk persistence
6. **`backend/retriever.py`** — Query embedding, similarity search, threshold filtering
7. **`backend/generator.py`** — Grounded prompt and LLM/fallback generation
8. **`static/script.js`** — Async API communication and dynamic UI rendering

---

## Future Scope — Milestone 2

Milestone 2 will extend this platform with a multi-agent orchestration system:

- **Query Understanding Agent** — Parses and reformulates user queries
- **Retrieval Agent** — Manages semantic search across multiple knowledge domains
- **Response Generation Agent** — Coordinates grounded generation with fact verification
- **Orchestration Layer** — Coordinates agent interactions and task delegation

The modular architecture of Milestone 1 (separate files for each RAG concern) is designed specifically
to support this extension.
