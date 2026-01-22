"""
Data models for RAG components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class RAGConfig:
    """RAG-specific configuration for an agent."""
    enabled: bool = False
    top_k: int = 5
    min_similarity: float = 0.3
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str = "all-MiniLM-L6-v2"
    knowledge_sources: list["KnowledgeSource"] = field(default_factory=list)


@dataclass
class KnowledgeSource:
    """Represents a knowledge source for RAG."""
    source_type: Literal["web", "database"]
    identifier: str  # URL for web, table name for database
    last_indexed: datetime | None = None
    status: Literal["active", "failed", "pending"] = "pending"
    error_message: str | None = None


@dataclass
class DocumentChunk:
    """A chunk of text with metadata."""
    text: str
    source_type: Literal["web", "database"]
    source_identifier: str  # URL or table name
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    chunk: DocumentChunk
    similarity_score: float
    rank: int


@dataclass
class RetrievalResult:
    """Result of context retrieval."""
    chunks: list[SearchResult]
    query: str
    total_results: int
    retrieval_time_ms: float


@dataclass
class SourceCitation:
    """Citation to a knowledge source."""
    source_type: Literal["web", "database"]
    identifier: str
    relevance_score: float
    
    def format_for_display(self) -> str:
        """
        Format the citation for display to users.
        
        Returns:
            A formatted string showing the source type and identifier.
            
        Examples:
            Web source: "[Web] https://example.com/docs"
            Database source: "[Database] products_table"
        """
        if self.source_type == "web":
            return f"[Web] {self.identifier}"
        else:  # database
            return f"[Database] {self.identifier}"
    
    def format_with_relevance(self) -> str:
        """
        Format the citation with relevance score for detailed display.
        
        Returns:
            A formatted string including the relevance score.
            
        Examples:
            "[Web] https://example.com/docs (relevance: 0.92)"
            "[Database] products_table (relevance: 0.78)"
        """
        base = self.format_for_display()
        return f"{base} (relevance: {self.relevance_score:.2f})"


@dataclass
class RAGResponse:
    """Response from RAG-enhanced generation."""
    content: str
    sources: list[SourceCitation]
    retrieval_result: RetrievalResult
    generation_time_ms: float


@dataclass
class ScrapedContent:
    """Content scraped from a web URL."""
    url: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str | None = None


@dataclass
class IngestionResult:
    """Result of knowledge source ingestion."""
    source: KnowledgeSource
    success: bool
    chunks_processed: int
    error_message: str | None = None


@dataclass
class RAGError:
    """Structured error information."""
    error_type: Literal["network", "storage", "validation", "generation", "data"]
    message: str  # User-friendly message
    details: str  # Technical details for logging
    recoverable: bool
    recovery_action: str | None = None
