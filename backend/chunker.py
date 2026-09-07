"""
chunker.py
Splits extracted document segments into semantic chunks with overlap
and attaches full attribution metadata (chunk_id, page, row, source).
"""

import re
from typing import List, Dict, Any
from pathlib import Path
from .models import DocumentChunk


class DocumentChunker:
    """
    Chunks textual documents into overlapping segments while preserving
    sentence boundaries and attaching provenance metadata.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, filename: str, segments: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """
        Takes a list of document segments (from DocumentProcessor) and produces
        a list of DocumentChunk instances with attribution metadata.
        """
        extension = Path(filename).suffix.lower()
        doc_type = extension.lstrip(".").upper()
        chunks: List[DocumentChunk] = []
        chunk_counter = 0

        for seg_idx, segment in enumerate(segments):
            text = segment.get("text", "").strip()
            if not text:
                continue

            page_number = segment.get("page_number")
            row_number = segment.get("row_number")

            # For CSV rows: Each row is an atomic factual record. Keep as single chunk if <= chunk_size * 1.5
            if row_number is not None and len(text) <= self.chunk_size * 2:
                chunk_id = f"{filename}_row{row_number}_{chunk_counter}"
                source_id = f"{filename} — Row {row_number}"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_name=filename,
                    document_type=doc_type,
                    text=text,
                    page_number=page_number,
                    row_number=row_number,
                    source_id=source_id,
                ))
                chunk_counter += 1
                continue

            # For prose text (PDF, DOCX, TXT): perform sentence-aware window splitting
            raw_chunks = self._split_text(text)
            for sub_idx, sub_text in enumerate(raw_chunks):
                chunk_id = f"{filename}_seg{seg_idx}_c{sub_idx}_{chunk_counter}"
                if page_number is not None:
                    source_id = f"{filename} — Page {page_number}"
                elif row_number is not None:
                    source_id = f"{filename} — Row {row_number}"
                else:
                    source_id = f"{filename} — Chunk {chunk_counter + 1}"

                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_name=filename,
                    document_type=doc_type,
                    text=sub_text,
                    page_number=page_number,
                    row_number=row_number,
                    source_id=source_id,
                ))
                chunk_counter += 1

        return chunks

    def _split_text(self, text: str) -> List[str]:
        """
        Splits text using a sliding window approach respecting sentence boundaries.
        """
        if len(text) <= self.chunk_size:
            return [text]

        # Break text into sentences/clauses
        sentences = re.split(r"(?<=[.!?\n])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return [text[:self.chunk_size]]

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If a single sentence exceeds chunk_size, split it by characters
            if sentence_len > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                start = 0
                while start < len(sentence):
                    end = start + self.chunk_size
                    chunks.append(sentence[start:end].strip())
                    start += (self.chunk_size - self.chunk_overlap)
                continue

            if current_length + sentence_len + (1 if current_chunk else 0) <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_len + 1
            else:
                if current_chunk:
                    chunk_str = " ".join(current_chunk)
                    chunks.append(chunk_str)

                    # Calculate overlap: backtrack sentences from the end
                    overlap_sentences = []
                    overlap_len = 0
                    for s in reversed(current_chunk):
                        if overlap_len + len(s) + 1 <= self.chunk_overlap:
                            overlap_sentences.insert(0, s)
                            overlap_len += len(s) + 1
                        else:
                            break
                    current_chunk = overlap_sentences + [sentence]
                    current_length = sum(len(s) + 1 for s in current_chunk)
                else:
                    current_chunk = [sentence]
                    current_length = sentence_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
