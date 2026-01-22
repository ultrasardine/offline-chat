# Implementation Plan: RAG Capabilities

## Overview

This implementation plan adds Retrieval-Augmented Generation (RAG) capabilities to the offline chat system. The implementation follows a bottom-up approach, building core components first (embedding generation, vector storage, document processing) before integrating them into the RAG orchestrator and finally extending the agent management system.

The plan prioritizes getting a minimal RAG pipeline working early, then iteratively adding features like web scraping, database integration, and advanced error handling.

## Tasks

- [x] 1. Set up RAG infrastructure and dependencies
  - Install required packages: chromadb, sentence-transformers, hypothesis
  - Create rag/ module directory structure
  - Set up test directory structure for RAG components
  - _Requirements: 7.1, 8.1, 15.1, 15.2_

- [x] 2. Implement Embedding Generator
  - [x] 2.1 Create EmbeddingGenerator class with sentence-transformers integration
    - Implement model loading with configurable model name
    - Implement single text embedding generation
    - Implement batch embedding generation
    - Add embedding dimension retrieval method
    - _Requirements: 8.2, 8.3, 8.4, 8.5_
  
  - [x] 2.2 Write property test for batch embedding consistency
    - **Property 17: Batch Embedding Consistency**
    - **Validates: Requirements 8.4**
  
  - [x] 2.3 Write property test for query embedding generation
    - **Property 9: Query Embedding Generation**
    - **Validates: Requirements 4.1**
  
  - [x] 2.4 Write unit tests for embedding generator
    - Test model loading and caching
    - Test embedding dimension consistency
    - Test error handling for invalid inputs
    - _Requirements: 8.3, 8.5_

- [x] 3. Implement Vector Store with ChromaDB
  - [x] 3.1 Create VectorStore class with ChromaDB client
    - Initialize persistent ChromaDB client in data directory
    - Implement collection creation with agent name
    - Implement document addition with embeddings and metadata
    - Implement similarity search with top-k and threshold filtering
    - Implement collection deletion
    - _Requirements: 7.1, 7.2, 7.4, 7.5_
  
  - [x] 3.2 Write property test for vector store round-trip
    - **Property 6: Vector Store Round-Trip**
    - **Validates: Requirements 2.5, 7.5**
  
  - [x] 3.3 Write property test for top-k retrieval limit
    - **Property 10: Top-K Retrieval Limit**
    - **Validates: Requirements 4.2**
  
  - [x] 3.4 Write unit tests for vector store
    - Test collection creation and deletion
    - Test empty collection behavior
    - Test concurrent read operations
    - _Requirements: 7.2, 7.4, 13.3_

- [x] 4. Implement Document Processor
  - [x] 4.1 Create DocumentProcessor class for text chunking
    - Implement text chunking with configurable size and overlap
    - Implement metadata preservation for each chunk
    - Implement database row to text conversion
    - Ensure column names and values included in text representation
    - _Requirements: 2.2, 2.3, 3.2, 3.3_
  
  - [x] 4.2 Write property test for document chunking preserves content
    - **Property 3: Document Chunking Preserves Content**
    - **Validates: Requirements 2.2**
  
  - [x] 4.3 Write property test for chunk metadata invariant
    - **Property 4: Chunk Metadata Invariant**
    - **Validates: Requirements 2.3, 3.5, 4.4**
  
  - [x] 4.4 Write property test for database row text completeness
    - **Property 8: Database Row Text Representation Completeness**
    - **Validates: Requirements 3.2, 3.3**
  
  - [x] 4.5 Write unit tests for document processor
    - Test chunking with various text sizes
    - Test chunk overlap behavior
    - Test edge cases (empty documents, single-word documents)
    - _Requirements: 2.2, 2.3_

- [x] 5. Checkpoint - Core components complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Context Retriever
  - [x] 6.1 Create ContextRetriever class
    - Integrate EmbeddingGenerator and VectorStore
    - Implement query embedding generation
    - Implement context retrieval with similarity search
    - Implement result ordering by similarity score
    - Return empty results when below threshold
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x] 6.2 Write property test for search results ordering
    - **Property 11: Search Results Ordering**
    - **Validates: Requirements 4.3**
  
  - [x] 6.3 Write property test for embedding count matches chunk count
    - **Property 5: Embedding Count Matches Chunk Count**
    - **Validates: Requirements 2.4, 3.4**
  
  - [x] 6.4 Write unit tests for context retriever
    - Test retrieval with various query types
    - Test empty result handling
    - Test threshold filtering
    - _Requirements: 4.5_

