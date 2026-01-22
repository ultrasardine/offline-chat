# Requirements Document: RAG Capabilities

## Introduction

This specification defines the addition of Retrieval-Augmented Generation (RAG) capabilities to the offline chat system. The feature enables agents to ground their responses in trusted knowledge sources (databases and web documents) to prevent hallucination and ensure responses are based on corporate-approved information. The system implements a hybrid RAG approach combining vector similarity search, database queries, and strict prompt engineering to maintain response accuracy.

## Glossary

- **RAG_System**: The Retrieval-Augmented Generation system that retrieves relevant context before generating responses
- **Vector_Store**: ChromaDB database storing document embeddings for similarity search
- **Knowledge_Source**: A trusted data source (database or web document) approved for agent responses
- **Embedding_Generator**: The sentence-transformers model that converts text to vector embeddings
- **Context_Retriever**: Component that searches and retrieves relevant context from knowledge sources
- **Document_Processor**: Component that chunks and processes documents for storage
- **Web_Scraper**: MCP-based tool that fetches content from approved URLs
- **Source_Citation**: Reference to the original knowledge source included in agent responses
- **Augmented_Prompt**: User query enhanced with retrieved context before sending to Ollama
- **Agent_Config**: Configuration defining an agent's knowledge sources and RAG settings

## Requirements

### Requirement 1: Knowledge Source Management

**User Story:** As a system administrator, I want to configure approved knowledge sources for each agent, so that responses are limited to trusted information.

#### Acceptance Criteria

1. WHEN an administrator creates or updates an agent, THE Agent_Config SHALL allow specification of approved database tables
2. WHEN an administrator creates or updates an agent, THE Agent_Config SHALL allow specification of approved website URLs
3. WHEN an administrator adds a website URL, THE RAG_System SHALL validate the URL format before acceptance
4. THE Agent_Config SHALL store knowledge source configurations persistently in the agent's configuration file
5. WHEN an agent is loaded, THE RAG_System SHALL initialize access to all configured knowledge sources

### Requirement 2: Document Ingestion and Processing

**User Story:** As a system administrator, I want to ingest web documents into the vector store, so that agents can retrieve relevant information from them.

#### Acceptance Criteria

1. WHEN a website URL is added to an agent's knowledge sources, THE Web_Scraper SHALL fetch the content from that URL
2. WHEN content is fetched, THE Document_Processor SHALL split the content into chunks of configurable size (default 512 tokens)
3. WHEN documents are chunked, THE Document_Processor SHALL preserve source URL metadata with each chunk
4. WHEN chunks are created, THE Embedding_Generator SHALL generate vector embeddings for each chunk using sentence-transformers
5. WHEN embeddings are generated, THE Vector_Store SHALL store the embeddings with their text content and metadata
6. IF web scraping fails, THEN THE RAG_System SHALL log the error and continue with other sources

### Requirement 3: Database Content Integration

**User Story:** As a system administrator, I want to include database tables as knowledge sources, so that agents can answer questions using structured data.

#### Acceptance Criteria

1. WHEN a database table is configured as a knowledge source, THE RAG_System SHALL validate the table exists in the SQLite database
2. WHEN database content is ingested, THE Document_Processor SHALL convert table rows into text representations
3. WHEN table rows are converted, THE Document_Processor SHALL include column names and values in a readable format
4. WHEN database content is processed, THE Embedding_Generator SHALL generate embeddings for each row representation
5. WHEN database embeddings are stored, THE Vector_Store SHALL include table name and row identifier in metadata

### Requirement 4: Context Retrieval

**User Story:** As an agent, I want to retrieve relevant context for user queries, so that my responses are grounded in approved knowledge sources.

#### Acceptance Criteria

