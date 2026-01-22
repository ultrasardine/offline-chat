# Design Document: RAG Capabilities

## Overview

This design implements a hybrid Retrieval-Augmented Generation (RAG) system for the offline chat application. The system grounds agent responses in trusted knowledge sources by retrieving relevant context before generation. The architecture combines vector similarity search (ChromaDB), local embedding generation (sentence-transformers), web scraping (MCP tools), and database integration to create a comprehensive RAG pipeline.

The design follows a standard RAG workflow:
1. User submits a query
2. Query is embedded using local sentence-transformers model
3. Vector store is searched for similar content chunks
4. Top-k most relevant chunks are retrieved with source metadata
5. Retrieved context is injected into an augmented prompt
6. Augmented prompt is sent to Ollama with strict instructions to use only provided context
7. Agent generates response with source citations
8. Response and source metadata are stored in conversation history

Key design principles:
- **Offline-first**: All components run locally without external API calls
- **Open-source**: All dependencies use permissive open-source licenses
- **Modular**: RAG components are optional and can be enabled per-agent
- **Transparent**: Source citations make information provenance clear
- **Resilient**: Graceful fallback to non-RAG mode on errors

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Chat Interface                           │
│                      (Terminal UI / main.py)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAG Orchestrator                            │
│                   (rag/orchestrator.py)                          │
│  - Coordinates retrieval and augmentation                        │
│  - Manages RAG workflow                                          │
└──┬──────────────┬──────────────┬──────────────┬─────────────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Context  │ │ Embedding│ │ Document │ │   Vector     │
│Retriever │ │Generator │ │Processor │ │    Store     │
│          │ │          │ │          │ │  (ChromaDB)  │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
     │            │            │              │
     └────────────┴────────────┴──────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Knowledge Sources                             │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  Web Documents   │         │  SQLite Database │             │
│  │  (via MCP tools) │         │  (Structured)    │             │
│  └──────────────────┘         └──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ollama LLM                                  │
│              (Receives augmented prompts)                        │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Ingestion Flow** (Setup Phase):
```
Web URL → Web_Scraper → Raw Content → Document_Processor → Chunks
                                                              ↓
Database Table → Row Converter → Text Representations → Chunks
                                                              ↓
                                    Chunks → Embedding_Generator → Embeddings
                                                                      ↓
                                                    Embeddings → Vector_Store
```

**Query Flow** (Runtime):
```
User Query → Embedding_Generator → Query Embedding
                                        ↓
                    Query Embedding → Context_Retriever → Vector_Store
                                                              ↓
                                        Top-k Chunks ← Vector_Store
                                                              ↓
                            Top-k Chunks → Prompt_Augmenter → Augmented Prompt
                                                                      ↓
                                            Augmented Prompt → Ollama → Response
                                                                              ↓
                                                Response + Citations → User
```

## Components and Interfaces

### 1. RAG Orchestrator

**Purpose**: Coordinates the entire RAG workflow from query to response.

**Interface**:
```python
class RAGOrchestrator:
    def __init__(
        self,
        agent_config: AgentConfig,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator,
        context_retriever: ContextRetriever
    ):
        """Initialize RAG orchestrator with required components."""
        pass
    
    def process_query(
        self,
        query: str,
        conversation_history: list[Message]
    ) -> RAGResponse:
        """
        Process a user query through the RAG pipeline.
        
        Args:
            query: User's input query
            conversation_history: Previous messages for context
            
        Returns:
            RAGResponse containing the generated response and source citations
        """
        pass
    
    def ingest_knowledge_sources(
        self,
        sources: list[KnowledgeSource]
    ) -> IngestionResult:
        """
        Ingest knowledge sources into the vector store.
        
        Args:
            sources: List of knowledge sources (URLs or database tables)
            
        Returns:
            IngestionResult with success/failure status for each source
        """
        pass
```

### 2. Embedding Generator

**Purpose**: Generate vector embeddings for text using local sentence-transformers models.

**Interface**:
```python
class EmbeddingGenerator:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with specified sentence-transformers model."""
        pass
    
    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        pass
    
    def generate_embeddings_batch(
        self,
        texts: list[str],
        show_progress: bool = False
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            show_progress: If True, display a progress bar during encoding (default: False)
            
        Returns:
            List of embedding vectors
        """
        pass
    
    def get_embedding_dimension(self) -> int:
        """Return the dimensionality of embeddings produced by this model."""
        pass
```

### 3. Vector Store

**Purpose**: Persist and search vector embeddings using ChromaDB.

