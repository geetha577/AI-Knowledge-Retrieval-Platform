"""
document_processor.py
Handles document validation, safe storage, format-specific text extraction,
and text sanitization for PDF, DOCX, TXT, and CSV files.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any
from werkzeug.utils import secure_filename
import pypdf
import docx
import pandas as pd


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}


class DocumentProcessingError(Exception):
    """Custom exception raised when document ingestion or parsing fails."""
    pass


class DocumentProcessor:
    """
    Parses various document formats into structured textual segments
    with metadata (e.g. page numbers, row indices).
    """

    def __init__(self, upload_dir: str = "data/uploads", max_file_size_mb: int = 25):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def is_allowed(self, filename: str) -> bool:
        """Check if filename has a permitted extension."""
        return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

    def save_file(self, file_storage) -> Path:
        """
        Validates and safely saves an uploaded Flask FileStorage object.
        Returns the absolute Path of the saved file.
        """
        filename = secure_filename(file_storage.filename)
        if not filename:
            raise DocumentProcessingError("Invalid filename provided.")

        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise DocumentProcessingError(
                f"Unsupported file format '{extension}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        destination = self.upload_dir / filename
        file_storage.save(destination)

        # Check if file is empty
        if destination.stat().st_size == 0:
            destination.unlink(missing_ok=True)
            raise DocumentProcessingError("The uploaded file is empty (0 bytes).")

        if destination.stat().st_size > self.max_file_size_bytes:
            destination.unlink(missing_ok=True)
            raise DocumentProcessingError(
                f"File exceeds maximum allowed size of {self.max_file_size_bytes // (1024 * 1024)}MB."
            )

        return destination

    def clean_text(self, text: str) -> str:
        """Sanitizes extracted text by standardizing whitespace and removing control characters."""
        if not text:
            return ""
        # Replace non-breaking spaces and tabs with standard space
        text = text.replace("\xa0", " ").replace("\t", " ")
        # Replace 3 or more newlines with double newline
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        # Collapse multiple spaces
        text = re.sub(r" +", " ", text)
        return text.strip()

    def extract(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Dispatches extraction based on file extension.
        Returns a list of segment dictionaries:
        [
            {
                "text": "...",
                "page_number": int or None,
                "row_number": int or None,
                "section": str or None
            }, ...
        ]
        """
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        elif suffix == ".docx":
            return self._extract_docx(file_path)
        elif suffix == ".txt":
            return self._extract_txt(file_path)
        elif suffix == ".csv":
            return self._extract_csv(file_path)
        else:
            raise DocumentProcessingError(f"Unsupported extension '{suffix}'.")

    def _extract_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extracts text page-by-page from a PDF using pypdf to preserve page numbers."""
        segments = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            total_pages = len(reader.pages)
            if total_pages == 0:
                raise DocumentProcessingError("PDF contains no readable pages.")

            for page_idx, page in enumerate(reader.pages):
                extracted = page.extract_text() or ""
                cleaned = self.clean_text(extracted)
                if cleaned:
                    segments.append({
                        "text": cleaned,
                        "page_number": page_idx + 1,
                        "row_number": None,
                    })

            if not segments:
                raise DocumentProcessingError(
                    "No text could be extracted from the PDF. It may be an image scan or password protected."
                )
            return segments

        except Exception as e:
            if isinstance(e, DocumentProcessingError):
                raise
            raise DocumentProcessingError(f"Error parsing PDF '{file_path.name}': {str(e)}")

    def _extract_docx(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extracts paragraphs and table contents from a Word DOCX document."""
        segments = []
        try:
            doc = docx.Document(str(file_path))

            # Extract paragraphs
            para_texts = []
            for para in doc.paragraphs:
                cleaned = self.clean_text(para.text)
                if cleaned:
                    para_texts.append(cleaned)

            if para_texts:
                combined_paras = "\n\n".join(para_texts)
                segments.append({
                    "text": combined_paras,
                    "page_number": None,
                    "row_number": None,
                })

            # Extract tables if present
            for table_idx, table in enumerate(doc.tables):
                table_rows = []
                for row in table.rows:
                    cells = [self.clean_text(cell.text) for cell in row.cells]
                    if any(cells):
                        table_rows.append(" | ".join(cells))
                if table_rows:
                    segments.append({
                        "text": f"Table {table_idx + 1}:\n" + "\n".join(table_rows),
                        "page_number": None,
                        "row_number": None,
                    })

            if not segments:
                raise DocumentProcessingError("Word document contains no readable text or tables.")
            return segments

        except Exception as e:
            if isinstance(e, DocumentProcessingError):
                raise
            raise DocumentProcessingError(f"Error parsing DOCX '{file_path.name}': {str(e)}")

    def _extract_txt(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extracts text from a plain text file using UTF-8 with Latin-1 fallback."""
        try:
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = file_path.read_text(encoding="latin-1")

            cleaned = self.clean_text(content)
            if not cleaned:
                raise DocumentProcessingError("Text file is empty or contains only whitespace.")

            return [{
                "text": cleaned,
                "page_number": None,
                "row_number": None,
            }]
        except Exception as e:
            if isinstance(e, DocumentProcessingError):
                raise
            raise DocumentProcessingError(f"Error reading TXT '{file_path.name}': {str(e)}")

    def _extract_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parses CSV records into structured, searchable textual rows preserving column names.
        Example row becomes: 'Name: Ravi | Department: CSE | CGPA: 8.7'
        """
        segments = []
        try:
            df = pd.read_csv(str(file_path))
            if df.empty:
                raise DocumentProcessingError("CSV file contains no data rows.")

            # Drop completely empty rows
            df = df.dropna(how="all")

            for row_idx, row in df.iterrows():
                row_parts = []
                for col in df.columns:
                    val = row[col]
                    if pd.notna(val):
                        # Clean string values
                        val_str = str(val).strip()
                        row_parts.append(f"{col}: {val_str}")
                if row_parts:
                    row_text = " | ".join(row_parts)
                    segments.append({
                        "text": row_text,
                        "page_number": None,
                        "row_number": int(row_idx) + 1,
                    })

            if not segments:
                raise DocumentProcessingError("No valid rows found in CSV.")
            return segments

        except Exception as e:
            if isinstance(e, DocumentProcessingError):
                raise
            raise DocumentProcessingError(f"Error parsing CSV '{file_path.name}': {str(e)}")
