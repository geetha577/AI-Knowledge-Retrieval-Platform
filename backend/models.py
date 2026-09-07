"""
models.py
Defines the core data models and schemas used across the RAG pipeline.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


@dataclass
class DocumentChunk:
    """
    Represents an atomic text chunk derived from an ingested document,
    complete with rich attribution metadata.
    """
    chunk_id: str
    document_name: str
    document_type: str
    text: str
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    source_id: str = ""
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        return cls(**data)


@dataclass
class RetrievalResult:
    """
    Represents a candidate chunk retrieved by semantic search,
    paired with its similarity score and qualitative relevance tag.
    """
    chunk: DocumentChunk
    similarity_score: float
    relevance: str  # "High", "Medium", "Low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "document_name": self.chunk.document_name,
            "document_type": self.chunk.document_type,
            "text": self.chunk.text,
            "page_number": self.chunk.page_number,
            "row_number": self.chunk.row_number,
            "source_id": self.chunk.source_id,
            "similarity_score": round(self.similarity_score, 4),
            "relevance": self.relevance,
        }


@dataclass
class QueryResponse:
    """
    Represents the final structured response returned to the user,
    including answer, confidence, sources, and explainability data.
    """
    answer: str
    confidence: str  # "High", "Medium", "Low", "None"
    sources: List[Dict[str, Any]]
    debug_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# Multi-Agent Architecture & Orchestration Data Models (M1.2)
# ============================================================

@dataclass
class DocumentMetadata:
    """Represents ingested document metadata and ingestion provenance."""
    document_name: str
    document_type: str
    file_size_bytes: int
    total_chunks: int
    total_pages: Optional[int] = None
    upload_timestamp: Optional[str] = None
    hash_checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserQuery:
    """Represents a structured user query after preprocessing."""
    raw_query: str
    cleaned_query: str
    intent_category: str = "factual"  # "factual", "procedural", "comparative", "clarification"
    detected_entities: List[str] = field(default_factory=list)
    requires_clarification: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentMessage:
    """Inter-agent communication message used by the Multi-Agent Orchestrator."""
    sender_agent: str      # e.g., "QueryUnderstandingAgent", "RetrievalAgent"
    recipient_agent: str   # e.g., "ResponseGenerationAgent", "ClarificationAgent"
    action: str            # e.g., "retrieve", "clarify", "synthesize", "memorize"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClarificationRequest:
    """Generated when a query is ambiguous or underspecified."""
    original_query: str
    clarification_question: str
    suggested_options: List[str] = field(default_factory=list)
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