**Interface**:
```python
class VectorStore:
    def __init__(self, data_dir: Path):
        """Initialize ChromaDB client with persistent storage."""
        pass
    
    def create_collection(
        self,
        agent_name: str,
        embedding_dimension: int
    ) -> None:
        """Create a new collection for an agent's knowledge base."""
        pass
    
    def add_documents(
        self,
        collection_name: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]]
    ) -> None:
        """
        Add document chunks with embeddings to a collection.
        
        Args:
            collection_name: Name of the collection
            chunks: Document chunks with text and metadata
            embeddings: Corresponding embedding vectors
        """
        pass
    
    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> list[SearchResult]:
        """
        Search for similar documents in a collection.
        
        Args:
            collection_name: Name of the collection to search
            query_embedding: Query vector
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of search results with text, metadata, and similarity scores
        """
        pass
    
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection and all its data."""
        pass
```

### 4. Document Processor

**Purpose**: Chunk documents and prepare them for embedding.

**Interface**:
```python
class DocumentProcessor:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """Initialize with chunking parameters."""
        pass
    
    def process_text_document(
        self,
        content: str,
        source_url: str
    ) -> list[DocumentChunk]:
        """
        Process a text document into chunks.
        
        Args:
            content: Raw text content
            source_url: URL or identifier of the source
            
        Returns:
            List of document chunks with metadata
        """
        pass
    
    def process_database_rows(
        self,
        table_name: str,
        rows: list[dict]
    ) -> list[DocumentChunk]:
        """
        Convert database rows into text chunks.
        
        Args:
            table_name: Name of the database table
            rows: List of row dictionaries
            
        Returns:
            List of document chunks with metadata
        """
        pass
```

### 5. Context Retriever

**Purpose**: Retrieve relevant context for queries from the vector store.

**Interface**:
```python
class ContextRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator
    ):
        """Initialize with vector store and embedding generator."""
        pass
    
    def retrieve_context(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> RetrievalResult:
        """
        Retrieve relevant context for a query.
        
        Args:
            collection_name: Agent's vector collection
            query: User's query text
            top_k: Number of chunks to retrieve
            min_similarity: Minimum similarity threshold
            
        Returns:
            RetrievalResult with chunks and metadata
        """
        pass
```

### 6. Web Scraper

**Purpose**: Fetch content from approved URLs using MCP tools.

**Interface**:
```python
class WebScraper:
    def __init__(self, mcp_client: MCPClient):
        """Initialize with MCP client for web fetching."""
        pass
    
    def scrape_url(
        self,
        url: str,
        max_retries: int = 3
    ) -> ScrapedContent:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            max_retries: Maximum retry attempts
            
        Returns:
            ScrapedContent with text and metadata
        """
        pass
    
    def scrape_urls_batch(
        self,
        urls: list[str]
    ) -> list[ScrapedContent]:
        """Scrape multiple URLs with rate limiting."""
        pass
```

### 7. Prompt Augmenter

**Purpose**: Construct augmented prompts with retrieved context.

**Interface**:
```python
class PromptAugmenter:
    def augment_prompt(
        self,
        query: str,
        context_chunks: list[DocumentChunk],
        system_prompt: str
    ) -> str:
        """
        Create an augmented prompt with context and instructions.
        
        Args:
            query: Original user query
            context_chunks: Retrieved context chunks
            system_prompt: Agent's base system prompt
            
        Returns:
            Augmented prompt string ready for Ollama
        """
        pass
    
    def format_context_chunk(
        self,
        chunk: DocumentChunk,
        index: int
    ) -> str:
        """Format a single context chunk with source attribution."""
        pass
```

## Data Models

### AgentConfig (Extended)

```python
@dataclass
class RAGConfig:
    """RAG-specific configuration for an agent."""
    enabled: bool = False
    top_k: int = 5
    min_similarity: float = 0.3
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str = "all-MiniLM-L6-v2"
    knowledge_sources: list[KnowledgeSource] = field(default_factory=list)

@dataclass
class AgentConfig:
    """Extended agent configuration with RAG support."""
    name: str
    display_name: str
    base_model: str
    system_prompt: str
    temperature: float = 0.7
    created_at: datetime = field(default_factory=datetime.now)
    rag_config: RAGConfig | None = None  # New field
```

### KnowledgeSource

```python
@dataclass
class KnowledgeSource:
    """Represents a knowledge source for RAG."""
    source_type: Literal["web", "database"]
    identifier: str  # URL for web, table name for database
    last_indexed: datetime | None = None
    status: Literal["active", "failed", "pending"] = "pending"
    error_message: str | None = None
```

### DocumentChunk

```python
@dataclass
class DocumentChunk:
    """A chunk of text with metadata."""
    text: str
    source_type: Literal["web", "database"]
    source_identifier: str  # URL or table name
    chunk_index: int
    metadata: dict[str, Any]  # Additional metadata (row ID, etc.)
```

