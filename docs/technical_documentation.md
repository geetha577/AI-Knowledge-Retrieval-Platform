# Technical Documentation
## AI-Based Knowledge Retrieval Platform with Query Resolution System

**Version:** 1.0 — Milestone 4  
**Date:** October 2026  
**Author:** AI Knowledge Retrieval Platform Team

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Data Flow](#3-data-flow)
4. [Component Reference](#4-component-reference)
   - [Document Processor](#41-documentprocessor)
   - [Document Chunker](#42-documentchunker)
   - [Embedding Engine](#43-embeddingengine)
   - [Vector Store](#44-vectorstore)
   - [Knowledge Retriever](#45-knowledgeretriever)
   - [Response Generator](#46-responsegenerator)
   - [Query Understanding Agent](#47-queryunderstandingagent)
   - [Retrieval Agent](#48-retrievalagent)
   - [Response Generation Agent](#49-responsegenerationagent)
   - [Clarification Agent](#410-clarificationagent)
   - [Conversation Manager](#411-conversationmanager)
   - [Multi-Agent Orchestrator](#412-multiagentorchestrator)
   - [Analytics Engine](#413-analyticsengine)
   - [Knowledge Gap Detector](#414-knowledgegapdetector)
5. [API Reference](#5-api-reference)
6. [Configuration Reference](#6-configuration-reference)
7. [Data Models](#7-data-models)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Voice Interaction](#9-voice-interaction)
10. [Error Handling](#10-error-handling)

---

## 1. System Overview

The AI-Based Knowledge Retrieval Platform is a full-stack Retrieval-Augmented Generation (RAG) system with a multi-agent pipeline. Users upload documents in PDF, DOCX, TXT, or CSV format, and can then ask natural-language questions about the content. The system retrieves the most relevant document chunks using semantic search and generates grounded, citation-backed answers.

**Technology Stack:**

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.1.3 (Python 3.10+) |
| Vector Search | FAISS 1.15.1 (flat index, cosine similarity) |
| Embedding Model | `all-MiniLM-L6-v2` (Sentence-Transformers) |
| PDF Parsing | pypdf 6.19.0 |
| Word Parsing | python-docx 1.2.0 |
| Tabular Parsing | pandas 3.0.6 |
| Analytics DB | SQLite (configurable to JSON) |
| LLM Integration | Google Gemini / OpenAI / Groq (optional) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Voice | Web Speech API (browser-native) |

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                           │
│  ┌─────────┐  ┌──────────────┐  ┌────────────────┐  ┌──────────┐  │
│  │ Upload  │  │  Chat Panel  │  │ Analytics Modal│  │  Voice   │  │
│  │  Panel  │  │  + Sources   │  │  + Gap Detect  │  │  (TTS)   │  │
│  └────┬────┘  └──────┬───────┘  └───────┬────────┘  └────┬─────┘  │
│       │              │                  │                 │         │
└───────┼──────────────┼──────────────────┼─────────────────┼─────────┘
        │ /upload      │ /query           │ /analytics      │
        ▼              ▼                  ▼                 │
┌─────────────────────────────────────────────────────────────────────┐
│                      FLASK API LAYER (app.py)                       │
│  POST /upload  POST /query  GET /analytics  GET /gaps  GET /docs   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
    INGESTION PATH        QUERY PATH          ANALYTICS PATH
             │                  │                  │
      ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
      │  Document   │    │Conversation │    │  Analytics  │
      │  Processor  │    │  Manager    │    │   Engine    │
      └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
             │                  │                  │
      ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
      │  Chunker    │    │  Query      │    │  Knowledge  │
      └──────┬──────┘    │Understanding│    │   Gap       │
             │           │   Agent     │    │  Detector   │
      ┌──────▼──────┐    └──────┬──────┘    └─────────────┘
      │  Embedding  │           │
      │   Engine    │    ┌──────▼──────┐
      └──────┬──────┘    │ Retrieval   │
             │           │   Agent     │
      ┌──────▼──────┐    └──────┬──────┘
      │  Vector     │           │
      │   Store     │    ┌──────▼──────┐
      │  (FAISS)    │    │  Response   │
      └─────────────┘    │  Generation │
                         │   Agent     │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │ Gemini LLM  │
                         │ OR Local    │
                         │ Synthesis   │
                         └─────────────┘
```

---

## 3. Data Flow

### 3.1 Document Ingestion Flow

```
File Upload (HTTP POST /upload)
    │
    ▼
DocumentProcessor.save_file()
    - Validate extension (.pdf/.docx/.txt/.csv)
    - Check file size (max 25 MB)
    - Sanitize filename (werkzeug secure_filename)
    - Save to data/uploads/
    │
    ▼
DocumentProcessor.extract()
    - PDF: pypdf page-by-page extraction (page_number metadata preserved)
    - DOCX: python-docx paragraphs + tables
    - TXT: UTF-8 / Latin-1 encoding with clean_text()
    - CSV: pandas row-level structured records
    Returns: List[{"text": str, "page_number": int|None, "row_number": int|None}]
    │
    ▼
DocumentChunker.chunk_document()
    - CSV rows: kept as atomic records (≤ 2× chunk_size)
    - Prose: sentence-aware sliding window
      chunk_size=400 chars, overlap=50 chars
    - Each chunk gets: chunk_id, document_name, document_type,
      page_number, row_number, source_id
    Returns: List[DocumentChunk]
    │
    ▼
EmbeddingEngine.generate_embeddings()
    - Model: all-MiniLM-L6-v2 (384-dimensional)
    - L2-normalized float32 vectors
    Returns: np.ndarray shape (N, 384)
    │
    ▼
VectorStore.add_documents()
    - FAISS IndexFlatIP (inner product = cosine on normalized vectors)
    - Metadata stored as parallel pickle list
    - Persisted to data/vector_store/index.faiss + metadata.pkl
```

### 3.2 Query Resolution Flow

```
User Query (HTTP POST /query)
    │
    ▼
ConversationManager.resolve_followup_query()
    - Detect pronoun/follow-up references
    - Inject prior topic context if needed
    │
    ▼
QueryUnderstandingAgent.analyze()
    - Pattern matching: comparative, procedural, factual
    - Ambiguity detection: pronouns, multi-meaning words, vague phrases
    - Returns: {query_type, route, confidence, reasoning}
    │
    ├─── route = "clarification" ──────────────────────────────────┐
    │                                                              │
    ▼                                                             ▼
RetrievalAgent.retrieve()                              ClarificationAgent.generate_clarification()
    ↳ KnowledgeRetriever.retrieve()                        - Tailor question to query type
      - FAISS search (fetch_k = top_k × 4 = 20)            - Provide clickable option chips
      - Lexical reranking (document name + term boost)      Returns: {question, options}
      - Filter by similarity_threshold (0.25)
      - Returns top_k=5 chunks
    │
    ▼
ResponseGenerationAgent.generate()
    - Groundedness check (conf < 0.40 AND no keyword match → reject)
    - Calls ResponseGenerator.generate_response()
      ├── Gemini API (if GEMINI_API_KEY set)
      ├── OpenAI API (if OPENAI_API_KEY set)
      ├── Groq API (if GROQ_API_KEY set)
      └── Local Grounded Synthesis fallback
    │
    ▼
AnalyticsEngine.record_query()
    - Logs: query, type, route, confidence, status, similarity, duration
    - Stored in SQLite (data/analytics/analytics.db)
    │
    ▼
Response JSON returned to frontend
    {answer, confidence, sources, pipeline_stages, status, conv_id}
```

---

## 4. Component Reference

### 4.1 DocumentProcessor

**File:** `backend/document_processor.py`

Handles file validation, storage, and format-specific text extraction.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `save_file(file_storage)` | Validates, sanitizes, and saves an uploaded Flask FileStorage object. Returns `Path`. |
| `extract(file_path)` | Dispatches to format-specific extractor based on file extension. |
| `_extract_pdf(file_path)` | Page-by-page extraction via pypdf. Handles encrypted PDFs. |
| `_extract_docx(file_path)` | Extracts paragraphs + tables from DOCX. |
| `_extract_txt(file_path)` | UTF-8 / Latin-1 plain text extraction. |
| `_extract_csv(file_path)` | Row-level structured records via pandas. Multi-encoding support. |
| `clean_text(text)` | Normalizes whitespace, removes control characters. |
| `clean_upload_dir()` | Removes all uploaded files for reset. |

**Supported Formats:** `.pdf`, `.docx`, `.txt`, `.csv`  
**Max File Size:** 25 MB

---

### 4.2 DocumentChunker

**File:** `backend/chunker.py`

Splits extracted text segments into overlapping chunks with sentence boundary awareness.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `chunk_document(filename, segments)` | Produces `List[DocumentChunk]` from document segments. |
| `_split_text(text)` | Sentence-aware sliding window chunking. |

**Configuration (from `config.yaml`):**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | 400 | Target characters per chunk |
| `chunk_overlap` | 50 | Characters carried over from previous chunk |

**CSV handling:** Each row is kept as a single atomic chunk if `len(text) ≤ chunk_size × 2`.

---

### 4.3 EmbeddingEngine

**File:** `backend/embeddings.py`

Generates L2-normalized dense vector embeddings.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `generate_embeddings(texts)` | Encodes list of strings → `np.ndarray (N, 384)` float32 L2-normalized |
| `generate_query_embedding(query)` | Encodes single query → `np.ndarray (1, 384)` |
| `_generate_fallback_embeddings(texts)` | Deterministic hash-based fallback when model unavailable |

**Model:** `all-MiniLM-L6-v2`  
**Dimension:** 384  
**Class-level model caching:** Models are loaded once and cached per process.

---

### 4.4 VectorStore

**File:** `backend/vector_store.py`

FAISS-based persistent vector store.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `add_documents(chunks, embeddings)` | Adds chunks and their embeddings to FAISS index |
| `search(query_vector, top_k)` | Returns `List[Tuple[DocumentChunk, float]]` sorted by similarity |
| `get_all_chunks()` | Returns all indexed chunks |
| `remove_document(document_name)` | Removes a document and rebuilds index |
| `save()` | Persists index.faiss + metadata.pkl |
| `load()` | Loads persisted index + metadata |

**Index Type:** `IndexFlatIP` (exact inner product search on normalized vectors ≡ cosine similarity)  
**Persistence:** `data/vector_store/index.faiss` + `data/vector_store/metadata.pkl`

---

### 4.5 KnowledgeRetriever

**File:** `backend/retriever.py`

Orchestrates query embedding, FAISS search, lexical re-ranking, and relevance scoring.

**Key Method:** `retrieve(query, top_k, threshold)`

**Pipeline:**
1. Generate query embedding
2. FAISS search with oversampling: `fetch_k = max(top_k × 4, 20)`
3. Lexical boost: document name match `+0.15`, term hit in text `+0.05` per content word
4. Re-sort by adjusted score, truncate to `top_k`
5. Filter by `similarity_threshold` (default 0.25)
6. Label relevance: High (≥0.65), Medium (≥0.45), Low (<0.45)

**Returns:**
```python
{
    "relevant_results": List[RetrievalResult],  # above threshold
    "all_retrieved": List[RetrievalResult],     # all top_k
    "top_score": float,
    "confidence": "High" | "Medium" | "Low" | "None",
    "query_embedding_shape": List[int]
}
```

---

### 4.6 ResponseGenerator

**File:** `backend/generator.py`

Generates grounded answers from retrieved context. Supports multiple LLM backends.

**Provider priority:** `GEMINI_API_KEY` → `OPENAI_API_KEY` → `GROQ_API_KEY` → Local fallback

**Key Methods:**

| Method | Description |
|--------|-------------|
| `generate_response(query, retrieval_data)` | Main entry point; returns `QueryResponse` |
| `_call_gemini(query, context)` | Calls Gemini API (tries gemini-1.5-flash → gemini-2.0-flash → gemini-1.5-pro) |
| `_call_openai(query, context)` | Calls OpenAI gpt-3.5-turbo |
| `_call_groq(query, context)` | Calls Groq (llama-3.1-8b-instant → llama-3.3-70b-versatile) |
| `_local_grounded_synthesis(query, results)` | Intent-aware extractive synthesizer (fallback) |
| `_is_slide_noise(text)` | Filters syllabus metadata, table fragments, short lines |
| `_extract_list_items(text)` | Extracts bullet/numbered items from text |
| `_classify_question_type(query)` | Maps query to: comparison/list/procedural/conceptual/definition/explanation |

**Local synthesis intent flags:**
- `wants_definition`: what is / define / meaning
- `wants_list`: types / advantages / features / list
- `wants_comparison`: compare / difference / versus
- `wants_procedural`: how to / steps to / process of
- `wants_reason`: why / purpose / importance
- `wants_summary`: summary / overview / briefly

---

### 4.7 QueryUnderstandingAgent

**File:** `backend/query_understanding_agent.py`

Classifies query intent and detects ambiguity.

**Classification order:**
1. Ambiguity check (pronouns, vague tokens, multi-meaning words, generic nouns)
2. Comparative patterns (`compare`, `difference between`, `versus`, `vs`)
3. Procedural patterns (`how do`, `steps to`, `process of`)
4. Factual patterns (`what is`, `define`, `types of`, `list`)
5. Default: factual

**Multi-meaning word detection:**
Words like `networks`, `memory`, `python`, `security`, `model`, `learning`, `architecture`, `kernel`, `thread`, `interface` trigger clarification when no disambiguating context is present.

**Returns:**
```python
{
    "query": str,
    "query_type": "factual" | "procedural" | "comparative" | "ambiguous",
    "classification_confidence": float,
    "route": "retrieval" | "clarification",
    "reasoning": str
}
```

---

### 4.8 RetrievalAgent

**File:** `backend/retrieval_agent.py`

Wraps `KnowledgeRetriever` for the multi-agent pipeline. Translates raw retriever output into a standardized dictionary format.

**Returns:**
```python
{
    "query": str,
    "query_type": str,
    "results": [{"content", "document", "page", "row_number", "section",
                 "chunk_id", "score", "relevance", "source_id"}],
    "retrieval_confidence": float,
    "confidence_label": str,
    "status": "success" | "no_results",
    "raw_retrieval_data": dict
}
```

---

### 4.9 ResponseGenerationAgent

**File:** `backend/response_generation_agent.py`

Wraps `ResponseGenerator` with extra groundedness validation for the multi-agent pipeline.

**Groundedness check:**
If `retrieval_confidence < 0.40` AND no content word overlap between query and retrieved chunks → reject with `REJECTION_MESSAGE` to prevent hallucination.

**Returns:**
```python
{
    "answer": str,
    "sources": List[dict],
    "confidence": "High" | "Medium" | "Low" | "None",
    "status": "success" | "no_results" | "clarification_needed",
    "debug_details": dict
}
```

---

### 4.10 ClarificationAgent

**File:** `backend/clarification_agent.py`

Generates targeted clarification questions with option chips for ambiguous queries.

**Handlers:**
- Multi-meaning words (python, networks, memory, learning, security, etc.)
- Generic requirement/process/deadline queries
- Pronoun ambiguity (it/this/that)
- Generic fallback with document-aware suggestions

**Returns:**
```python
{
    "needs_clarification": True,
    "clarification_question": str,
    "reason": str,
    "confidence": float,
    "suggested_options": List[str]   # Up to 3 option chips
}
```

---

### 4.11 ConversationManager

**File:** `backend/conversation_manager.py`

Manages two types of conversational context:

**Session-based clarification (Milestone 3):**
- `start_session(original_query, clarification_question, suggested_options)` → `session_id`
- `get_session(session_id)`, `record_turn()`, `complete_session()`, `resolve_query()`

**Memory-based follow-up (Milestone 3.2):**
- `get_or_create_memory(conv_id)` → `ConversationMemory`
- `add_memory_turn(conv_id, query, answer, ...)` — stores last 10 turns
- `resolve_followup_query(conv_id, query)` — resolves pronouns and bare continuations

**Follow-up detection logic:**
- Only bare continuation phrases trigger context injection (e.g., "and?", "continue", "go on")
- Self-contained queries (≥ 2 content words, no pronouns) skip injection
- Acronym-aware topic extraction (ai, os, ml, dl preserved as 2-letter tokens)

---

### 4.12 MultiAgentOrchestrator

**File:** `backend/orchestrator.py`

Coordinates the complete multi-agent pipeline sequentially.

**Pipeline stages:**
1. `ConversationMemory` — follow-up resolution (if `conv_id` provided)
2. `QueryUnderstandingAgent` — intent classification
3. Branch on route:
   - `clarification` → `ClarificationAgent` → return clarification response
   - `retrieval` → `RetrievalAgent` → `ResponseGenerationAgent` → return answer
4. `AnalyticsEngine.record_query()` — telemetry logging

**Max clarification turns:** 3 (configurable in `ConversationManager`)

**Returns:**
```python
{
    "query": str, "original_query": str, "resolved_query": str,
    "query_type": str, "classification_confidence": float, "route": str,
    "answer": str, "confidence": str, "sources": List[dict],
    "status": str, "session_id": str|None, "conv_id": str,
    "pipeline_stages": List[dict], "debug_details": dict
}
```

---

### 4.13 AnalyticsEngine

**File:** `backend/analytics_engine.py`

Thread-safe analytics storage with SQLite backend.

**SQLite schema (`queries` table):**

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Unique query ID (millisecond timestamp) |
| timestamp | REAL | Unix timestamp |
| date_str | TEXT | Human-readable date |
| query | TEXT | Original user query |
| resolved_query | TEXT | Resolved follow-up query |
| query_type | TEXT | factual / procedural / comparative / ambiguous |
| route | TEXT | retrieval / clarification |
| confidence | TEXT | High / Medium / Low / None |
| status | TEXT | success / no_results / clarification_required / error |
| top_similarity_score | REAL | Best FAISS cosine score |
| retrieved_chunks_count | INTEGER | Chunks above threshold |
| source_documents | TEXT | JSON list of document names |
| duration_sec | REAL | Total pipeline time |
| session_id | TEXT | Clarification session ID |
| conv_id | TEXT | Conversation memory ID |
| clarification_question | TEXT | Generated clarification prompt |
| is_unanswered | INTEGER | 1 if no results found |
| error | TEXT | Error message if any |

**Key Methods:** `record_query()`, `get_logs(limit)`, `get_summary()`, `export_csv()`

---

### 4.14 KnowledgeGapDetector

**File:** `backend/knowledge_gap_detector.py`

Analyzes query logs to surface knowledge base gaps.

**Detection criteria:**
- Status = `no_results`, OR
- Confidence = `None` or `Low`, OR
- `top_similarity_score < 0.40`

**Clustering:** Queries grouped by first two significant content words. Similar clusters merged by shared words.

**Gap record:**
```python
{
    "gap_id": str,          # Hash-based unique ID
    "topic": str,           # Cluster label
    "frequency": int,       # Number of queries in cluster
    "severity": "High" | "Medium" | "Low",  # ≥3=High, 2=Medium, 1=Low
    "sample_queries": List[str],
    "average_score": float,
    "recommendation": str,
    "latest_query_date": str
}
```

---

## 5. API Reference

### POST `/upload`

Uploads and indexes a document.

**Request:** `multipart/form-data` with `file` field  
**Response:**
```json
{
    "success": true,
    "filename": "Artificial_Intelligence.docx",
    "document_type": "DOCX",
    "chunks_added": 45,
    "total_chunks": 495,
    "message": "Successfully processed and indexed 'Artificial_Intelligence.docx'"
}
```

---

### POST `/query`

Submits a user query through the multi-agent pipeline.

**Request body:**
```json
{
    "query": "What is virtual memory?",
    "session_id": null,
    "is_clarification": false,
    "conv_id": "conv_abc123",
    "top_k": 5,
    "threshold": 0.25
}
```

**Response:**
```json
{
    "query": "What is virtual memory?",
    "query_type": "factual",
    "classification_confidence": 0.9,
    "route": "retrieval",
    "answer": "Virtual memory is a memory management technique...",
    "confidence": "High",
    "sources": [{"document_name": "Operating_Systems.pdf", "page_number": 4, ...}],
    "status": "success",
    "pipeline_stages": [...],
    "conv_id": "conv_abc123"
}
```

---

### GET `/documents`

Returns a list of all indexed documents.

**Response:**
```json
{
    "documents": [
        {"document_name": "Operating_Systems.pdf", "document_type": "PDF", "chunk_count": 89}
    ],
    "total_chunks": 495,
    "total_documents": 8
}
```

---

### DELETE `/documents/<filename>`

Removes a document from the index.

---

### POST `/load-sample`

Loads the pre-built sample knowledge base.

---

### GET `/analytics`

Returns analytics summary.

**Response:**
```json
{
    "summary": {
        "total_queries": 42,
        "answered_queries": 38,
        "answer_rate": 90.5,
        "avg_confidence": "High",
        "avg_similarity": 0.72,
        "avg_duration_sec": 0.18
    },
    "logs": [...],
    "query_type_breakdown": {...},
    "confidence_breakdown": {...}
}
```

---

### GET `/gaps`

Returns knowledge gap analysis.

---

### GET `/analytics/export`

Downloads analytics as CSV.

---

### DELETE `/analytics`

Clears all analytics data.

---

## 6. Configuration Reference

### config.yaml

```yaml
ingestion:
  chunk_size: 400           # Characters per chunk (prose documents)
  chunk_overlap: 50         # Overlap between adjacent chunks

retrieval:
  embedding_model: "all-MiniLM-L6-v2"   # SentenceTransformers model
  faiss_index_type: "flat"               # FAISS index type
  index_path: "data/vector_store/index.faiss"

analytics:
  storage: "sqlite"                       # "sqlite" or "json"
  db_path: "data/analytics/analytics.db"
  export_path: "data/analytics/export.csv"

server:
  host: "127.0.0.1"
  port: 5000

cache:
  maxsize: 500
```

### .env

```env
# LLM API Keys (add ONE to enable real AI generation)
OPENAI_API_KEY=
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=

# Retrieval parameters (override config.yaml defaults)
TOP_K=5
SIMILARITY_THRESHOLD=0.25
CHUNK_SIZE=500
CHUNK_OVERLAP=100
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

## 7. Data Models

### DocumentChunk

```python
@dataclass
class DocumentChunk:
    chunk_id: str           # Unique identifier
    document_name: str      # Original filename
    document_type: str      # "PDF" / "DOCX" / "TXT" / "CSV"
    text: str               # Chunk text content
    page_number: int|None   # For PDFs
    row_number: int|None    # For CSVs
    source_id: str          # Human-readable "filename — Page N"
    extra_metadata: dict    # Additional metadata
```

### RetrievalResult

```python
@dataclass
class RetrievalResult:
    chunk: DocumentChunk
    similarity_score: float   # Adjusted cosine similarity
    relevance: str            # "High" / "Medium" / "Low"
```

### QueryResponse

```python
@dataclass
class QueryResponse:
    answer: str
    confidence: str           # "High" / "Medium" / "Low" / "None"
    sources: List[dict]       # Source attribution records
    debug_details: dict       # Generation metadata
```

---

## 8. Frontend Architecture

**File:** `static/script.js` (~1285 lines), `static/style.css` (~2025 lines), `templates/index.html` (444 lines)

**Key JavaScript Functions:**

| Function | Lines | Description |
|----------|-------|-------------|
| `submitQuery()` | ~380-480 | Sends query to backend, handles response routing |
| `appendAssistantAnswer()` | ~555-715 | Renders answer with badges, source panel, pipeline trace |
| `toggleSources()` | ~722-733 | Expand/collapse source citation panel |
| `toggleSnip()` | ~735-747 | Expand/collapse per-source text snippet |
| `scrollToLatestMessage()` | ~818-832 | Scrolls the new message into view at top of viewport |
| `loadAnalytics()` | ~1000+ | Fetches and renders analytics dashboard |
| `loadGaps()` | ~1050+ | Fetches and renders knowledge gap cards |

**UI Panels:**
- **Upload panel** (left): drag-and-drop + file browser + indexed document list + sample KB loader
- **Chat panel** (center): message thread with answer + citations + pipeline trace + voice controls
- **Analytics modal**: query statistics, recent log table, gap detection cards

---

## 9. Voice Interaction

**Technology:** Web Speech API (browser-native, no external dependency)

**Speech-to-Text (STT):**
- Activated by clicking the microphone button (bottom of chat)
- Uses `SpeechRecognition` / `webkitSpeechRecognition`
- Transcribed text is inserted into the query input and auto-submitted

**Text-to-Speech (TTS):**
- Activated by clicking the 🔊 Listen button on any answer
- Uses `speechSynthesis.speak()` with `SpeechSynthesisUtterance`
- Answer text is cleaned of markdown before speaking
- Clicking again cancels speech

**Browser compatibility:** Chrome, Edge (full support), Firefox (TTS only), Safari (limited)

---

## 10. Error Handling

| Scenario | Handling |
|----------|----------|
| Unsupported file format | `DocumentProcessingError` → HTTP 400 with user-friendly message |
| Empty file | `DocumentProcessingError` → "The file is empty" message |
| File too large (>25 MB) | `DocumentProcessingError` → size limit message |
| Encrypted PDF | `DocumentProcessingError` → "password-protected" message |
| No documents indexed | Query returns `REJECTION_MESSAGE` with "no relevant information" |
| All LLM APIs fail | Falls back to local grounded synthesis |
| Low confidence + no keyword match | Returns grounded rejection to prevent hallucination |
| Max clarification turns exceeded | Returns broad question to user to try again |
| FAISS index empty | `search()` returns empty list → pipeline returns rejection |
| Test environment (offline) | `_generate_fallback_embeddings()` (hash-based) used automatically |
