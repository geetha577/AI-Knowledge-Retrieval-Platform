# Milestone 4 — Implementation Report
## AI-Based Knowledge Retrieval Platform with Query Resolution System

**Milestone:** M4 — Analytics, Multi-Domain Testing & System Optimization  
**Date:** October 2026  
**Repository:** https://github.com/geetha577/AI-Knowledge-Retrieval-Platform

---

## Overview

Milestone 4 extends the working M1–M3 RAG platform with:
1. **M4.1** — Query Analytics Engine and Knowledge Gap Detector
2. **M4.2** — Multi-domain knowledge base testing (3+ domains)
3. **M4.3** — System optimization: answer quality, synthesis quality, noise filtering, conversation context
4. **M4.4** — Automated multi-domain test suite
5. **M4.5** — Voice interaction (TTS + STT)
6. **M4.6** — Full documentation suite

All prior milestone functionality (M1–M3) has been preserved intact. No existing features were removed.

---

## M4.1 — Query Analytics Engine

### Implementation

**File:** `backend/analytics_engine.py`

The `AnalyticsEngine` class provides thread-safe analytics storage with a SQLite backend (configurable to JSON for development).

**Features implemented:**

| Feature | Implementation |
|---------|---------------|
| Query event logging | `record_query()` called from `orchestrator.py` after every pipeline run |
| Multi-field tracking | 18 fields per record: query text, type, route, confidence, score, duration, status, sources, session/conv IDs |
| Thread safety | Python `threading.Lock` wraps all read/write operations |
| Storage backends | SQLite (production) + JSON (test fallback) |
| Summary statistics | `get_summary()` returns totals, averages, breakdowns by type/confidence/route |
| CSV export | `export_csv()` dumps full log to `data/analytics/export.csv` |
| Log retrieval | `get_logs(limit)` returns N most recent records |
| Analytics API | `GET /analytics` exposes summary + logs to frontend |
| Dashboard | Frontend analytics modal shows total queries, confidence breakdown, recent log table |

**SQLite Schema:** 18 columns including `query`, `query_type`, `route`, `confidence`, `status`, `top_similarity_score`, `retrieved_chunks_count`, `source_documents`, `duration_sec`, `is_unanswered`, `error`.

### Knowledge Gap Detector

**File:** `backend/knowledge_gap_detector.py`

The `KnowledgeGapDetector` analyzes logged queries to surface recurrent knowledge gaps.

**Detection criteria:**
- `status == "no_results"`, OR
- `confidence ∈ {None, Low}`, OR
- `top_similarity_score < 0.40`

**Clustering algorithm:**
1. Extract content words (≥3 chars, not stopwords) from each problem query
2. Form a 2-word cluster label from top two content words
3. Merge clusters that share any of those words
4. Count frequency, compute average score, label severity (High ≥3, Medium =2, Low =1)
5. Sort by frequency descending

**Output per gap record:**
```json
{
    "gap_id": "gap_78234",
    "topic": "Quantum Computing",
    "frequency": 5,
    "severity": "High",
    "sample_queries": ["what is quantum computing?", "explain qubits"],
    "average_score": 0.12,
    "recommendation": "Consider uploading reference documents covering 'quantum computing'...",
    "latest_query_date": "2026-10-05 14:32:11"
}
```

**UI:** Gap cards appear in the Analytics modal, sorted by severity.

---

## M4.2 — Multi-Domain Knowledge Base Testing

### Knowledge Domains Tested

The system was tested with documents from three distinct knowledge domains:

| Domain | Document | Format | Content Type |
|--------|----------|--------|-------------|
| Artificial Intelligence | `Artificial_Intelligence.docx` | DOCX | Definitions, types, applications, ML, DL |
| Operating Systems | `Operating_Systems.pdf` | PDF | Memory management, scheduling, virtual memory, page faults |
| Cybersecurity | `Cybersecurity_Basics.txt` | TXT | Threats, attacks, encryption, firewalls |
| Student Records | `students.csv` | CSV | Name, ID, CGPA, department structured records |

### Cross-Domain Test Results

**Domain: Artificial Intelligence**

| Query | Retrieval Confidence | Answer Quality |
|-------|---------------------|---------------|
| "What is AI?" | High (0.82) | ✅ Correct definition |
| "Types of AI?" | High (0.78) | ✅ Lists Narrow, General, Super AI |
| "What is machine learning?" | High (0.79) | ✅ Correct definition with examples |
| "Applications of AI?" | Medium (0.65) | ✅ Lists relevant applications |

**Domain: Operating Systems**

| Query | Retrieval Confidence | Answer Quality |
|-------|---------------------|---------------|
| "What is virtual memory?" | High (0.99) | ✅ Correct definition + demand paging |
| "What is a page fault?" | High (0.94) | ✅ Correct explanation |
| "What is CPU scheduling?" | High (0.81) | ✅ Correct |
| "Explain deadlock" | Medium (0.58) | ✅ Correct definition |