### SearchResult

```python
@dataclass
class SearchResult:
    """Result from vector similarity search."""
    chunk: DocumentChunk
    similarity_score: float
    rank: int
```

### RetrievalResult

```python
@dataclass
class RetrievalResult:
    """Result of context retrieval."""
    chunks: list[SearchResult]
    query: str
    total_results: int
    retrieval_time_ms: float
```

### RAGResponse

```python
@dataclass
class RAGResponse:
    """Response from RAG-enhanced generation."""
    content: str
    sources: list[SourceCitation]
    retrieval_result: RetrievalResult
    generation_time_ms: float

@dataclass
class SourceCitation:
    """Citation to a knowledge source."""
    source_type: Literal["web", "database"]
    identifier: str
    relevance_score: float
```

### Message (Extended)

```python
@dataclass
class Message:
    """Extended message with RAG metadata."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    sources: list[SourceCitation] | None = None  # New field for RAG responses
```

## Correctness Properties


A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Agent Configuration Round-Trip

*For any* agent configuration with RAG settings (knowledge sources, parameters), serializing to JSON then deserializing should produce an equivalent configuration with all RAG settings preserved.

**Validates: Requirements 1.1, 1.2, 1.4, 1.5**

### Property 2: URL Validation Rejects Invalid Formats

*For any* string that is not a valid URL format, attempting to add it as a web knowledge source should be rejected by the validation logic.

**Validates: Requirements 1.3**

### Property 3: Document Chunking Preserves Content

*For any* text document, the concatenation of all chunk texts (in order) should contain all the original content without loss.

**Validates: Requirements 2.2**

### Property 4: Chunk Metadata Invariant

*For any* document processed into chunks, every chunk should contain the source identifier (URL or table name) in its metadata.

**Validates: Requirements 2.3, 3.5, 4.4**

### Property 5: Embedding Count Matches Chunk Count

*For any* list of document chunks, generating embeddings should produce exactly one embedding vector per chunk.

**Validates: Requirements 2.4, 3.4**

### Property 6: Vector Store Round-Trip

*For any* set of document chunks with embeddings, storing them in the vector store then retrieving by exact match should return chunks with identical text and metadata.

**Validates: Requirements 2.5, 7.5**

### Property 7: Database Table Validation

*For any* table name that does not exist in the SQLite database, attempting to add it as a knowledge source should be rejected by validation.

**Validates: Requirements 3.1**

### Property 8: Database Row Text Representation Completeness

*For any* database row, the text representation should contain all column names and their corresponding values.

**Validates: Requirements 3.2, 3.3**

### Property 9: Query Embedding Generation

*For any* non-empty query string, the embedding generator should produce a vector of the expected dimensionality.

**Validates: Requirements 4.1**

### Property 10: Top-K Retrieval Limit

*For any* query and vector store with N chunks, retrieving top-k results should return at most min(k, N) results.

**Validates: Requirements 4.2**

### Property 11: Search Results Ordering

*For any* search results returned by the context retriever, the results should be ordered by similarity score in descending order (highest similarity first).

**Validates: Requirements 4.3**

### Property 12: Augmented Prompt Contains Context

*For any* query with retrieved context chunks, the augmented prompt should contain the text of all retrieved chunks.

**Validates: Requirements 5.1**

### Property 13: Augmented Prompt Contains Source Attribution

*For any* augmented prompt with context chunks, each chunk should be formatted with its source identifier (URL or table name).

**Validates: Requirements 5.2**

### Property 14: RAG Prompt Instructions Completeness

*For any* RAG-enabled agent, the system prompt should contain instructions to: (1) respond only based on provided context, (2) cite sources, (3) acknowledge uncertainty, (4) never fabricate information, and (5) quote or paraphrase from context.

**Validates: Requirements 5.3, 5.4, 12.1, 12.3, 12.4, 12.5**

### Property 15: Source Citation Completeness

*For any* source citation, if the source type is "database" then the citation should include the table name, and if the source type is "web" then the citation should include the URL.

**Validates: Requirements 6.3, 6.4**

### Property 16: Agent Collection Creation

*For any* agent created with RAG enabled, a corresponding vector store collection should be created with the agent's name.

**Validates: Requirements 7.2**

### Property 17: Batch Embedding Consistency

*For any* list of texts, generating embeddings in batch should produce the same results as generating embeddings individually for each text.

**Validates: Requirements 8.4**

### Property 18: RAG Configuration Parameters

*For any* RAG configuration, all parameters (top_k, min_similarity, chunk_size, chunk_overlap) should be stored and retrieved correctly.

**Validates: Requirements 10.1, 10.2, 10.3, 10.4**

### Property 19: Conversation History Round-Trip with RAG Metadata

