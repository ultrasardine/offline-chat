"""
Unit tests for RAG data models.
"""

from datetime import datetime

from offline_chat.rag.models import (
    DocumentChunk,
    IngestionResult,
    KnowledgeSource,
    RAGConfig,
    RAGError,
    RAGResponse,
    RetrievalResult,
    ScrapedContent,
    SearchResult,
    SourceCitation,
)


class TestRAGConfig:
    """Tests for RAGConfig dataclass."""

    def test_default_values(self):
        """Test that RAGConfig has correct default values."""
        config = RAGConfig()

        assert config.enabled is False
        assert config.top_k == 5
        assert config.min_similarity == 0.3
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.knowledge_sources == []

    def test_custom_values(self):
        """Test RAGConfig with custom values."""
        sources = [
            KnowledgeSource(source_type="web", identifier="https://example.com"),
            KnowledgeSource(source_type="database", identifier="users"),
        ]

        config = RAGConfig(
            enabled=True,
            top_k=10,
            min_similarity=0.5,
            chunk_size=1024,
            chunk_overlap=100,
            embedding_model="custom-model",
            knowledge_sources=sources,
        )

        assert config.enabled is True
        assert config.top_k == 10
        assert config.min_similarity == 0.5
        assert config.chunk_size == 1024
        assert config.chunk_overlap == 100
        assert config.embedding_model == "custom-model"
        assert len(config.knowledge_sources) == 2

    def test_knowledge_sources_default_factory(self):
        """Test that knowledge_sources uses default_factory to avoid shared list."""
        config1 = RAGConfig()
        config2 = RAGConfig()

        config1.knowledge_sources.append(
            KnowledgeSource(source_type="web", identifier="https://example.com")
        )

        # config2 should have an empty list, not share config1's list
        assert len(config1.knowledge_sources) == 1
        assert len(config2.knowledge_sources) == 0

    def test_validation_top_k_positive(self):
        """Test that top_k should be positive."""
        # Valid positive values
        config = RAGConfig(top_k=1)
        assert config.top_k == 1

        config = RAGConfig(top_k=100)
        assert config.top_k == 100

        # Zero and negative values are technically allowed by the dataclass
        # but should be validated by the application logic
        config = RAGConfig(top_k=0)
        assert config.top_k == 0  # Dataclass allows it

        config = RAGConfig(top_k=-5)
        assert config.top_k == -5  # Dataclass allows it

    def test_validation_min_similarity_range(self):
        """Test that min_similarity should be between 0 and 1."""
        # Valid values
        config = RAGConfig(min_similarity=0.0)
        assert config.min_similarity == 0.0

        config = RAGConfig(min_similarity=0.5)
        assert config.min_similarity == 0.5

        config = RAGConfig(min_similarity=1.0)
        assert config.min_similarity == 1.0

        # Out of range values are technically allowed by the dataclass
        # but should be validated by the application logic
        config = RAGConfig(min_similarity=-0.1)
        assert config.min_similarity == -0.1  # Dataclass allows it

        config = RAGConfig(min_similarity=1.5)
        assert config.min_similarity == 1.5  # Dataclass allows it

    def test_validation_chunk_size_positive(self):
        """Test that chunk_size should be positive."""
        # Valid positive values
        config = RAGConfig(chunk_size=128)
        assert config.chunk_size == 128

        config = RAGConfig(chunk_size=2048)
        assert config.chunk_size == 2048

        # Zero and negative values are technically allowed by the dataclass
        # but should be validated by the application logic
        config = RAGConfig(chunk_size=0)
        assert config.chunk_size == 0  # Dataclass allows it

        config = RAGConfig(chunk_size=-100)
        assert config.chunk_size == -100  # Dataclass allows it

    def test_validation_chunk_overlap_non_negative(self):
        """Test that chunk_overlap should be non-negative and less than chunk_size."""
        # Valid values
        config = RAGConfig(chunk_size=512, chunk_overlap=0)
        assert config.chunk_overlap == 0

        config = RAGConfig(chunk_size=512, chunk_overlap=50)
        assert config.chunk_overlap == 50

        config = RAGConfig(chunk_size=512, chunk_overlap=256)
        assert config.chunk_overlap == 256

        # Overlap equal to chunk_size (edge case)
        config = RAGConfig(chunk_size=512, chunk_overlap=512)
        assert config.chunk_overlap == 512  # Dataclass allows it

        # Overlap greater than chunk_size (should be validated by application)
        config = RAGConfig(chunk_size=512, chunk_overlap=600)
        assert config.chunk_overlap == 600  # Dataclass allows it

        # Negative overlap
        config = RAGConfig(chunk_overlap=-10)
        assert config.chunk_overlap == -10  # Dataclass allows it

    def test_validation_embedding_model_non_empty(self):
        """Test that embedding_model should be a non-empty string."""
        # Valid model names
        config = RAGConfig(embedding_model="all-MiniLM-L6-v2")
        assert config.embedding_model == "all-MiniLM-L6-v2"

        config = RAGConfig(embedding_model="custom-model")
        assert config.embedding_model == "custom-model"

        # Empty string (should be validated by application)
        config = RAGConfig(embedding_model="")
        assert config.embedding_model == ""  # Dataclass allows it

    def test_configuration_combinations(self):
        """Test various valid configuration combinations."""
        # Minimal RAG config
        config = RAGConfig(enabled=True)
        assert config.enabled is True
        assert config.top_k == 5  # Default

        # High precision config
        config = RAGConfig(
            enabled=True,
            top_k=3,
            min_similarity=0.8,
            chunk_size=256,
            chunk_overlap=25,
        )
        assert config.top_k == 3
        assert config.min_similarity == 0.8
        assert config.chunk_size == 256
        assert config.chunk_overlap == 25

        # Large context config
        config = RAGConfig(
            enabled=True,
            top_k=20,
            min_similarity=0.1,
            chunk_size=2048,
            chunk_overlap=200,
        )
        assert config.top_k == 20
        assert config.min_similarity == 0.1
        assert config.chunk_size == 2048
        assert config.chunk_overlap == 200


