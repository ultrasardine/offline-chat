#!/usr/bin/env python3
"""
Example RAG-Enabled Agents

This script demonstrates how to create agents with RAG (Retrieval-Augmented Generation)
capabilities using different types of knowledge sources:
1. Web sources only
2. Database sources only
3. Mixed sources (web + database)

Requirements:
- Ollama running locally
- Sample database created (run: uv run python create_sample_db.py)
- Internet connection for web scraping

Note: These examples use enabled=True for demonstration purposes. In production,
consider starting with enabled=False and letting the system enable RAG automatically
when you add and ingest knowledge sources. This ensures RAG is only active when
there's actual content to retrieve from.
"""

import asyncio
from pathlib import Path

from offline_chat import Agent, AgentManager
from offline_chat.rag.models import KnowledgeSource, RAGConfig


def example_1_web_sources():
    """
    Example 1: RAG Agent with Web Sources Only

    This agent can answer questions about Python by referencing official documentation.
    """
    print("\n" + "="*70)
    print("Example 1: RAG Agent with Web Sources")
    print("="*70)

    manager = AgentManager()

    # Create RAG configuration with web sources
    rag_config = RAGConfig(
        enabled=True,
        top_k=5,                              # Retrieve top 5 most relevant chunks
        min_similarity=0.3,                   # Minimum similarity threshold
        chunk_size=512,                       # Size of text chunks
        chunk_overlap=50,                     # Overlap between chunks
        embedding_model="all-MiniLM-L6-v2",  # Sentence transformer model
        knowledge_sources=[
            KnowledgeSource(
                source_type="web",
                identifier="https://docs.python.org/3/tutorial/introduction.html",
                status="pending"
            ),
            KnowledgeSource(
                source_type="web",
                identifier="https://docs.python.org/3/tutorial/controlflow.html",
                status="pending"
            ),
        ]
    )

    # Create agent with RAG
    agent = Agent(
        name="python-docs-assistant",
        display_name="Python Documentation Assistant",
        base_model="llama3:latest",
        system_prompt="""You are a Python expert who answers questions based on
        official Python documentation. Always cite your sources and provide accurate
        information from the documentation.""",
        temperature=0.5,
        rag_config=rag_config
    )

    try:
        manager.create_agent(agent)
        print(f"✓ Created agent: {agent.display_name}")
        print(f"  Knowledge sources: {len(rag_config.knowledge_sources)} web pages")
        print(f"  Top-k: {rag_config.top_k}, Min similarity: {rag_config.min_similarity}")
        print("\nTo use this agent:")
        print("  1. Ingest knowledge sources: manager.add_knowledge_source(...)")
        print("  2. Start chat session: session.start('python-docs-assistant')")
        print("  3. Ask questions like: 'How do I use list comprehensions?'")
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")


def example_2_database_sources():
    """
    Example 2: RAG Agent with Database Sources Only

    This agent can answer questions about company sales data by querying
    indexed database tables.
    """
    print("\n" + "="*70)
    print("Example 2: RAG Agent with Database Sources")
    print("="*70)

    manager = AgentManager()

    # Get path to sample database
    sample_db_path = Path.cwd() / "sample_company.db"

    if not sample_db_path.exists():
        print(f"⚠ Sample database not found at: {sample_db_path}")
        print("  Run: uv run python create_sample_db.py")
        return

    # Create RAG configuration with database sources
    rag_config = RAGConfig(
        enabled=True,
        top_k=8,                              # More chunks for database queries
        min_similarity=0.25,                  # Lower threshold for structured data
        chunk_size=256,                       # Smaller chunks for database rows
        chunk_overlap=0,                      # No overlap for structured data
        embedding_model="all-MiniLM-L6-v2",
        knowledge_sources=[
            KnowledgeSource(
                source_type="database",
                identifier="customers",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="products",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="orders",
                status="pending"
            ),
        ]
    )

    # Create agent with RAG
    agent = Agent(
        name="sales-data-assistant",
        display_name="Sales Data Assistant",
        base_model="llama3:latest",
        system_prompt="""You are a sales data analyst who answers questions based on
        company sales data. Use the indexed database information to provide accurate
        insights about customers, products, and orders. Always cite which tables you're
        referencing.""",
        temperature=0.3,  # Lower temperature for factual data
        rag_config=rag_config
    )

    try:
        manager.create_agent(agent)
        print(f"✓ Created agent: {agent.display_name}")
        print(f"  Knowledge sources: {len(rag_config.knowledge_sources)} database tables")
        print(f"  Tables: {', '.join(s.identifier for s in rag_config.knowledge_sources)}")
        print(f"  Top-k: {rag_config.top_k}, Min similarity: {rag_config.min_similarity}")
        print("\nTo use this agent:")
        print("  1. Ingest database tables: manager.add_knowledge_source(...)")
        print("  2. Start chat session: session.start('sales-data-assistant')")
        print("  3. Ask questions like: 'Who are our top customers?'")
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")


