"""
Property-based tests for RAG configuration.
"""

from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

from offline_chat.agent import Agent
from offline_chat.rag.models import KnowledgeSource, RAGConfig


# Strategy for generating valid agent names (kebab-case)
agent_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
    min_size=3,
    max_size=30
).filter(lambda x: x and x[0] != "-" and x[-1] != "-" and "--" not in x)


# Strategy for generating display names
display_name_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip())


# Strategy for generating system prompts
system_prompt_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    min_size=10,
    max_size=200
).filter(lambda x: x.strip())


# Strategy for generating base model names
base_model_strategy = st.sampled_from([
    "llama3:latest",
    "mistral:latest",
    "phi3:latest",
    "gemma:latest"
])


# Strategy for generating temperature values
temperature_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


# Strategy for generating language names
language_strategy = st.sampled_from(["English", "German", "Spanish", "French", "Japanese"])


# Strategy for generating KnowledgeSource objects
@st.composite
def knowledge_source_strategy(draw):
    """Generate a valid KnowledgeSource."""
    source_type = draw(st.sampled_from(["web", "database"]))
    
    if source_type == "web":
        # Generate a URL-like identifier
        identifier = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters=".-/"),
            min_size=10,
            max_size=50
        ).map(lambda x: f"https://example.com/{x}"))
    else:
        # Generate a table name
        identifier = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="_"),
            min_size=3,
            max_size=30
        ).filter(lambda x: x and x[0] != "_"))
    
    # Randomly include last_indexed or leave it None
    last_indexed = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2025, 12, 31)
        ).map(lambda dt: dt.replace(tzinfo=timezone.utc))
    ))
    
    status = draw(st.sampled_from(["active", "failed", "pending"]))
    
    # Only include error_message if status is "failed"
    error_message = None
    if status == "failed":
        error_message = draw(st.one_of(
            st.none(),
            st.text(min_size=5, max_size=50).filter(lambda x: x.strip())
        ))
    
    return KnowledgeSource(
        source_type=source_type,
        identifier=identifier,
        last_indexed=last_indexed,
        status=status,
        error_message=error_message
    )


# Strategy for generating RAGConfig objects
@st.composite
def rag_config_strategy(draw):
    """Generate a valid RAGConfig."""
    enabled = draw(st.booleans())
    top_k = draw(st.integers(min_value=1, max_value=20))
    min_similarity = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    chunk_size = draw(st.integers(min_value=100, max_value=2000))
    chunk_overlap = draw(st.integers(min_value=0, max_value=500))
    embedding_model = draw(st.sampled_from([
        "all-MiniLM-L6-v2",
        "all-mpnet-base-v2",
        "paraphrase-MiniLM-L6-v2"
    ]))
    knowledge_sources = draw(st.lists(knowledge_source_strategy(), min_size=0, max_size=5))
    
    return RAGConfig(
        enabled=enabled,
        top_k=top_k,
        min_similarity=min_similarity,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
        knowledge_sources=knowledge_sources
    )


# Strategy for generating Agent objects with RAG config
@st.composite
def agent_with_rag_strategy(draw):
    """Generate a valid Agent with RAG configuration."""
    name = draw(agent_name_strategy)
    display_name = draw(display_name_strategy)
    base_model = draw(base_model_strategy)
    system_prompt = draw(system_prompt_strategy)
    temperature = draw(temperature_strategy)
    language = draw(language_strategy)
    web_search_enabled = draw(st.booleans())
    guidelines = draw(st.lists(
        st.text(min_size=5, max_size=50).filter(lambda x: x.strip()),
        min_size=0,
        max_size=5
    ))
    created_at = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2025, 12, 31)
    ).map(lambda dt: dt.replace(tzinfo=timezone.utc)))
    
    # Generate RAG config (can be None or a RAGConfig instance)
    rag_config = draw(st.one_of(st.none(), rag_config_strategy()))
    
    return Agent(
        name=name,
        display_name=display_name,
        base_model=base_model,
        system_prompt=system_prompt,
        temperature=temperature,
        language=language,
        web_search_enabled=web_search_enabled,
        mcp_servers=[],  # Keep empty for simplicity
        connection_assignments=[],  # Keep empty for simplicity
        guidelines=guidelines,
        created_at=created_at,
        rag_config=rag_config
    )