1. WHEN a user submits a query, THE Embedding_Generator SHALL generate a vector embedding for the query
2. WHEN a query embedding is generated, THE Context_Retriever SHALL search the Vector_Store for the top-k most similar chunks (default k=5)
3. WHEN similar chunks are found, THE Context_Retriever SHALL return the chunks ordered by similarity score descending
4. WHEN chunks are retrieved, THE Context_Retriever SHALL include source metadata (URL or table name) with each chunk
5. IF no similar chunks are found above a minimum similarity threshold (default 0.3), THEN THE Context_Retriever SHALL return an empty result set

### Requirement 5: Prompt Augmentation

**User Story:** As an agent, I want to receive user queries with relevant context injected, so that I can generate accurate responses based on approved sources.

#### Acceptance Criteria

1. WHEN context is retrieved for a query, THE RAG_System SHALL construct an augmented prompt containing the retrieved context
2. WHEN constructing the augmented prompt, THE RAG_System SHALL format context chunks with clear source attribution
3. WHEN the augmented prompt is constructed, THE RAG_System SHALL include instructions to respond only based on provided context
4. WHEN the augmented prompt is constructed, THE RAG_System SHALL include instructions to cite sources in the response
5. WHEN the augmented prompt is ready, THE RAG_System SHALL send it to the Ollama model for response generation

### Requirement 6: Response Generation with Source Citations

**User Story:** As a user, I want agent responses to include citations to their sources, so that I can verify the information and understand its origin.

#### Acceptance Criteria

1. WHEN an agent generates a response using RAG, THE RAG_System SHALL instruct the agent to include source citations
2. WHEN multiple sources are used, THE RAG_System SHALL ensure each distinct source is cited
3. WHEN a database table is used as a source, THE Source_Citation SHALL include the table name
4. WHEN a web document is used as a source, THE Source_Citation SHALL include the URL
5. WHEN no relevant context is found, THE RAG_System SHALL instruct the agent to state that no information is available rather than hallucinate

### Requirement 7: Vector Store Management

**User Story:** As a system administrator, I want to manage the vector database efficiently, so that the system performs well and uses storage appropriately.

#### Acceptance Criteria

1. THE Vector_Store SHALL use ChromaDB for persistent vector storage
2. WHEN an agent is created with knowledge sources, THE Vector_Store SHALL create a dedicated collection for that agent
3. WHEN knowledge sources are updated, THE RAG_System SHALL support re-indexing the Vector_Store with new content
4. WHEN an agent is deleted, THE RAG_System SHALL provide an option to delete the associated vector collection
5. THE Vector_Store SHALL store embeddings on local disk in the data directory structure

### Requirement 8: Embedding Generation

**User Story:** As a system, I want to generate embeddings locally without external API calls, so that the system remains offline-capable and private.

#### Acceptance Criteria

1. THE Embedding_Generator SHALL use the sentence-transformers library for local embedding generation
2. THE Embedding_Generator SHALL use a configurable model (default: 'all-MiniLM-L6-v2')
3. WHEN the system starts, THE Embedding_Generator SHALL load the embedding model into memory
4. WHEN generating embeddings, THE Embedding_Generator SHALL process text in batches for efficiency
5. THE Embedding_Generator SHALL cache the loaded model to avoid repeated loading

### Requirement 9: Web Scraping Integration

**User Story:** As a system administrator, I want to scrape approved websites for content, so that agents have access to up-to-date web-based knowledge.

#### Acceptance Criteria

1. THE Web_Scraper SHALL use an open-source MCP tool (Firecrawl MCP or fetch MCP) for content retrieval
2. WHEN scraping a URL, THE Web_Scraper SHALL extract the main text content while removing navigation and boilerplate
3. WHEN scraping a URL, THE Web_Scraper SHALL handle common web formats (HTML, markdown)
4. WHEN scraping fails due to network issues, THE Web_Scraper SHALL retry up to 3 times with exponential backoff
5. WHEN scraping is rate-limited, THE Web_Scraper SHALL respect rate limits and delay subsequent requests

### Requirement 10: RAG Configuration

**User Story:** As a system administrator, I want to configure RAG parameters per agent, so that I can optimize retrieval quality for different use cases.