- [x] 7. Implement Prompt Augmenter
  - [x] 7.1 Create PromptAugmenter class
    - Implement context chunk formatting with source attribution
    - Implement augmented prompt construction
    - Include RAG instructions (context-only, cite sources, no hallucination)
    - Format multiple context chunks clearly
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 12.1, 12.3, 12.4, 12.5_
  
  - [x] 7.2 Write property test for augmented prompt contains context
    - **Property 12: Augmented Prompt Contains Context**
    - **Validates: Requirements 5.1**
  
  - [x] 7.3 Write property test for augmented prompt contains source attribution
    - **Property 13: Augmented Prompt Contains Source Attribution**
    - **Validates: Requirements 5.2**
  
  - [x] 7.4 Write property test for RAG prompt instructions completeness
    - **Property 14: RAG Prompt Instructions Completeness**
    - **Validates: Requirements 5.3, 5.4, 12.1, 12.3, 12.4, 12.5**
  
  - [x] 7.5 Write unit tests for prompt augmenter
    - Test prompt formatting with various chunk counts
    - Test handling of no context scenario
    - Test instruction inclusion
    - _Requirements: 5.3, 5.4, 6.5, 12.2_

- [x] 8. Extend Agent Configuration for RAG
  - [x] 8.1 Create RAGConfig dataclass
    - Define RAG configuration parameters (top_k, min_similarity, etc.)
    - Set sensible defaults (k=5, threshold=0.3, chunk_size=512, overlap=50)
    - Create KnowledgeSource dataclass for source tracking
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [x] 8.2 Extend AgentConfig with RAG support
    - Add optional rag_config field to AgentConfig
    - Update agent config serialization/deserialization
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [x] 8.3 Write property test for agent configuration round-trip
    - **Property 1: Agent Configuration Round-Trip**
    - **Validates: Requirements 1.1, 1.2, 1.4, 1.5**
  
  - [x] 8.4 Write property test for RAG configuration parameters
    - **Property 18: RAG Configuration Parameters**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
  
  - [x] 8.5 Write unit tests for RAG configuration
    - Test default values
    - Test configuration validation
    - Test backward compatibility with non-RAG configs
    - _Requirements: 10.5_

- [x] 9. Implement Web Scraper with MCP integration
  - [x] 9.1 Create WebScraper class using MCP fetch tool
    - Integrate with MCP client for web fetching
    - Implement URL scraping with content extraction
    - Implement retry logic with exponential backoff
    - Implement rate limiting for batch scraping
    - Handle HTML and markdown formats
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [x] 9.2 Write property test for URL validation
    - **Property 2: URL Validation Rejects Invalid Formats**
    - **Validates: Requirements 1.3**
  
  - [x] 9.3 Write unit tests for web scraper
    - Test scraping with mock MCP responses
    - Test retry logic with failing requests
    - Test rate limiting behavior
    - Test error handling for network failures
    - _Requirements: 2.6, 9.4, 9.5_

- [x] 10. Implement Database Integration
  - [x] 10.1 Add database table validation
    - Implement SQLite table existence checking
    - Implement table row fetching
    - Convert rows to text representations via DocumentProcessor
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 10.2 Write property test for database table validation
    - **Property 7: Database Table Validation**
    - **Validates: Requirements 3.1**
  
  - [x] 10.3 Write unit tests for database integration
    - Test with sample SQLite database
    - Test table validation with valid/invalid tables
    - Test row conversion to text
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 11. Checkpoint - All components implemented
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement RAG Orchestrator
  - [x] 12.1 Create RAGOrchestrator class
    - Coordinate all RAG components
    - Implement knowledge source ingestion workflow
    - Implement query processing workflow (embed → retrieve → augment → generate)
    - Track ingestion status for each knowledge source
    - _Requirements: 1.5, 2.1, 2.4, 2.5, 2.6, 5.5_
  
  - [x] 12.2 Implement ingestion for web sources
    - Scrape URL content
    - Process into chunks
    - Generate embeddings
    - Store in vector database
    - Handle failures gracefully
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  
  - [x] 12.3 Implement ingestion for database sources
    - Fetch table rows
    - Convert to text representations
    - Generate embeddings
    - Store in vector database with metadata
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 12.4 Implement query processing pipeline
    - Generate query embedding
    - Retrieve relevant context
    - Augment prompt with context
    - Send to Ollama for generation
    - Extract and format source citations
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 12.5 Write integration tests for RAG orchestrator
    - Test end-to-end ingestion workflow
    - Test end-to-end query workflow
    - Test with multiple knowledge sources
    - Test error handling and fallback
    - _Requirements: 2.6, 14.1, 14.2, 14.3_

- [x] 13. Extend Conversation History for RAG
  - [x] 13.1 Extend Message dataclass with source citations
    - Add optional sources field to Message
    - Update conversation history serialization
    - Maintain backward compatibility with non-RAG histories
    - _Requirements: 11.1, 11.3, 11.4, 11.5_
  
  - [x] 13.2 Create SourceCitation dataclass
    - Define citation structure (type, identifier, relevance)
    - Implement citation formatting for display
    - _Requirements: 6.3, 6.4_
  
  - [x] 13.3 Write property test for conversation history round-trip with RAG
    - **Property 19: Conversation History Round-Trip with RAG Metadata**
    - **Validates: Requirements 11.1, 11.3, 11.4**
  
  - [x] 13.4 Write property test for source citation completeness
    - **Property 15: Source Citation Completeness**
    - **Validates: Requirements 6.3, 6.4**
  
  - [x] 13.5 Write property test for conversation history display includes sources
    - **Property 20: Conversation History Display Includes Sources**
    - **Validates: Requirements 11.2**
  
  - [x] 13.6 Write unit tests for extended conversation history
    - Test backward compatibility with old history files
    - Test source citation display formatting
    - Test history with mixed RAG/non-RAG messages
    - _Requirements: 11.5_

