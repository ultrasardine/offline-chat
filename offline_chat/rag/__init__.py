"""
RAG (Retrieval-Augmented Generation) module for offline chat.

This module provides components for grounding agent responses in trusted knowledge sources
through vector similarity search, document processing, and prompt augmentation.
"""

from offline_chat.rag.models import (
    RAGConfig,
    KnowledgeSource,
    DocumentChunk,
    SearchResult,
    RetrievalResult,
    SourceCitation,
    RAGResponse,
    ScrapedContent,
    IngestionResult,
    RAGError,
)
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.vector_store import VectorStore
from offline_chat.rag.document_processor import DocumentProcessor
from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.prompt_augmenter import PromptAugmenter
from offline_chat.rag.web_scraper import WebScraper
from offline_chat.rag.database_integration import DatabaseIntegration
from offline_chat.rag.orchestrator import RAGOrchestrator
from offline_chat.rag.validators import is_valid_url, validate_knowledge_source_url

__all__ = [
    # Components
    "EmbeddingGenerator",
    "VectorStore",
    "DocumentProcessor",
    "ContextRetriever",
    "PromptAugmenter",
    "RAGOrchestrator",
    "WebScraper",
    "DatabaseIntegration",
    # Models
    "RAGConfig",
    "KnowledgeSource",
    "DocumentChunk",
    "SearchResult",
    "RetrievalResult",
    "SourceCitation",
    "RAGResponse",
    "ScrapedContent",
    "IngestionResult",
    "RAGError",
    # Validators
    "is_valid_url",
    "validate_knowledge_source_url",
]