#### Acceptance Criteria

1. THE Agent_Config SHALL allow configuration of the number of context chunks to retrieve (top-k parameter)
2. THE Agent_Config SHALL allow configuration of the minimum similarity threshold for retrieval
3. THE Agent_Config SHALL allow configuration of the chunk size for document processing
4. THE Agent_Config SHALL allow configuration of chunk overlap size to preserve context across boundaries
5. THE Agent_Config SHALL provide sensible defaults for all RAG parameters (k=5, threshold=0.3, chunk_size=512, overlap=50)

### Requirement 11: Conversation History with RAG

**User Story:** As a user, I want my conversation history to reflect which sources were used, so that I can track the provenance of information over time.

#### Acceptance Criteria

1. WHEN a RAG-enhanced response is generated, THE RAG_System SHALL store the retrieved context metadata with the conversation history
2. WHEN viewing conversation history, THE RAG_System SHALL display which sources were consulted for each response
3. WHEN a conversation is saved, THE RAG_System SHALL persist source citations alongside message content
4. WHEN a conversation is loaded, THE RAG_System SHALL restore source citation information
5. THE RAG_System SHALL maintain backward compatibility with non-RAG conversation histories

### Requirement 12: Hallucination Prevention

**User Story:** As a system administrator, I want to prevent agents from hallucinating information, so that all responses are trustworthy and verifiable.

#### Acceptance Criteria

1. WHEN RAG is enabled for an agent, THE RAG_System SHALL modify the system prompt to enforce context-only responses
2. WHEN no relevant context is found, THE RAG_System SHALL instruct the agent to explicitly state that no information is available
3. WHEN the agent is uncertain, THE RAG_System SHALL instruct the agent to acknowledge uncertainty rather than guess
4. THE RAG_System SHALL include explicit instructions in the system prompt to never fabricate information
5. THE RAG_System SHALL instruct the agent to quote or paraphrase from provided context rather than generate novel claims

### Requirement 13: Performance and Scalability

**User Story:** As a user, I want RAG-enhanced responses to be generated quickly, so that the chat experience remains responsive.

#### Acceptance Criteria

1. WHEN a query is submitted, THE Context_Retriever SHALL return results within 500ms for vector stores containing up to 10,000 chunks
2. WHEN generating embeddings, THE Embedding_Generator SHALL process queries in under 100ms
3. WHEN multiple agents use RAG, THE Vector_Store SHALL support concurrent read operations without performance degradation
4. THE RAG_System SHALL load embedding models lazily to minimize startup time
5. THE RAG_System SHALL provide progress indicators when ingesting large document sets

### Requirement 14: Error Handling and Resilience

**User Story:** As a user, I want the system to handle errors gracefully, so that RAG failures don't break the chat experience.

#### Acceptance Criteria

1. IF the Vector_Store is unavailable, THEN THE RAG_System SHALL fall back to non-RAG mode and log a warning
2. IF embedding generation fails, THEN THE RAG_System SHALL return an error message to the user and continue operation
3. IF web scraping fails for a URL, THEN THE RAG_System SHALL skip that source and use other available sources
4. IF the ChromaDB collection is corrupted, THEN THE RAG_System SHALL provide a repair or rebuild option
5. WHEN errors occur, THE RAG_System SHALL log detailed error information for debugging while showing user-friendly messages

### Requirement 15: Open-Source Compliance

**User Story:** As a system administrator, I want all RAG components to use open-source libraries, so that the system remains free and auditable.

#### Acceptance Criteria

1. THE Vector_Store SHALL use ChromaDB (Apache 2.0 license)
2. THE Embedding_Generator SHALL use sentence-transformers (Apache 2.0 license)
3. THE Web_Scraper SHALL use open-source MCP tools (Firecrawl MCP or fetch MCP)
4. THE RAG_System SHALL not depend on any proprietary or closed-source libraries
5. THE RAG_System SHALL document all third-party dependencies and their licenses
