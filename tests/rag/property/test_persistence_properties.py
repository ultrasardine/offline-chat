"""
Property-based tests for RAG persistence and conversation history.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.rag.models import SourceCitation


# Strategy for generating valid URLs
@st.composite
def url_strategy(draw):
    """Generate valid URL strings."""
    protocol = draw(st.sampled_from(["http", "https"]))
    domain = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters=".-"),
            min_size=3,
            max_size=30,
        ).filter(lambda x: x and not x.startswith(".") and not x.endswith("."))
    )

    # Optionally add path
    has_path = draw(st.booleans())
    if has_path:
        path = draw(
            st.text(
                alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="/-_"),
                min_size=1,
                max_size=50,
            ).filter(lambda x: x and not x.startswith("/"))
        )
        return f"{protocol}://{domain}/{path}"

    return f"{protocol}://{domain}"


# Strategy for generating valid table names
@st.composite
def table_name_strategy(draw):
    """Generate valid database table names."""
    return draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
            min_size=1,
            max_size=50,
        ).filter(lambda x: x and not x[0].isdigit() and x[0] != "_")
    )


# Strategy for generating SourceCitation objects
@st.composite
def source_citation_strategy(draw):
    """Generate valid SourceCitation objects."""
    source_type = draw(st.sampled_from(["web", "database"]))

    if source_type == "web":
        identifier = draw(url_strategy())
    else:  # database
        identifier = draw(table_name_strategy())

    relevance_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))

    return SourceCitation(source_type=source_type, identifier=identifier, relevance_score=relevance_score)


@pytest.mark.property_test
class TestPersistenceProperties:
    """Property-based tests for RAG persistence."""

    @given(citation=source_citation_strategy())
    @settings(max_examples=100, deadline=None)
    def test_source_citation_completeness(self, citation):
        """
        **Validates: Requirements 6.3, 6.4**

        Property 15: Source Citation Completeness

        For any source citation, if the source type is "database" then the citation
        should include the table name, and if the source type is "web" then the
        citation should include the URL.

        This property ensures that all source citations contain the necessary
        information to identify and verify the source of information, which is
        critical for transparency and trustworthiness of RAG-enhanced responses.
        """
        # Verify that the citation has a source_type
        assert citation.source_type in ["web", "database"], "Source citation must have a valid source_type"

        # Verify that the citation has an identifier
        assert citation.identifier is not None, "Source citation must have an identifier"
        assert len(citation.identifier) > 0, "Source citation identifier must not be empty"

        # Requirement 6.3: Database citations must include table name
        if citation.source_type == "database":
            # The identifier should be a valid table name
            assert isinstance(citation.identifier, str), "Database citation identifier must be a string (table name)"
            assert len(citation.identifier) > 0, "Database citation must include a non-empty table name"

            # Verify the formatted display includes the table name
            formatted = citation.format_for_display()
            assert citation.identifier in formatted, (
                f"Database citation display must include table name '{citation.identifier}'"
            )
            assert "[Database]" in formatted, "Database citation display must indicate source type"

        # Requirement 6.4: Web citations must include URL
        elif citation.source_type == "web":
            # The identifier should be a valid URL
            assert isinstance(citation.identifier, str), "Web citation identifier must be a string (URL)"
            assert len(citation.identifier) > 0, "Web citation must include a non-empty URL"

            # Basic URL validation - should start with http:// or https://
            assert citation.identifier.startswith(("http://", "https://")), (
                f"Web citation must include a valid URL, got: {citation.identifier}"
            )

            # Verify the formatted display includes the URL
            formatted = citation.format_for_display()
            assert citation.identifier in formatted, f"Web citation display must include URL '{citation.identifier}'"
            assert "[Web]" in formatted, "Web citation display must indicate source type"

        # Verify that relevance score is present and valid
        assert citation.relevance_score is not None, "Source citation must have a relevance score"
        assert 0.0 <= citation.relevance_score <= 1.0, (
            f"Relevance score must be between 0.0 and 1.0, got: {citation.relevance_score}"
        )

        # Verify that format_with_relevance includes both identifier and score
        formatted_with_relevance = citation.format_with_relevance()
        assert citation.identifier in formatted_with_relevance, "Citation with relevance must include the identifier"
        assert "relevance:" in formatted_with_relevance.lower(), (
            "Citation with relevance must include the relevance score"
        )

    def test_placeholder_for_property_19(self):
        """Placeholder test - Property 19 will be implemented in task 13.3."""
        pass

    @given(
        role=st.sampled_from(["user", "assistant"]),
        content=st.text(min_size=1, max_size=500),
        sources=st.lists(source_citation_strategy(), min_size=1, max_size=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_conversation_history_display_includes_sources(self, role, content, sources):
        """
        **Validates: Requirements 11.2**

        Property 20: Conversation History Display Includes Sources

        For any RAG-enhanced message in conversation history, the formatted display
        should include the source citations used for that response.

        This property ensures that when viewing conversation history, users can see
        which knowledge sources were consulted for each RAG-enhanced response,
        providing transparency and traceability of information provenance.
        """
        from datetime import datetime

        from offline_chat.history import Message

        # Create a RAG-enhanced message with sources
        message = Message(role=role, content=content, timestamp=datetime.now(), sources=sources)

        # Verify that the message has sources
        assert message.sources is not None, "RAG-enhanced message must have sources"
        assert len(message.sources) > 0, "RAG-enhanced message must have at least one source"

        # Get the formatted display of the message
        formatted = message.format_for_display()

        # Requirement 11.2: The formatted display should include source citations
        assert formatted is not None, "Message format_for_display must return a value"
        assert len(formatted) > 0, "Formatted message must not be empty"

        # The formatted display must include the message content
        assert content in formatted, "Formatted display must include message content"

        # The formatted display must include information about sources
        # Check that each source is represented in the formatted output
        for source in sources:
            # The source identifier should appear in the formatted display
            assert source.identifier in formatted, (
                f"Formatted display must include source identifier '{source.identifier}'"
            )

        # Verify that the formatted display indicates the source type
        # At least one source type indicator should be present
        has_web_indicator = "[Web]" in formatted
        has_db_indicator = "[Database]" in formatted

        # Check that we have the appropriate indicators based on source types
        has_web_sources = any(s.source_type == "web" for s in sources)
        has_db_sources = any(s.source_type == "database" for s in sources)

        if has_web_sources:
            assert has_web_indicator, "Formatted display must include [Web] indicator for web sources"

        if has_db_sources:
            assert has_db_indicator, "Formatted display must include [Database] indicator for database sources"

        # Verify that the formatted display has a sources section
        # This could be indicated by keywords like "Sources:", "Citations:", etc.
        has_sources_section = any(keyword in formatted.lower() for keyword in ["source", "citation", "reference"])
        assert has_sources_section, "Formatted display must have a section indicating sources were used"

    @given(role=st.sampled_from(["user", "assistant"]), content=st.text(min_size=1, max_size=500))
    @settings(max_examples=100, deadline=None)
    def test_non_rag_message_display_without_sources(self, role, content):
        """
        Test that non-RAG messages (without sources) format correctly.

        This ensures backward compatibility - messages without sources should
        still format properly without attempting to display source citations.
        """
        from datetime import datetime

        from offline_chat.history import Message

        # Create a non-RAG message (sources=None)
        message = Message(role=role, content=content, timestamp=datetime.now(), sources=None)

        # Verify that the message has no sources
        assert message.sources is None, "Non-RAG message should have sources=None"

        # Get the formatted display
        formatted = message.format_for_display()

        # The formatted display should work without errors
        assert formatted is not None, "Non-RAG message format_for_display must return a value"
        assert len(formatted) > 0, "Formatted non-RAG message must not be empty"

        # The formatted display must include the message content
        assert content in formatted, "Formatted display must include message content"

        # The formatted display should NOT include source indicators
        # since this is not a RAG-enhanced message
        assert "[Web]" not in formatted or "[Database]" not in formatted, (
            "Non-RAG message should not show source indicators"
        )