**Domain: Cybersecurity**

| Query | Retrieval Confidence | Answer Quality |
|-------|---------------------|---------------|
| "What is a phishing attack?" | High (0.77) | ✅ Correct |
| "What is encryption?" | High (0.71) | ✅ Correct |
| "What is a firewall?" | High (0.68) | ✅ Correct |

**Domain: Student Records (CSV)**

| Query | Retrieval Confidence | Answer Quality |
|-------|---------------------|---------------|
| "Show student records" | High | ✅ Returns structured row data |
| "Find students with CGPA above 9" | Medium | ✅ Returns matching rows |

**Ambiguity detection:**

| Query | Expected Route | Actual Route |
|-------|---------------|-------------|
| "networks" | clarification | ✅ clarification |
| "memory" | clarification | ✅ clarification |
| "explain it" | clarification | ✅ clarification |
| "tell me about security" (with docs) | retrieval | ✅ retrieval |

---

## M4.3 — System Optimization

### A. Answer Quality Improvements

**Problem identified:** The local grounded synthesis was returning near-identical answers for different queries because all questions retrieved the same top chunk from a document.

**Root cause:**  
- No API key configured → always uses local extractive fallback
- Local fallback scored sentences primarily by keyword overlap, which caused highly similar answers for related queries
- CSE3003 PDF began with syllabus/admin pages (CO/PO mapping) → network queries returned course admin text

**Improvements implemented:**

#### 1. Intent-Aware Synthesis (`backend/generator.py`)

The `_local_grounded_synthesis()` method was rewritten with 6 intent flags:

```python
wants_definition  = any(...["what is", "what are", "define", "explain"])
wants_list        = any(...["types", "advantages", "features", "list"])
wants_comparison  = any(...["difference", "compare", "versus"])
wants_procedural  = any(...["how to", "steps to", "process of"])
wants_reason      = any(...["why", "purpose", "importance", "benefit"])
wants_summary     = any(...["summary", "overview", "briefly"])
```

Structured output templates per intent:
- **Reason queries**: Lead sentence + "**Key Applications & Importance:**" bulleted list
- **Summary queries**: Lead sentence + "**Key Highlights:**" bulleted list
- **Definition + list**: Definition paragraph + "**Key Types / Categories:**" bulleted list
- **Comparison**: Contrast sentences prioritized
- **Procedural**: Numbered step list

#### 2. Slide Noise Filtering (`_is_slide_noise`)

Expanded to filter:
- Syllabus metadata: `CO1`, `PO1`, `Course Code`, `Version No`, `TPC`
- Remarks/case study markers: `Remarks: Types of`, `Mini case study:`
- Module/unit/slide headers: `Module - 1`, `Unit 2`, `Chapter 3`
- Short lines < 5 words
- Table data fragments: `Scalars represent`, `Vectors store`, `Weight matrix in a Dense`

#### 3. PDF Artifact Cleaning

Regex updated to strip bullet artifact characters: `?`, ``, `–`, `—` from extracted text before scoring.

Chapter title stripping:
```python
re.sub(r"^chapter\s*\d+[:\s-]*[A-Za-z0-9\s]{0,25}?(?=[A-Z][a-z])", "", s_clean)
```

Duplicate title detection:
```python
if len(words) >= 4 and " ".join(words[:2]).lower() == " ".join(words[2:4]).lower():
    s_clean = " ".join(words[2:])  # Remove duplicated title prefix
```

#### 4. Sentence Scoring Enhancement

Added question-type specific score bonuses:
- `wants_definition + "is a" / "refers to" / "is defined as"` → +3.5
- `wants_reason + "used for" / "enables" / "applications"` → +4.0
- `wants_summary + "overview of" / "management" / "simulation"` → +3.5
- `wants_comparison + "while" / "whereas" / "contrast"` → +3.0

### B. Conversation Context Fix

**Problem:** Follow-up context was being injected into self-contained queries (e.g., asking "What is AI?" after a networks conversation would inject networks context).

**Fix in `backend/conversation_manager.py`:**

`is_followup()` — removed "why", "and", "also" as follow-up triggers. Only bare continuation phrases qualify: "continue", "go on", "yes", "more", "next", "and?".

`resolve_followup()` — added guard:
```python
content_words = [w for w in query.lower().split() if w not in stop_words and len(w) > 2]
has_pronoun = any(p in query.lower() for p in ["it", "this", "that", "they", "them"])
if len(content_words) >= 2 and not has_pronoun:
    return query  # Self-contained — skip context injection
```

Also added "this topic" / "that topic" phrase replacement with the actual prior topic.

### C. Acronym-Aware Topic Extraction

`_extract_topics()` in `ConversationManager` now preserves 2-letter technical terms:
```python
known_acronyms = {"ai", "os", "ml", "dl", "rl", "nlp", "sql", "api", "oop", "cpu", "ram", "gpu"}
```

