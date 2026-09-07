"""
Backend package for AI-Based Knowledge Retrieval Platform.
Provides modular components for:
- Document extraction and cleaning (document_processor.py)
- Text chunking with metadata (chunker.py)
- Dense vector embedding generation (embeddings.py)
- FAISS vector store indexing and persistence (vector_store.py)
- Semantic similarity retrieval (retriever.py)
- Grounded response generation (generator.py)
- Data schemas and models (models.py)
"""

from .models import DocumentChunk, RetrievalResult, QueryResponse
from .document_processor import DocumentProcessor
from .chunker import DocumentChunker
from .embeddings import EmbeddingEngine
from .vector_store import VectorStore
from .retriever import KnowledgeRetriever
from .generator import ResponseGenerator

__all__ = [
    "DocumentChunk",
    "RetrievalResult",
    "QueryResponse",
    "DocumentProcessor",
    "DocumentChunker",
    "EmbeddingEngine",
    "VectorStore",
    "KnowledgeRetriever",
    "ResponseGenerator",
]