def example_3_mixed_sources():
    """
    Example 3: RAG Agent with Mixed Sources (Web + Database)

    This agent combines web documentation with database information to provide
    comprehensive answers that reference both external knowledge and internal data.
    """
    print("\n" + "="*70)
    print("Example 3: RAG Agent with Mixed Sources (Web + Database)")
    print("="*70)

    manager = AgentManager()

    # Get path to sample database
    sample_db_path = Path.cwd() / "sample_company.db"

    if not sample_db_path.exists():
        print(f"⚠ Sample database not found at: {sample_db_path}")
        print("  Run: uv run python create_sample_db.py")
        return

    # Create RAG configuration with mixed sources
    rag_config = RAGConfig(
        enabled=True,
        top_k=10,                             # More chunks for diverse sources
        min_similarity=0.3,
        chunk_size=512,
        chunk_overlap=50,
        embedding_model="all-MiniLM-L6-v2",
        knowledge_sources=[
            # Web sources - product documentation
            KnowledgeSource(
                source_type="web",
                identifier="https://docs.python.org/3/library/sqlite3.html",
                status="pending"
            ),
            # Database sources - company data
            KnowledgeSource(
                source_type="database",
                identifier="customers",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="products",
                status="pending"
            ),
        ]
    )

    # Create agent with RAG
    agent = Agent(
        name="research-assistant",
        display_name="Research Assistant",
        base_model="llama3:latest",
        system_prompt="""You are a research assistant with access to both external
        documentation and internal company data. When answering questions:
        1. Reference external documentation for technical concepts
        2. Reference internal data for company-specific information
        3. Clearly distinguish between external and internal sources
        4. Provide comprehensive answers that combine both perspectives""",
        temperature=0.6,
        rag_config=rag_config
    )

    try:
        manager.create_agent(agent)
        print(f"✓ Created agent: {agent.display_name}")
        print(f"  Knowledge sources: {len(rag_config.knowledge_sources)} total")

        web_sources = [s for s in rag_config.knowledge_sources if s.source_type == "web"]
        db_sources = [s for s in rag_config.knowledge_sources if s.source_type == "database"]

        print(f"    - Web sources: {len(web_sources)}")
        for source in web_sources:
            print(f"      • {source.identifier}")

        print(f"    - Database sources: {len(db_sources)}")
        for source in db_sources:
            print(f"      • {source.identifier}")

        print(f"  Top-k: {rag_config.top_k}, Min similarity: {rag_config.min_similarity}")
        print("\nTo use this agent:")
        print("  1. Ingest all sources: manager.add_knowledge_source(...)")
        print("  2. Start chat session: session.start('research-assistant')")
        print("  3. Ask questions like: 'How can I query our customer database using Python?'")
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")


async def demo_chat_with_rag_agent():
    """
    Bonus: Interactive demo showing how to chat with a RAG-enabled agent.

    This demonstrates the complete workflow:
    1. Create agent with RAG
    2. Ingest knowledge sources
    3. Chat with the agent
    4. See source citations in responses
    """
    print("\n" + "="*70)
    print("Bonus: Interactive Chat Demo with RAG Agent")
    print("="*70)

    manager = AgentManager()

    # Create a simple RAG agent
    rag_config = RAGConfig(
        enabled=True,
        top_k=3,
        min_similarity=0.3,
        knowledge_sources=[
            KnowledgeSource(
                source_type="web",
                identifier="https://docs.python.org/3/tutorial/introduction.html",
                status="pending"
            ),
        ]
    )

    agent = Agent(
        name="demo-rag-agent",
        display_name="Demo RAG Agent",
        base_model="llama3:latest",
        system_prompt="You answer questions based on Python documentation.",
        temperature=0.5,
        rag_config=rag_config
    )

    try:
        # Create agent
        manager.create_agent(agent)
        print(f"✓ Created agent: {agent.display_name}")

        # Note: In a real scenario, you would ingest knowledge sources here
        # manager.add_knowledge_source(agent.name, "web", "https://...", ingest=True)

        print("\n⚠ Note: This is a demo. In production, you would:")
        print("  1. Ingest knowledge sources before chatting")
        print("  2. Wait for ingestion to complete")
        print("  3. Then start the chat session")

        print("\nExample chat flow:")
        print("  You: How do I use Python strings?")
        print("  Agent: [Retrieves relevant chunks from documentation]")
        print("  Agent: Based on the Python documentation, strings in Python...")
        print("  Agent: Sources: https://docs.python.org/3/tutorial/introduction.html")

    except Exception as e:
        print(f"✗ Failed: {e}")
    finally:
        # Clean up demo agent
        try:
            manager.delete_agent("demo-rag-agent")
            print("\n✓ Cleaned up demo agent")
        except Exception:
            pass


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("RAG-Enabled Agent Examples")
    print("="*70)
    print("\nThis script demonstrates three types of RAG-enabled agents:")
    print("  1. Web sources only - Answers from web documentation")
    print("  2. Database sources only - Answers from indexed database tables")
    print("  3. Mixed sources - Combines web docs and database data")

    # Run examples
    example_1_web_sources()
    example_2_database_sources()
    example_3_mixed_sources()

    # Run interactive demo
    asyncio.run(demo_chat_with_rag_agent())

    print("\n" + "="*70)
    print("Examples Complete!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Review the created agents: make agents")
    print("  2. Ingest knowledge sources for each agent")
    print("  3. Start chatting: make run")
    print("\nFor more information, see the RAG section in README.md")


if __name__ == "__main__":
    main()