@pytest.mark.property_test
class TestConfigProperties:
    """Property-based tests for RAG configuration."""
    
    @given(agent=agent_with_rag_strategy())
    @settings(max_examples=100, deadline=None)
    def test_agent_configuration_round_trip(self, agent):
        """
        **Validates: Requirements 1.1, 1.2, 1.4, 1.5**
        
        Property 1: Agent Configuration Round-Trip
        
        For any agent configuration with RAG settings (knowledge sources, parameters),
        serializing to JSON then deserializing should produce an equivalent configuration
        with all RAG settings preserved.
        
        This property ensures that agent configurations can be reliably persisted and
        restored without data loss, which is critical for maintaining agent state across
        application restarts.
        """
        # Serialize agent to dictionary
        agent_dict = agent.to_dict()
        
        # Deserialize back to Agent object
        restored_agent = Agent.from_dict(agent_dict)
        
        # Verify basic agent properties are preserved
        assert restored_agent.name == agent.name
        assert restored_agent.display_name == agent.display_name
        assert restored_agent.base_model == agent.base_model
        assert restored_agent.system_prompt == agent.system_prompt
        assert abs(restored_agent.temperature - agent.temperature) < 1e-6
        assert restored_agent.language == agent.language
        assert restored_agent.web_search_enabled == agent.web_search_enabled
        assert restored_agent.guidelines == agent.guidelines
        
        # Verify created_at timestamp is preserved (compare as ISO strings to handle timezone)
        assert restored_agent.created_at.isoformat() == agent.created_at.isoformat()
        
        # Verify RAG config preservation
        if agent.rag_config is None:
            assert restored_agent.rag_config is None
        else:
            assert restored_agent.rag_config is not None
            
            # Verify RAG config parameters
            assert restored_agent.rag_config.enabled == agent.rag_config.enabled
            assert restored_agent.rag_config.top_k == agent.rag_config.top_k
            assert abs(restored_agent.rag_config.min_similarity - agent.rag_config.min_similarity) < 1e-6
            assert restored_agent.rag_config.chunk_size == agent.rag_config.chunk_size
            assert restored_agent.rag_config.chunk_overlap == agent.rag_config.chunk_overlap
            assert restored_agent.rag_config.embedding_model == agent.rag_config.embedding_model
            
            # Verify knowledge sources count
            assert len(restored_agent.rag_config.knowledge_sources) == len(agent.rag_config.knowledge_sources)
            
            # Verify each knowledge source is preserved
            for original_ks, restored_ks in zip(
                agent.rag_config.knowledge_sources,
                restored_agent.rag_config.knowledge_sources
            ):
                assert restored_ks.source_type == original_ks.source_type
                assert restored_ks.identifier == original_ks.identifier
                assert restored_ks.status == original_ks.status
                assert restored_ks.error_message == original_ks.error_message
                
                # Verify last_indexed timestamp
                if original_ks.last_indexed is None:
                    assert restored_ks.last_indexed is None
                else:
                    assert restored_ks.last_indexed is not None
                    assert restored_ks.last_indexed.isoformat() == original_ks.last_indexed.isoformat()
    
    @given(rag_config=rag_config_strategy())
    @settings(max_examples=100, deadline=None)
    def test_rag_configuration_parameters(self, rag_config):
        """
        **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
        
        Property 18: RAG Configuration Parameters
        
        For any RAG configuration, all parameters (top_k, min_similarity, chunk_size,
        chunk_overlap) should be stored and retrieved correctly.
        
        This property ensures that RAG configuration parameters maintain their values
        through serialization and deserialization, which is critical for consistent
        RAG behavior across application restarts.
        """
        # Create an agent with the RAG config
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            temperature=0.7,
            language="English",
            web_search_enabled=False,
            mcp_servers=[],
            connection_assignments=[],
            guidelines=[],
            created_at=datetime.now(timezone.utc),
            rag_config=rag_config
        )
        
        # Serialize to dictionary
        agent_dict = agent.to_dict()
        
        # Deserialize back to Agent
        restored_agent = Agent.from_dict(agent_dict)
        
        # Verify RAG config is present
        assert restored_agent.rag_config is not None
        
        # Verify all RAG configuration parameters are preserved
        # Requirement 10.1: top_k parameter
        assert restored_agent.rag_config.top_k == rag_config.top_k
        
        # Requirement 10.2: min_similarity parameter
        assert abs(restored_agent.rag_config.min_similarity - rag_config.min_similarity) < 1e-6
        
        # Requirement 10.3: chunk_size parameter
        assert restored_agent.rag_config.chunk_size == rag_config.chunk_size
        
        # Requirement 10.4: chunk_overlap parameter
        assert restored_agent.rag_config.chunk_overlap == rag_config.chunk_overlap
        
        # Also verify other RAG config fields for completeness
        assert restored_agent.rag_config.enabled == rag_config.enabled
        assert restored_agent.rag_config.embedding_model == rag_config.embedding_model
        assert len(restored_agent.rag_config.knowledge_sources) == len(rag_config.knowledge_sources)