class TestKnowledgeSource:
    """Tests for KnowledgeSource dataclass."""

    def test_web_source_creation(self):
        """Test creating a web knowledge source."""
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com/docs"
        )

        assert source.source_type == "web"
        assert source.identifier == "https://example.com/docs"
        assert source.last_indexed is None
        assert source.status == "pending"
        assert source.error_message is None

    def test_database_source_creation(self):
        """Test creating a database knowledge source."""
        source = KnowledgeSource(
            source_type="database",
            identifier="products"
        )

        assert source.source_type == "database"
        assert source.identifier == "products"
        assert source.status == "pending"

    def test_source_with_all_fields(self):
        """Test knowledge source with all fields populated."""
        now = datetime.now()
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com",
            last_indexed=now,
            status="active",
            error_message=None,
        )

        assert source.last_indexed == now
        assert source.status == "active"

    def test_failed_source(self):
        """Test knowledge source with failed status."""
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com",
            status="failed",
            error_message="Connection timeout",
        )

        assert source.status == "failed"
        assert source.error_message == "Connection timeout"


class TestDocumentChunk:
    """Tests for DocumentChunk dataclass."""

    def test_web_chunk_creation(self):
        """Test creating a document chunk from web source."""
        chunk = DocumentChunk(
            text="This is a sample text chunk.",
            source_type="web",
            source_identifier="https://example.com",
            chunk_index=0,
        )

        assert chunk.text == "This is a sample text chunk."
        assert chunk.source_type == "web"
        assert chunk.source_identifier == "https://example.com"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {}

    def test_database_chunk_creation(self):
        """Test creating a document chunk from database source."""
        chunk = DocumentChunk(
            text="User: John Doe, Email: john@example.com",
            source_type="database",
            source_identifier="users",
            chunk_index=5,
            metadata={"row_id": 123, "table": "users"},
        )

        assert chunk.source_type == "database"
        assert chunk.source_identifier == "users"
        assert chunk.chunk_index == 5
        assert chunk.metadata["row_id"] == 123
        assert chunk.metadata["table"] == "users"

    def test_metadata_default_factory(self):
        """Test that metadata uses default_factory to avoid shared dict."""
        chunk1 = DocumentChunk(
            text="Text 1",
            source_type="web",
            source_identifier="url1",
            chunk_index=0,
        )
        chunk2 = DocumentChunk(
            text="Text 2",
            source_type="web",
            source_identifier="url2",
            chunk_index=0,
        )

        chunk1.metadata["key"] = "value"

        # chunk2 should have an empty dict, not share chunk1's dict
        assert "key" in chunk1.metadata
        assert "key" not in chunk2.metadata


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating a search result."""
        chunk = DocumentChunk(
            text="Sample text",
            source_type="web",
            source_identifier="https://example.com",
            chunk_index=0,
        )

        result = SearchResult(
            chunk=chunk,
            similarity_score=0.85,
            rank=1,
        )

        assert result.chunk == chunk
        assert result.similarity_score == 0.85
        assert result.rank == 1


class TestRetrievalResult:
    """Tests for RetrievalResult dataclass."""

    def test_retrieval_result_creation(self):
        """Test creating a retrieval result."""
        chunk = DocumentChunk(
            text="Sample text",
            source_type="web",
            source_identifier="https://example.com",
            chunk_index=0,
        )

        search_result = SearchResult(
            chunk=chunk,
            similarity_score=0.85,
            rank=1,
        )

        result = RetrievalResult(
            chunks=[search_result],
            query="test query",
            total_results=1,
            retrieval_time_ms=45.2,
        )

        assert len(result.chunks) == 1
        assert result.query == "test query"
        assert result.total_results == 1
        assert result.retrieval_time_ms == 45.2


class TestSourceCitation:
    """Tests for SourceCitation dataclass."""

    def test_web_citation(self):
        """Test creating a web source citation."""
        citation = SourceCitation(
            source_type="web",
            identifier="https://example.com/docs",
            relevance_score=0.92,
        )

        assert citation.source_type == "web"
        assert citation.identifier == "https://example.com/docs"
        assert citation.relevance_score == 0.92

    def test_database_citation(self):
        """Test creating a database source citation."""
        citation = SourceCitation(
            source_type="database",
            identifier="products",
            relevance_score=0.78,
        )

        assert citation.source_type == "database"
        assert citation.identifier == "products"
        assert citation.relevance_score == 0.78

    def test_format_for_display_web(self):
        """Test formatting web citation for display."""
        citation = SourceCitation(
            source_type="web",
            identifier="https://example.com/docs",
            relevance_score=0.92,
        )

        formatted = citation.format_for_display()
        assert formatted == "[Web] https://example.com/docs"
        assert "Web" in formatted
        assert citation.identifier in formatted

    def test_format_for_display_database(self):
        """Test formatting database citation for display."""
        citation = SourceCitation(
            source_type="database",
            identifier="products_table",
            relevance_score=0.78,
        )

        formatted = citation.format_for_display()
        assert formatted == "[Database] products_table"
        assert "Database" in formatted
        assert citation.identifier in formatted

    def test_format_with_relevance_web(self):
        """Test formatting web citation with relevance score."""
        citation = SourceCitation(
            source_type="web",
            identifier="https://example.com/docs",
            relevance_score=0.92,
        )

        formatted = citation.format_with_relevance()
        assert formatted == "[Web] https://example.com/docs (relevance: 0.92)"
        assert "0.92" in formatted
        assert "relevance" in formatted

    def test_format_with_relevance_database(self):
        """Test formatting database citation with relevance score."""
        citation = SourceCitation(
            source_type="database",
            identifier="users",
            relevance_score=0.78,
        )

        formatted = citation.format_with_relevance()
        assert formatted == "[Database] users (relevance: 0.78)"
        assert "0.78" in formatted
        assert "relevance" in formatted

    def test_format_with_relevance_rounds_to_two_decimals(self):
        """Test that relevance score is formatted to 2 decimal places."""
        citation = SourceCitation(
            source_type="web",
            identifier="https://example.com",
            relevance_score=0.123456,
        )

        formatted = citation.format_with_relevance()
        assert "0.12" in formatted
        assert "0.123456" not in formatted

    def test_format_with_high_relevance(self):
        """Test formatting citation with high relevance score."""
        citation = SourceCitation(
            source_type="web",
            identifier="https://docs.python.org",
            relevance_score=0.99,
        )

        formatted = citation.format_with_relevance()
        assert "[Web] https://docs.python.org (relevance: 0.99)" == formatted

    def test_format_with_low_relevance(self):
        """Test formatting citation with low relevance score."""
        citation = SourceCitation(
            source_type="database",
            identifier="logs",
            relevance_score=0.31,
        )

        formatted = citation.format_with_relevance()
        assert "[Database] logs (relevance: 0.31)" == formatted

    def test_format_preserves_url_structure(self):
        """Test that formatting preserves complex URL structures."""
        citation = SourceCitation(
            source_type="web",
            identifier="https://example.com/docs/api/v2/reference?section=auth#overview",
            relevance_score=0.85,
        )

        formatted = citation.format_for_display()
        assert citation.identifier in formatted
        assert "?" in formatted
        assert "#" in formatted

    def test_format_preserves_table_name_with_special_chars(self):
        """Test that formatting preserves table names with underscores and numbers."""
        citation = SourceCitation(
            source_type="database",
            identifier="user_profiles_2024",
            relevance_score=0.75,
        )

        formatted = citation.format_for_display()
        assert "user_profiles_2024" in formatted


class TestRAGResponse:
    """Tests for RAGResponse dataclass."""

    def test_rag_response_creation(self):
        """Test creating a RAG response."""
        chunk = DocumentChunk(
            text="Sample text",
            source_type="web",
            source_identifier="https://example.com",
            chunk_index=0,
        )

        search_result = SearchResult(
            chunk=chunk,
            similarity_score=0.85,
            rank=1,
        )

        retrieval_result = RetrievalResult(
            chunks=[search_result],
            query="test query",
            total_results=1,
            retrieval_time_ms=45.2,
        )

        citation = SourceCitation(
            source_type="web",
            identifier="https://example.com",
            relevance_score=0.85,
        )

        response = RAGResponse(
            content="This is the generated response.",
            sources=[citation],
            retrieval_result=retrieval_result,
            generation_time_ms=120.5,
        )

        assert response.content == "This is the generated response."
        assert len(response.sources) == 1
        assert response.retrieval_result == retrieval_result
        assert response.generation_time_ms == 120.5


class TestScrapedContent:
    """Tests for ScrapedContent dataclass."""

    def test_successful_scrape(self):
        """Test creating scraped content for successful scrape."""
        content = ScrapedContent(
            url="https://example.com",
            text="This is the scraped content.",
            metadata={"title": "Example Page"},
            success=True,
        )

        assert content.url == "https://example.com"
        assert content.text == "This is the scraped content."
        assert content.metadata["title"] == "Example Page"
        assert content.success is True
        assert content.error_message is None

    def test_failed_scrape(self):
        """Test creating scraped content for failed scrape."""
        content = ScrapedContent(
            url="https://example.com",
            text="",
            success=False,
            error_message="Connection timeout",
        )

        assert content.url == "https://example.com"
        assert content.text == ""
        assert content.success is False
        assert content.error_message == "Connection timeout"

    def test_default_values(self):
        """Test ScrapedContent default values."""
        content = ScrapedContent(
            url="https://example.com",
            text="Content",
        )

        assert content.metadata == {}
        assert content.success is True
        assert content.error_message is None


class TestIngestionResult:
    """Tests for IngestionResult dataclass."""

    def test_successful_ingestion(self):
        """Test creating ingestion result for successful ingestion."""
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com",
        )

        result = IngestionResult(
            source=source,
            success=True,
            chunks_processed=42,
            error_message=None,
        )

        assert result.source == source
        assert result.success is True
        assert result.chunks_processed == 42
        assert result.error_message is None

    def test_failed_ingestion(self):
        """Test creating ingestion result for failed ingestion."""
        source = KnowledgeSource(
            source_type="database",
            identifier="invalid_table",
        )

        result = IngestionResult(
            source=source,
            success=False,
            chunks_processed=0,
            error_message="Table does not exist",
        )

        assert result.source == source
        assert result.success is False
        assert result.chunks_processed == 0
        assert result.error_message == "Table does not exist"


class TestRAGError:
    """Tests for RAGError dataclass."""

    def test_network_error(self):
        """Test creating a network error."""
        error = RAGError(
            error_type="network",
            message="Failed to connect to the server",
            details="Connection timeout after 30 seconds",
            recoverable=True,
            recovery_action="Retry the request",
        )

        assert error.error_type == "network"
        assert error.message == "Failed to connect to the server"
        assert error.details == "Connection timeout after 30 seconds"
        assert error.recoverable is True
        assert error.recovery_action == "Retry the request"

    def test_storage_error(self):
        """Test creating a storage error."""
        error = RAGError(
            error_type="storage",
            message="Vector store is unavailable",
            details="ChromaDB connection failed",
            recoverable=True,
            recovery_action="Restart ChromaDB service",
        )

        assert error.error_type == "storage"
        assert error.recoverable is True

    def test_non_recoverable_error(self):
        """Test creating a non-recoverable error."""
        error = RAGError(
            error_type="validation",
            message="Invalid configuration",
            details="chunk_size must be positive",
            recoverable=False,
            recovery_action=None,
        )

        assert error.error_type == "validation"
        assert error.recoverable is False
        assert error.recovery_action is None