- [x] 14. Implement Error Handling and Resilience
  - [x] 14.1 Create RAGError dataclass for structured errors
    - Define error types and recovery actions
    - Implement user-friendly error messages
    - _Requirements: 14.5_
  
  - [x] 14.2 Add fallback to non-RAG mode
    - Detect vector store unavailability
    - Fall back to standard Ollama chat
    - Log warnings for debugging
    - _Requirements: 14.1_
  
  - [x] 14.3 Add error recovery for corrupted collections
    - Detect corrupted ChromaDB collections
    - Provide rebuild option
    - _Requirements: 14.4_
  
  - [x] 14.4 Write unit tests for error handling
    - Test vector store unavailable scenario
    - Test embedding generation failure
    - Test web scraping failure
    - Test corrupted collection recovery
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

- [x] 15. Integrate RAG with Agent Management
  - [x] 15.1 Update agent creation flow to support RAG configuration
    - Add optional RAG setup during agent creation
    - Allow specification of knowledge sources
    - Create vector collection when RAG is enabled
    - _Requirements: 1.1, 1.2, 1.5, 7.2_
  
  - [x] 15.2 Update agent loading to initialize RAG components
    - Load RAG configuration from agent config
    - Initialize RAG orchestrator if enabled
    - Load vector collection
    - _Requirements: 1.5_
  
  - [x] 15.3 Update agent deletion to clean up RAG resources
    - Provide option to delete vector collection
    - Clean up indexed content
    - _Requirements: 7.4_
  
  - [x] 15.4 Write property test for agent collection creation
    - **Property 16: Agent Collection Creation**
    - **Validates: Requirements 7.2**
  
  - [x] 15.5 Write integration tests for agent management with RAG
    - Test creating RAG-enabled agent
    - Test loading RAG-enabled agent
    - Test deleting RAG-enabled agent with cleanup
    - _Requirements: 1.5, 7.2, 7.4_

- [x] 16. Update Chat Session for RAG
  - [x] 16.1 Modify ChatSession to use RAG orchestrator
    - Check if agent has RAG enabled
    - Route queries through RAG orchestrator when enabled
    - Fall back to standard Ollama chat when disabled
    - Store source citations in conversation history
    - _Requirements: 5.5, 11.1_
  
  - [x] 16.2 Update chat display to show source citations
    - Format source citations in terminal output
    - Show which sources were consulted for each response
    - _Requirements: 11.2_
  
  - [x] 16.3 Write integration tests for RAG-enhanced chat
    - Test chat session with RAG-enabled agent
    - Test source citation display
    - Test fallback to non-RAG mode
    - _Requirements: 5.5, 11.2, 14.1_

- [x] 17. Add RAG Management Commands
  - [x] 17.1 Add command to ingest knowledge sources
    - Allow adding URLs to existing agents
    - Allow adding database tables to existing agents
    - Trigger ingestion and indexing
    - Show progress during ingestion
    - _Requirements: 2.1, 3.1, 13.5_
  
  - [x] 17.2 Add command to re-index knowledge sources
    - Support updating existing knowledge sources
    - Clear old embeddings and re-ingest
    - _Requirements: 7.3_
  
  - [x] 17.3 Add command to list knowledge sources for an agent
    - Display configured sources with status
    - Show last indexed timestamp
    - Show any error messages
    - _Requirements: 1.1, 1.2_
  
  - [x] 17.4 Write integration tests for RAG management commands
    - Test adding knowledge sources
    - Test re-indexing
    - Test listing sources
    - _Requirements: 7.3_

- [x] 18. Performance Optimization
  - [x] 18.1 Implement lazy loading for embedding models
    - Load model only on first use
    - Cache loaded model in memory
    - _Requirements: 8.5, 13.4_
  
  - [x] 18.2 Add progress indicators for long operations
    - Show progress during document ingestion
    - Show progress during batch embedding generation
    - _Requirements: 13.5_
  
  - [x] 18.3 Write performance tests
    - Test retrieval time with 10,000 chunks
    - Test embedding generation time
    - Verify performance requirements met
    - _Requirements: 13.1, 13.2_

- [x] 19. Final checkpoint - Complete RAG system
  - Ensure all tests pass, ask the user if questions arise.

- [x] 20. Documentation and Examples
  - [x] 20.1 Update README with RAG capabilities
    - Document RAG feature overview
    - Document knowledge source types
    - Document configuration options
    - _Requirements: 15.5_
  
  - [x] 20.2 Create example RAG-enabled agents
    - Create example with web sources
    - Create example with database sources
    - Create example with mixed sources
    - _Requirements: 1.1, 1.2_
  
  - [x] 20.3 Document third-party dependencies and licenses
    - List all RAG-related dependencies
    - Document license information
    - Verify open-source compliance
    - _Requirements: 15.5_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The implementation builds from bottom-up: core components → orchestrator → integration
- RAG is optional per-agent, maintaining backward compatibility