Meta-words ("summary", "topic", "information", "notes", "explain") added to stopwords to prevent them from becoming the extracted topic.

### D. Resilient LLM Callers

`_call_gemini()` — tries 3 models in sequence:
1. `gemini-1.5-flash` (fastest, free tier)
2. `gemini-2.0-flash` (newer)
3. `gemini-1.5-pro` (most capable)

`_call_groq()` — tries 2 models:
1. `llama-3.1-8b-instant`
2. `llama-3.3-70b-versatile`

### E. Auto-Scroll Fix

`scrollToLatestMessage()` function added to `static/script.js`:
```javascript
function scrollToLatestMessage() {
    const msgs = chatMessages.querySelectorAll('.message');
    if (msgs.length > 0) {
        const last = msgs[msgs.length - 1];
        last.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}
```
Called from `appendAssistantAnswer()` and `appendUserMessage()`.

### F. Citation Simplification

Sources panel is **collapsed by default**. Compact header shows:
```
📄 Sources (5) · Top match: 99% ▶
```
Individual source snippets are hidden inside "show text" toggle buttons. Users can expand/collapse each source independently.

---

## M4.4 — Automated Test Suite

**File:** `tests/test_milestone4_multidomain.py` — 12 tests

Test categories:
1. `test_analytics_engine_records_query` — analytics recording
2. `test_analytics_engine_summary` — summary statistics accuracy
3. `test_analytics_gap_detector_empty` — empty log handling
4. `test_analytics_gap_detection` — gap detection with seeded data
5. `test_analytics_export_csv` — CSV export functionality
6. `test_multi_domain_ai_query` — AI domain retrieval
7. `test_multi_domain_os_query` — OS domain retrieval
8. `test_multi_domain_cybersecurity_query` — Cybersecurity domain retrieval
9. `test_voice_synthesis_available` — TTS API availability
10. `test_confidence_levels` — confidence label accuracy
11. `test_knowledge_gap_severity` — severity classification logic
12. `test_pipeline_total_duration` — pipeline latency under 5 seconds

**Total test suite:** 96 tests (39 + 21 + 18 + 12 + 6 additional) — all passing.

---

## M4.5 — Voice Interaction

**STT (Speech-to-Text):**
- Web Speech API via `SpeechRecognition` / `webkitSpeechRecognition`
- Microphone button at bottom of chat panel
- Transcribed text auto-submitted as query

**TTS (Text-to-Speech):**
- `speechSynthesis.speak()` with `SpeechSynthesisUtterance`
- "Listen" button on every answer
- Markdown stripped before synthesis
- Toggle to stop playback

**Compatibility:** Chrome and Edge have full support. Firefox supports TTS. No external API required.

---

## M4.6 — Documentation

| Document | File | Description |
|----------|------|-------------|
| README | `README.md` | Quick start, architecture, configuration, GitHub guide |
| Technical Docs | `docs/technical_documentation.md` | Full component reference + API |
| M4 Report | `docs/m4_implementation_report.md` | This document |
| Testing Report | `docs/testing_report.md` | 96-test detailed results |
| Optimization Report | `docs/optimization_report.md` | Before/after comparison |
| Final Report | `docs/final_project_report.md` | End-to-end project summary |
| Demo Guide | `docs/demo_guide.md` | Step-by-step demo for submission |
| System Architecture | `SYSTEM_ARCHITECTURE.md` | Architecture reference |

---

## M4 Requirement Checklist

| Requirement | Status | Evidence |
|------------|--------|---------|
| Query analytics engine | ✅ | `analytics_engine.py` — SQLite + JSON |
| Query log per request | ✅ | `record_query()` called in `orchestrator.py` |
| Confidence tracking | ✅ | `confidence` field in every log record |
| Knowledge gap detection | ✅ | `knowledge_gap_detector.py` — clustering algorithm |
| Gap severity levels | ✅ | High/Medium/Low based on frequency |
| Multi-domain testing (3+ domains) | ✅ | AI + OS + Cybersecurity + CSV tested |
| Analytics dashboard UI | ✅ | Analytics modal in `index.html` |
| Gap display in UI | ✅ | Gap cards rendered in analytics modal |
| CSV export | ✅ | `GET /analytics/export` endpoint |
| Voice interaction (TTS) | ✅ | "Listen" button on answers |
| Voice interaction (STT) | ✅ | Microphone button for speech input |
| Auto-scroll to answer | ✅ | `scrollToLatestMessage()` in `script.js` |
| Citation simplification | ✅ | Collapsed by default, per-source expand |
| Agent pipeline trace | ✅ | Expandable trace on each answer |
| 90+ passing tests | ✅ | 96 tests passing |
| Full documentation | ✅ | 7 documents in `docs/` |
| GitHub repository | ✅ | https://github.com/geetha577/AI-Knowledge-Retrieval-Platform |