*For any* conversation history containing RAG-enhanced messages with source citations, saving then loading the history should preserve all source citation information.

**Validates: Requirements 11.1, 11.3, 11.4**

### Property 20: Conversation History Display Includes Sources

*For any* RAG-enhanced message in conversation history, the formatted display should include the source citations used for that response.

**Validates: Requirements 11.2**

## Error Handling

### Error Categories

1. **Network Errors**: Web scraping failures, timeouts
2. **Storage Errors**: Vector store unavailable, disk full, corrupted collections
3. **Validation Errors**: Invalid URLs, non-existent tables, malformed configurations
4. **Generation Errors**: Embedding model failures, Ollama unavailable
5. **Data Errors**: Corrupted embeddings, missing metadata

### Error Handling Strategy

**Graceful Degradation**:
- If vector store is unavailable, fall back to non-RAG mode
- If specific knowledge sources fail, continue with available sources
- If embedding generation fails, return user-friendly error and allow retry

**Retry Logic**:
- Web scraping: 3 retries with exponential backoff (1s, 2s, 4s)
- Vector store operations: 2 retries with 500ms delay
- Embedding generation: No retries (fail fast)

**Error Logging**:
- All errors logged with full stack traces to debug log
- User-facing errors show friendly messages without technical details
- Error context includes: timestamp, operation, affected resources

**Recovery Options**:
- Corrupted vector collection: Provide rebuild option
- Failed knowledge source: Mark as failed, allow re-indexing
- Missing embedding model: Automatic download on first use

### Error Response Format

```python
@dataclass
class RAGError:
    """Structured error information."""
    error_type: Literal["network", "storage", "validation", "generation", "data"]
    message: str  # User-friendly message
    details: str  # Technical details for logging
    recoverable: bool
    recovery_action: str | None  # Suggested recovery action
```

## Testing Strategy

### Dual Testing Approach

The RAG system requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific examples of document chunking with known inputs
- Integration between components (orchestrator coordinating retrieval)
- Edge cases (empty documents, single-word queries, no results)
- Error conditions (network failures, invalid configurations)
- Example web scraping scenarios with mock responses

**Property-Based Tests** focus on:
- Universal properties that hold for all inputs
- Round-trip properties (serialization, vector store persistence)
- Invariants (metadata preservation, ordering guarantees)
- Input validation across random valid/invalid inputs
- Comprehensive coverage through randomization

### Property-Based Testing Configuration

**Framework**: Use Hypothesis for Python property-based testing

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `# Feature: rag-capabilities, Property {N}: {property_text}`

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st
import pytest

@given(
    chunks=st.lists(
        st.builds(DocumentChunk, ...),
        min_size=1,
        max_size=100
    )
)
@pytest.mark.property_test
def test_chunk_metadata_invariant(chunks):
    """
    Feature: rag-capabilities, Property 4: Chunk Metadata Invariant
    
    For any document processed into chunks, every chunk should contain
    the source identifier in its metadata.
    """
    for chunk in chunks:
        assert "source_identifier" in chunk.metadata
        assert chunk.metadata["source_identifier"] is not None
```

### Test Organization

```
tests/
├── unit/
│   ├── test_document_processor.py
│   ├── test_embedding_generator.py
│   ├── test_vector_store.py
│   ├── test_context_retriever.py
│   ├── test_prompt_augmenter.py
│   └── test_web_scraper.py
├── property/
│   ├── test_config_properties.py
│   ├── test_chunking_properties.py
│   ├── test_embedding_properties.py
│   ├── test_retrieval_properties.py
│   └── test_persistence_properties.py
├── integration/
│   ├── test_rag_orchestrator.py
│   └── test_end_to_end_rag.py
└── fixtures/
    ├── sample_documents.py
    ├── mock_web_content.py
    └── test_databases.py
```

### Key Testing Considerations

**Mocking External Dependencies**:
- Mock MCP client for web scraping tests
- Use in-memory ChromaDB for faster tests
- Mock Ollama client for prompt augmentation tests

**Test Data Generation**:
- Use Hypothesis strategies for generating random documents
- Create fixtures for realistic web content and database schemas
- Generate edge cases (empty strings, very long texts, special characters)

**Performance Testing**:
- Measure retrieval time with 10,000 chunk vector store
- Measure embedding generation time for various text lengths
- Test concurrent access patterns

**Integration Testing**:
- Test full RAG pipeline from query to response
- Test knowledge source ingestion end-to-end
- Test error recovery scenarios

### Coverage Goals

- Unit test coverage: >80% for all RAG components
- Property test coverage: All 20 correctness properties implemented
- Integration test coverage: All major workflows (ingestion, retrieval, augmentation)
- Error handling coverage: All error types and recovery paths
