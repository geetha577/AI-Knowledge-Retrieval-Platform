# Testing Report
## AI-Based Knowledge Retrieval Platform with Query Resolution System

**Date:** October 2026  
**Total Tests:** 96 passing, 0 failing  
**Test Runner:** pytest  
**Environment:** Python 3.10+, Windows 11

---

## Summary

| Test Suite | File | Tests | Status |
|-----------|------|-------|--------|
| M1 Pipeline Tests | `tests/test_pipeline.py` | 39 | ✅ All Pass |
| Clarification Tests | `tests/test_clarification.py` | 21 | ✅ All Pass |
| Multi-Agent Tests | `tests/test_multi_agent.py` | 18 | ✅ All Pass |
| M4 Multi-Domain Tests | `tests/test_milestone4_multidomain.py` | 12 | ✅ All Pass |
| **Total** | | **96** | **✅ 96/96** |

---

## Running the Tests

```powershell
# Activate virtual environment
venv\Scripts\Activate.ps1

# Install pytest if not present
pip install pytest

# Run all tests
python -m pytest tests/ -v

# Run a specific suite
python -m pytest tests/test_pipeline.py -v
python -m pytest tests/test_clarification.py -v
python -m pytest tests/test_multi_agent.py -v
python -m pytest tests/test_milestone4_multidomain.py -v

# Run with short tracebacks
python -m pytest tests/ --tb=short -q
```

---

## Test Suite 1: M1 Pipeline Tests (39 tests)

**File:** `tests/test_pipeline.py`

Tests the core Milestone 1 components independently.

### Document Processor Tests (~9 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_is_allowed_valid_extensions` | PDF, DOCX, TXT, CSV allowed | Pass |
| `test_is_allowed_invalid_extension` | .exe, .zip rejected | Pass |
| `test_save_file_empty_file` | Empty file raises error | Pass |
| `test_extract_pdf_basic` | PDF extraction returns segments with page numbers | Pass |
| `test_extract_docx_basic` | DOCX paragraph extraction | Pass |
| `test_extract_txt_basic` | TXT UTF-8 extraction | Pass |
| `test_extract_csv_basic` | CSV row-level structured extraction | Pass |
| `test_clean_text_whitespace` | Normalizes tabs, newlines, non-breaking spaces | Pass |
| `test_upload_dir_creation` | Upload directory auto-created | Pass |

### Chunker Tests (~6 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_chunk_short_text` | Text < chunk_size → single chunk | Pass |
| `test_chunk_long_text` | Long text split into multiple chunks | Pass |
| `test_chunk_overlap` | Adjacent chunks share overlap text | Pass |
| `test_chunk_csv_row_atomic` | CSV row kept as single chunk | Pass |
| `test_chunk_metadata_preserved` | page_number, source_id, chunk_id set | Pass |
| `test_chunk_empty_segment_skip` | Empty segments skipped | Pass |

### Embedding Engine Tests (~5 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_generate_embeddings_shape` | Output shape (N, 384) | Pass |
| `test_generate_embeddings_normalized` | L2-norm ≈ 1.0 | Pass |
| `test_generate_query_embedding` | Query returns (1, 384) | Pass |
| `test_fallback_embeddings_offline` | Fallback produces correct shape | Pass |
| `test_embedding_consistency` | Same text → same embedding | Pass |

### Vector Store Tests (~6 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_add_documents` | Chunks added, count increases | Pass |
| `test_search_returns_results` | Search returns ranked results | Pass |
| `test_search_empty_index` | Empty index returns [] | Pass |
| `test_remove_document` | Document removed, count decreases | Pass |
| `test_persist_and_load` | Save → Load preserves data | Pass |
| `test_search_top_k` | top_k respected | Pass |

