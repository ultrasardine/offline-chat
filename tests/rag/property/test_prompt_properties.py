"""
Property-based tests for prompt augmentation.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from offline_chat.rag.models import DocumentChunk, SearchResult
from offline_chat.rag.prompt_augmenter import PromptAugmenter


# Hypothesis strategies for generating test data
def document_chunk_strategy():
    """Strategy for generating DocumentChunk objects."""
    return st.builds(
        DocumentChunk,
        text=st.text(min_size=1, max_size=500),
        source_type=st.sampled_from(["web", "database"]),
        source_identifier=st.text(min_size=1, max_size=100),
        chunk_index=st.integers(min_value=0, max_value=100),
        metadata=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.none(), st.integers(), st.text(max_size=50)),
            max_size=5,
        ),
    )


def search_result_strategy():
    """Strategy for generating SearchResult objects."""
    return st.builds(
        SearchResult,
        chunk=document_chunk_strategy(),
        similarity_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        rank=st.integers(min_value=1, max_value=100),
    )


@pytest.mark.property_test
class TestPromptProperties:
    """Property-based tests for prompt augmentation."""

    @given(
        query=st.text(min_size=1, max_size=500),
        context_chunks=st.lists(document_chunk_strategy(), min_size=1, max_size=10),
        system_prompt=st.text(min_size=1, max_size=200),
    )
    def test_augmented_prompt_contains_context(
        self, query: str, context_chunks: list[DocumentChunk], system_prompt: str
    ):
        """
        Feature: rag-capabilities, Property 12: Augmented Prompt Contains Context

        For any query with retrieved context chunks, the augmented prompt should
        contain the text of all retrieved chunks.

        **Validates: Requirements 5.1**
        """
        augmenter = PromptAugmenter()
        augmented_prompt = augmenter.augment_prompt(query, context_chunks, system_prompt)

        # Verify that all chunk texts are present in the augmented prompt
        for chunk in context_chunks:
            assert chunk.text in augmented_prompt, f"Chunk text '{chunk.text[:50]}...' not found in augmented prompt"

    @given(
        query=st.text(min_size=1, max_size=500),
        search_results=st.lists(search_result_strategy(), min_size=1, max_size=10),
        system_prompt=st.text(min_size=1, max_size=200),
    )
    def test_augmented_prompt_contains_context_from_search_results(
        self, query: str, search_results: list[SearchResult], system_prompt: str
    ):
        """
        Feature: rag-capabilities, Property 12: Augmented Prompt Contains Context

        For any query with retrieved context chunks (as SearchResult objects),
        the augmented prompt should contain the text of all retrieved chunks.

        **Validates: Requirements 5.1**
        """
        augmenter = PromptAugmenter()
        augmented_prompt = augmenter.augment_prompt(query, search_results, system_prompt)

        # Verify that all chunk texts from search results are present in the augmented prompt
        for search_result in search_results:
            chunk_text = search_result.chunk.text
            assert chunk_text in augmented_prompt, f"Chunk text '{chunk_text[:50]}...' not found in augmented prompt"

    @given(
        query=st.text(min_size=1, max_size=500),
        context_chunks=st.lists(document_chunk_strategy(), min_size=1, max_size=10),
        system_prompt=st.text(min_size=1, max_size=200),
    )
    def test_augmented_prompt_contains_source_attribution(
        self, query: str, context_chunks: list[DocumentChunk], system_prompt: str
    ):
        """
        Feature: rag-capabilities, Property 13: Augmented Prompt Contains Source Attribution

        For any augmented prompt with context chunks, each chunk should be formatted
        with its source identifier (URL or table name).

        **Validates: Requirements 5.2**
        """
        augmenter = PromptAugmenter()
        augmented_prompt = augmenter.augment_prompt(query, context_chunks, system_prompt)

        # Verify that all source identifiers are present in the augmented prompt
        for chunk in context_chunks:
            assert chunk.source_identifier in augmented_prompt, (
                f"Source identifier '{chunk.source_identifier}' not found in augmented prompt"
            )

            # Verify that source type is also indicated
            if chunk.source_type == "web":
                # For web sources, should have "Web Source:" label
                assert "Web Source:" in augmented_prompt or "web" in augmented_prompt.lower(), (
                    "Web source type not clearly indicated in augmented prompt"
                )
            elif chunk.source_type == "database":
                # For database sources, should have "Database Table:" label
                assert "Database Table:" in augmented_prompt or "database" in augmented_prompt.lower(), (
                    "Database source type not clearly indicated in augmented prompt"
                )

    @given(
        query=st.text(min_size=1, max_size=500),
        search_results=st.lists(search_result_strategy(), min_size=1, max_size=10),
        system_prompt=st.text(min_size=1, max_size=200),
    )
    def test_augmented_prompt_contains_source_attribution_from_search_results(
        self, query: str, search_results: list[SearchResult], system_prompt: str
    ):
        """
        Feature: rag-capabilities, Property 13: Augmented Prompt Contains Source Attribution

        For any augmented prompt with context chunks (as SearchResult objects),
        each chunk should be formatted with its source identifier (URL or table name).

        **Validates: Requirements 5.2**
        """
        augmenter = PromptAugmenter()
        augmented_prompt = augmenter.augment_prompt(query, search_results, system_prompt)

        # Verify that all source identifiers from search results are present in the augmented prompt
        for search_result in search_results:
            chunk = search_result.chunk
            assert chunk.source_identifier in augmented_prompt, (
                f"Source identifier '{chunk.source_identifier}' not found in augmented prompt"
            )

            # Verify that source type is also indicated
            if chunk.source_type == "web":
                # For web sources, should have "Web Source:" label
                assert "Web Source:" in augmented_prompt or "web" in augmented_prompt.lower(), (
                    "Web source type not clearly indicated in augmented prompt"
                )
            elif chunk.source_type == "database":
                # For database sources, should have "Database Table:" label
                assert "Database Table:" in augmented_prompt or "database" in augmented_prompt.lower(), (
                    "Database source type not clearly indicated in augmented prompt"
                )

    @given(
        query=st.text(min_size=1, max_size=500),
        context_chunks=st.lists(document_chunk_strategy(), min_size=1, max_size=10),
        system_prompt=st.text(min_size=1, max_size=200),
    )
    def test_rag_prompt_instructions_completeness(
        self, query: str, context_chunks: list[DocumentChunk], system_prompt: str
    ):
        """
        Feature: rag-capabilities, Property 14: RAG Prompt Instructions Completeness

        For any RAG-enabled agent, the system prompt should contain instructions to:
        (1) respond only based on provided context,
        (2) cite sources,
        (3) acknowledge uncertainty,
        (4) never fabricate information, and
        (5) quote or paraphrase from context.

        **Validates: Requirements 5.3, 5.4, 12.1, 12.3, 12.4, 12.5**
        """
        augmenter = PromptAugmenter()
        augmented_prompt = augmenter.augment_prompt(query, context_chunks, system_prompt)

        # Convert to lowercase for case-insensitive matching
        prompt_lower = augmented_prompt.lower()

        # (1) Requirement 5.3 & 12.1: Respond only based on provided context
        assert "respond only based on" in prompt_lower or "only based on the context" in prompt_lower, (
            "Missing instruction to respond only based on provided context"
        )
        assert "do not use any external knowledge" in prompt_lower or "not use external knowledge" in prompt_lower, (
            "Missing instruction to not use external knowledge"
        )

        # (2) Requirement 5.4: Cite sources
        assert "cite" in prompt_lower and "source" in prompt_lower, "Missing instruction to cite sources"

        # (3) Requirement 12.3: Acknowledge uncertainty
        assert "uncertain" in prompt_lower or "don't have enough information" in prompt_lower, (
            "Missing instruction to acknowledge uncertainty"
        )

        # (4) Requirement 12.4: Never fabricate information
        assert (
            "not fabricate" in prompt_lower
            or "do not fabricate" in prompt_lower
            or "must not fabricate" in prompt_lower
        ), "Missing instruction to never fabricate information"

        # (5) Requirement 12.5: Quote or paraphrase from context
        assert "quote or paraphrase" in prompt_lower or "paraphrase" in prompt_lower, (
            "Missing instruction to quote or paraphrase from context"
        )
