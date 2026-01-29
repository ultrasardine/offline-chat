"""
RAG orchestrator for coordinating the entire RAG workflow.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import ollama

from offline_chat.agent import Agent
from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.database_integration import DatabaseIntegration
from offline_chat.rag.document_processor import DocumentProcessor
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import (
    IngestionResult,
    KnowledgeSource,
    RAGResponse,
    RetrievalResult,
    SourceCitation,
)
from offline_chat.rag.prompt_augmenter import PromptAugmenter
from offline_chat.rag.vector_store import VectorStore
from offline_chat.rag.web_scraper import WebScraper

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """
    Coordinate the entire RAG workflow from query to response.

    This class manages the RAG pipeline: ingestion of knowledge sources,
    query processing, context retrieval, and prompt augmentation.

    The orchestrator coordinates:
    - Knowledge source ingestion (web scraping, database fetching)
    - Document processing and chunking
    - Embedding generation
    - Vector storage
    - Context retrieval
    - Prompt augmentation
    """

    def __init__(
        self,
        agent_config: Agent,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator,
        context_retriever: ContextRetriever,
        document_processor: DocumentProcessor | None = None,
        prompt_augmenter: PromptAugmenter | None = None,
        web_scraper: WebScraper | None = None,
        database_integration: DatabaseIntegration | None = None,
    ):
        """
        Initialize RAG orchestrator with required components.

        Args:
            agent_config: Agent configuration with RAG settings
            vector_store: VectorStore instance
            embedding_generator: EmbeddingGenerator instance
            context_retriever: ContextRetriever instance
            document_processor: Optional DocumentProcessor instance
            prompt_augmenter: Optional PromptAugmenter instance
            web_scraper: Optional WebScraper instance for web sources
            database_integration: Optional DatabaseIntegration instance for database sources
        """
        self.agent_config = agent_config
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.context_retriever = context_retriever

        # Initialize optional components with defaults if not provided
        self.document_processor = document_processor or DocumentProcessor(
            chunk_size=agent_config.rag_config.chunk_size if agent_config.rag_config else 512,
            chunk_overlap=agent_config.rag_config.chunk_overlap if agent_config.rag_config else 50,
        )
        self.prompt_augmenter = prompt_augmenter or PromptAugmenter()
        self.web_scraper = web_scraper
        self.database_integration = database_integration

        # Track ingestion status for each knowledge source
        self._ingestion_status: dict[str, KnowledgeSource] = {}

    def process_query(
        self,
        query: str,
        conversation_history: list[Any] | None = None,
        generate_response: bool = False
    ) -> RAGResponse | None:
        """
        Process a user query through the RAG pipeline.

        This method implements the complete query workflow:
        1. Generate query embedding
        2. Retrieve relevant context from vector store
        3. Augment prompt with context
        4. (Optional) Send to Ollama for generation
        5. Extract source citations

        If the vector store is unavailable, logs a warning and returns None
        to signal fallback to non-RAG mode.

        Args:
            query: User's input query
            conversation_history: Previous messages for context (optional)
            generate_response: If True, calls Ollama to generate response.
                             If False, only prepares retrieval data (default: False)

        Returns:
            RAGResponse containing retrieval results, source citations,
            and optionally the generated response content.
            Returns None if vector store is unavailable (fallback to non-RAG mode).

        Raises:
            ValueError: If query is empty or RAG is not enabled
        """
        if not query:
            raise ValueError("Query cannot be empty")

        if not self.agent_config.rag_config or not self.agent_config.rag_config.enabled:
            raise ValueError("RAG is not enabled for this agent")

        start_time = time.time()

        # Get RAG configuration parameters
        rag_config = self.agent_config.rag_config
        collection_name = self.agent_config.name

        # Step 1 & 2: Generate query embedding and retrieve relevant context
        # Detect vector store unavailability and fall back to non-RAG mode
        try:
            logger.info(f"Retrieving context for query: {query[:50]}...")
            retrieval_result = self.context_retriever.retrieve_context(
                collection_name=collection_name,
                query=query,
                top_k=rag_config.top_k,
                min_similarity=rag_config.min_similarity,
            )

            logger.info(
                f"Retrieved {retrieval_result.total_results} chunks "
                f"in {retrieval_result.retrieval_time_ms:.2f}ms"
            )
        except Exception as e:
            # Check if this is a vector store unavailability error
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in [
                "connection", "unavailable", "not found", "does not exist",
                "chromadb", "collection", "database"
            ]):
                logger.warning(
                    f"Vector store unavailable for agent '{self.agent_config.name}': {e}. "
                    f"Falling back to non-RAG mode."
                )
                return None
            else:
                # Re-raise if it's not a vector store availability issue
                logger.error(f"Error during context retrieval: {e}")
                raise

        # Step 3: Augment prompt with context
        augmented_prompt = self.get_augmented_prompt(query, retrieval_result)

        # Step 4: (Optional) Send to Ollama for generation
        response_content = ""
        if generate_response:
            logger.info("Generating response with Ollama...")
            response_content = self._generate_with_ollama(augmented_prompt)
            logger.info(f"Response generated: {len(response_content)} characters")

        # Step 5: Extract source citations from retrieved chunks
        sources = self._extract_source_citations(retrieval_result)

        # Calculate total processing time
        generation_time_ms = (time.time() - start_time) * 1000

        # Create RAG response
        return RAGResponse(
            content=response_content,
            sources=sources,
            retrieval_result=retrieval_result,
            generation_time_ms=generation_time_ms,
        )

    def get_augmented_prompt(
        self,
        query: str,
        retrieval_result: RetrievalResult
    ) -> str:
        """
        Get the augmented prompt for a query with retrieved context.

        This is a helper method that can be called by ChatSession to get
        the augmented prompt after process_query has been called.

        Args:
            query: User's input query
            retrieval_result: Result from context retrieval

        Returns:
            Augmented prompt string ready for Ollama
        """
        return self.prompt_augmenter.augment_prompt(
            query=query,
            context_chunks=retrieval_result.chunks,
            system_prompt=self.agent_config.system_prompt,
        )

    def ingest_knowledge_sources(
        self,
        sources: list[KnowledgeSource],
        show_progress: bool = True
    ) -> list[IngestionResult]:
        """
        Ingest knowledge sources into the vector store.

        This method processes each knowledge source based on its type:
        - Web sources: Scrape URL content
        - Database sources: Fetch table rows

        Then for each source:
        1. Process content into chunks
        2. Generate embeddings
        3. Store in vector database
        4. Track ingestion status

        Args:
            sources: List of knowledge sources (URLs or database tables)
            show_progress: If True, display progress indicators during ingestion (default: True)

        Returns:
            List of IngestionResult with success/failure status for each source

        Raises:
            ValueError: If sources list is empty or RAG is not enabled
        """
        if not sources:
            raise ValueError("Sources list cannot be empty")

        if not self.agent_config.rag_config or not self.agent_config.rag_config.enabled:
            raise ValueError("RAG is not enabled for this agent")

        logger.info(f"Starting ingestion of {len(sources)} knowledge sources")

        # Ensure vector collection exists
        collection_name = self.agent_config.name
        embedding_dim = self.embedding_generator.get_embedding_dimension()
        self.vector_store.create_collection(collection_name, embedding_dim)

        results: list[IngestionResult] = []

        for idx, source in enumerate(sources):
            if show_progress:
                print(f"\n[{idx + 1}/{len(sources)}] Processing {source.source_type} source: {source.identifier}")

            logger.info(
                f"Ingesting {source.source_type} source: {source.identifier}"
            )

            try:
                if source.source_type == "web":
                    result = self._ingest_web_source(source, show_progress=show_progress)
                elif source.source_type == "database":
                    result = self._ingest_database_source(source, show_progress=show_progress)
                else:
                    raise ValueError(f"Unknown source type: {source.source_type}")

                results.append(result)

                # Update ingestion status
                if result.success:
                    source.status = "active"
                    source.last_indexed = datetime.now()
                    source.error_message = None
                    if show_progress:
                        print(f"✓ Successfully processed {result.chunks_processed} chunks")
                else:
                    source.status = "failed"
                    source.error_message = result.error_message
                    if show_progress:
                        print(f"✗ Failed: {result.error_message}")

                self._ingestion_status[source.identifier] = source

            except Exception as e:
                logger.error(
                    f"Failed to ingest source {source.identifier}: {e}",
                    exc_info=True
                )

                error_msg = f"Ingestion failed: {str(e)}"
                source.status = "failed"
                source.error_message = error_msg
                self._ingestion_status[source.identifier] = source

                if show_progress:
                    print(f"✗ Failed: {error_msg}")

                results.append(
                    IngestionResult(
                        source=source,
                        success=False,
                        chunks_processed=0,
                        error_message=error_msg,
                    )
                )

        # Log summary
        successful = sum(1 for r in results if r.success)
        total_chunks = sum(r.chunks_processed for r in results)
        logger.info(
            f"Ingestion complete: {successful}/{len(sources)} sources successful, "
            f"{total_chunks} total chunks processed"
        )

        if show_progress:
            print(f"\n{'='*60}")
            print(f"Ingestion Summary: {successful}/{len(sources)} sources successful")
            print(f"Total chunks processed: {total_chunks}")
            print(f"{'='*60}\n")

        return results

    def get_ingestion_status(self, source_identifier: str) -> KnowledgeSource | None:
        """
        Get the ingestion status for a specific knowledge source.

        Args:
            source_identifier: URL or table name of the source

        Returns:
            KnowledgeSource with status information, or None if not found
        """
        return self._ingestion_status.get(source_identifier)

    def check_collection_health(self) -> tuple[bool, str | None]:
        """
        Check the health of the agent's vector collection.

        This method checks if the collection exists and is not corrupted.

        Returns:
            Tuple of (is_healthy, error_message)
            - is_healthy: True if collection is healthy, False if corrupted or missing
            - error_message: Description of the issue if not healthy, None otherwise
        """
        collection_name = self.agent_config.name

        # Check if collection is corrupted
        is_corrupted, error_msg = self.vector_store.is_collection_corrupted(collection_name)

        if is_corrupted:
            return False, error_msg

        # Check if collection exists and has data
        info = self.vector_store.get_collection_info(collection_name)

        if info is None:
            return False, "Collection does not exist. Run ingestion to create it."

        if info["count"] == 0:
            return False, "Collection is empty. Run ingestion to add knowledge sources."

        return True, None

    def rebuild_collection(self, force: bool = False) -> tuple[bool, str]:
        """
        Rebuild the agent's vector collection.

        This is a convenience method that wraps the vector store's rebuild_collection
        method with the agent's configuration.

        Args:
            force: If True, rebuild even if collection appears healthy

        Returns:
            Tuple of (success, message)
            - success: True if rebuild succeeded, False otherwise
            - message: Description of the result
        """
        collection_name = self.agent_config.name
        embedding_dim = self.embedding_generator.get_embedding_dimension()

        return self.vector_store.rebuild_collection(
            collection_name=collection_name,
            embedding_dimension=embedding_dim,
            force=force
        )

    def _ingest_web_source(self, source: KnowledgeSource, show_progress: bool = False) -> IngestionResult:
        """
        Ingest a web source by scraping, chunking, embedding, and storing.

        Args:
            source: Web knowledge source with URL
            show_progress: If True, display progress indicators

        Returns:
            IngestionResult with success/failure status
        """
        if not self.web_scraper:
            return IngestionResult(
                source=source,
                success=False,
                chunks_processed=0,
                error_message="Web scraper not configured",
            )

        try:
            # Scrape URL content (async operation)
            if show_progress:
                print("  → Scraping URL...")
            logger.info(f"Scraping URL: {source.identifier}")
            scraped_content = asyncio.run(
                self.web_scraper.scrape_url(source.identifier)
            )

            if not scraped_content.success:
                return IngestionResult(
                    source=source,
                    success=False,
                    chunks_processed=0,
                    error_message=scraped_content.error_message,
                )

            # Process into chunks
            if show_progress:
                print(f"  → Processing content ({len(scraped_content.text)} chars)...")
            logger.info(f"Processing content into chunks: {len(scraped_content.text)} chars")
            chunks = self.document_processor.process_text_document(
                content=scraped_content.text,
                source_url=source.identifier,
            )

            if not chunks:
                return IngestionResult(
                    source=source,
                    success=False,
                    chunks_processed=0,
                    error_message="No chunks generated from content",
                )

            # Generate embeddings
            if show_progress:
                print(f"  → Generating embeddings for {len(chunks)} chunks...")
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings_batch(
                chunk_texts,
                show_progress=show_progress
            )

            # Store in vector database
            if show_progress:
                print("  → Storing in vector database...")
            logger.info(f"Storing {len(chunks)} chunks in vector store")
            collection_name = self.agent_config.name
            self.vector_store.add_documents(
                collection_name=collection_name,
                chunks=chunks,
                embeddings=embeddings,
            )

            logger.info(
                f"Successfully ingested web source: {source.identifier} "
                f"({len(chunks)} chunks)"
            )

            return IngestionResult(
                source=source,
                success=True,
                chunks_processed=len(chunks),
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Error ingesting web source {source.identifier}: {e}")
            return IngestionResult(
                source=source,
                success=False,
                chunks_processed=0,
                error_message=str(e),
            )

    def _ingest_database_source(self, source: KnowledgeSource, show_progress: bool = False) -> IngestionResult:
        """
        Ingest a database source by fetching rows, converting to text, embedding, and storing.

        Args:
            source: Database knowledge source with table name
            show_progress: If True, display progress indicators

        Returns:
            IngestionResult with success/failure status
        """
        if not self.database_integration:
            return IngestionResult(
                source=source,
                success=False,
                chunks_processed=0,
                error_message="Database integration not configured",
            )

        try:
            # Validate table exists
            if show_progress:
                print("  → Validating table...")
            logger.info(f"Validating table: {source.identifier}")
            if not self.database_integration.validate_table_exists(source.identifier):
                return IngestionResult(
                    source=source,
                    success=False,
                    chunks_processed=0,
                    error_message=f"Table '{source.identifier}' does not exist",
                )

            # Fetch table rows and convert to chunks
            if show_progress:
                print("  → Fetching table rows...")
            logger.info(f"Fetching rows from table: {source.identifier}")
            chunks = self.database_integration.get_table_as_chunks(source.identifier)

            if not chunks:
                return IngestionResult(
                    source=source,
                    success=False,
                    chunks_processed=0,
                    error_message="No rows found in table",
                )

            # Generate embeddings
            if show_progress:
                print(f"  → Generating embeddings for {len(chunks)} rows...")
            logger.info(f"Generating embeddings for {len(chunks)} rows")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings_batch(
                chunk_texts,
                show_progress=show_progress
            )

            # Store in vector database
            if show_progress:
                print("  → Storing in vector database...")
            logger.info(f"Storing {len(chunks)} chunks in vector store")
            collection_name = self.agent_config.name
            self.vector_store.add_documents(
                collection_name=collection_name,
                chunks=chunks,
                embeddings=embeddings,
            )

            logger.info(
                f"Successfully ingested database source: {source.identifier} "
                f"({len(chunks)} chunks)"
            )

            return IngestionResult(
                source=source,
                success=True,
                chunks_processed=len(chunks),
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Error ingesting database source {source.identifier}: {e}")
            return IngestionResult(
                source=source,
                success=False,
                chunks_processed=0,
                error_message=str(e),
            )

    def _extract_source_citations(
        self,
        retrieval_result: RetrievalResult
    ) -> list[SourceCitation]:
        """
        Extract unique source citations from retrieval results.

        Args:
            retrieval_result: Result from context retrieval

        Returns:
            List of unique source citations with relevance scores
        """
        # Group chunks by source identifier
        source_scores: dict[tuple[str, str], float] = {}

        for search_result in retrieval_result.chunks:
            chunk = search_result.chunk
            key = (chunk.source_type, chunk.source_identifier)

            # Keep the highest similarity score for each source
            if key not in source_scores or search_result.similarity_score > source_scores[key]:
                source_scores[key] = search_result.similarity_score

        # Create source citations
        citations = [
            SourceCitation(
                source_type=source_type,
                identifier=identifier,
                relevance_score=score,
            )
            for (source_type, identifier), score in source_scores.items()
        ]

        # Sort by relevance score (descending)
        citations.sort(key=lambda c: c.relevance_score, reverse=True)

        return citations

    def _generate_with_ollama(self, augmented_prompt: str) -> str:
        """
        Generate a response using Ollama with the augmented prompt.

        This method sends the augmented prompt (containing context and instructions)
        to Ollama and returns the generated response.

        Args:
            augmented_prompt: The augmented prompt with context and RAG instructions

        Returns:
            Generated response content from Ollama

        Raises:
            Exception: If Ollama generation fails
        """
        try:
            # Build messages for Ollama
            # The augmented prompt already contains the system prompt and context
            messages = [
                {
                    "role": "user",
                    "content": augmented_prompt
                }
            ]

            # Call Ollama with the agent's base model
            response = ollama.chat(
                model=self.agent_config.base_model,
                messages=messages,
                stream=False,
            )

            # Extract response content
            content = response.get("message", {}).get("content", "")

            return content

        except Exception as e:
            logger.error(f"Failed to generate response with Ollama: {e}")
            raise