### Knowledge Retriever Tests (~7 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_retrieve_returns_results` | Retrieval finds relevant chunks | Pass |
| `test_retrieve_similarity_threshold` | Low-score chunks filtered | Pass |
| `test_retrieve_confidence_labels` | High/Medium/Low labeling correct | Pass |
| `test_retrieve_lexical_boost` | Document name match boosts score | Pass |
| `test_retrieve_empty_store` | No results when store empty | Pass |
| `test_retrieve_top_k_limit` | Returns at most top_k results | Pass |
| `test_retrieve_oversampling` | fetch_k = max(top_k×4, 20) | Pass |

### Response Generator Tests (~6 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_generate_response_no_context` | Empty results → rejection message | Pass |
| `test_generate_response_with_context` | Returns answer string | Pass |
| `test_local_synthesis_definition` | "what is" → definition format | Pass |
| `test_local_synthesis_list` | "types of" → bulleted list | Pass |
| `test_local_synthesis_noise_filter` | Syllabus lines filtered out | Pass |
| `test_slide_noise_detection` | `_is_slide_noise()` correct | Pass |

---

## Test Suite 2: Clarification Agent Tests (21 tests)

**File:** `tests/test_clarification.py`

Tests the Clarification Agent and Query Understanding Agent.

### Query Understanding Agent Tests (~10 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_classify_factual_what_is` | "What is AI?" → factual | Pass |
| `test_classify_factual_define` | "Define virtual memory" → factual | Pass |
| `test_classify_procedural_how_to` | "How to sort a list?" → procedural | Pass |
| `test_classify_procedural_steps` | "Steps to install Python" → procedural | Pass |
| `test_classify_comparative_vs` | "TCP vs UDP" → comparative | Pass |
| `test_classify_comparative_difference` | "Difference between RAM and ROM" → comparative | Pass |
| `test_classify_ambiguous_pronoun` | "explain it" → ambiguous | Pass |
| `test_classify_ambiguous_vague` | "tell me about this" → ambiguous | Pass |
| `test_classify_multi_meaning_networks` | "networks" → ambiguous (clarification) | Pass |
| `test_classify_multi_meaning_memory` | "memory" → ambiguous | Pass |

### Clarification Agent Tests (~11 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_clarification_networks_options` | "networks" → Computer vs Neural options | Pass |
| `test_clarification_memory_options` | "memory" → RAM/OS/AI options | Pass |
| `test_clarification_python_options` | "python" → programming vs biology options | Pass |
| `test_clarification_security_options` | "security" → Cyber/Network options | Pass |
| `test_clarification_requirement_query` | "what are the requirements?" → clarification | Pass |
| `test_clarification_pronoun_with_docs` | Provides doc suggestions as options | Pass |
| `test_clarification_pronoun_no_docs` | Default domain suggestions shown | Pass |
| `test_clarification_question_not_empty` | Question string always non-empty | Pass |
| `test_clarification_suggestions_list` | Returns list of strings | Pass |
| `test_clarification_confidence_score` | Confidence between 0 and 1 | Pass |
| `test_clarification_needs_flag` | `needs_clarification` is True | Pass |

---

## Test Suite 3: Multi-Agent Orchestrator Tests (18 tests)

**File:** `tests/test_multi_agent.py`

Tests the full multi-agent pipeline.

### Orchestrator Routing Tests (~8 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_orchestrator_factual_route` | Factual query → retrieval route | Pass |
| `test_orchestrator_ambiguous_route` | Ambiguous query → clarification route | Pass |
| `test_orchestrator_clarification_response` | Clarification includes question + options | Pass |
| `test_orchestrator_session_created` | `session_id` returned for ambiguous query | Pass |
| `test_orchestrator_session_resolution` | Clarification resolves to retrieval | Pass |
| `test_orchestrator_max_clarification` | Exceeding max turns returns graceful answer | Pass |
| `test_orchestrator_pipeline_stages` | All 3 stages present in response | Pass |
| `test_orchestrator_analytics_recorded` | Analytics engine receives call | Pass |

### Conversation Memory Tests (~6 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_conv_memory_followup_pronoun` | "explain it" with prior topic → resolved | Pass |
| `test_conv_memory_no_bleed` | Self-contained query not modified | Pass |
| `test_conv_memory_this_topic` | "this topic" replaced with actual topic | Pass |
| `test_conv_memory_stores_turn` | Turn added to memory | Pass |
| `test_conv_memory_max_turns` | Memory capped at 10 turns | Pass |
| `test_conv_memory_acronym_extraction` | "AI" preserved as topic (2-letter acronym) | Pass |

### Response Generation Agent Tests (~4 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_rga_groundedness_check` | Low score + no keyword → rejection | Pass |
| `test_rga_success_with_context` | Valid context → success status | Pass |
| `test_rga_no_results` | Empty retrieval → no_results status | Pass |
| `test_rga_source_attribution` | Sources list populated | Pass |

---

## Test Suite 4: M4 Multi-Domain Tests (12 tests)

**File:** `tests/test_milestone4_multidomain.py`

Tests Milestone 4 specific features: analytics, gap detection, multi-domain retrieval.

### Analytics Tests (~5 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_analytics_engine_records_query` | Query entry appears in logs | Pass |
| `test_analytics_engine_summary` | Summary totals are accurate | Pass |
| `test_analytics_gap_detector_empty` | No gaps for empty log | Pass |
| `test_analytics_gap_detection` | Seeded unanswered queries → gaps detected | Pass |
| `test_analytics_export_csv` | CSV file created with headers | Pass |

### Multi-Domain Retrieval Tests (~4 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_multi_domain_ai_query` | AI domain: retrieval confidence > 0.5 | Pass |
| `test_multi_domain_os_query` | OS domain: retrieval confidence > 0.5 | Pass |
| `test_multi_domain_cybersecurity_query` | Cybersecurity: retrieval confidence > 0.4 | Pass |
| `test_multi_domain_cross_isolation` | OS query doesn't retrieve AI chunks | Pass |

### System Quality Tests (~3 tests)

| Test | Description | Expected |
|------|-------------|----------|
| `test_confidence_levels` | High ≥0.65, Medium ≥0.45, Low <0.45 | Pass |
| `test_knowledge_gap_severity` | High freq=3+, Medium freq=2, Low freq=1 | Pass |
| `test_pipeline_total_duration` | Full pipeline < 5 seconds | Pass |

---

## Test Isolation Strategy

All tests use **in-memory or temporary data** to avoid polluting the production vector store or analytics database:

- `EmbeddingEngine` falls back to deterministic hash-based vectors in offline test environments
- `VectorStore` initialized with a temporary directory path for each test
- `AnalyticsEngine` initialized with `tmp_path` fixtures (pytest's built-in temp directory)
- No actual document files are required for unit tests — text content is injected directly as `DocumentChunk` objects

---

## Edge Cases Covered

| Edge Case | Test | Status |
|-----------|------|--------|
| Empty query | QUA returns ambiguous | ✅ |
| Empty document | DocumentProcessingError raised | ✅ |
| File > 25 MB | DocumentProcessingError raised | ✅ |
| Encrypted PDF | DocumentProcessingError raised | ✅ |
| No indexed documents | Retriever returns no results | ✅ |
| Similarity below threshold | Chunks filtered, rejection returned | ✅ |
| All LLMs unreachable | Falls back to local synthesis | ✅ |
| Max clarification turns exceeded | Graceful fallback message | ✅ |
| Empty CSV | DocumentProcessingError raised | ✅ |
| CSV with null cells | NaN cells skipped | ✅ |
| Self-referential follow-up | Context injection skipped | ✅ |
| Acronym in query ("AI") | Topic correctly extracted as "ai" | ✅ |
| Duplicate chunks in results | Redundancy check skips duplicates | ✅ |
| FAISS empty search | Returns empty list | ✅ |
| Analytics log empty | Gap detector returns [] | ✅ |
