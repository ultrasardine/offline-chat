# Offline Chat

A terminal-based chatbot application that uses local Ollama models. Create personalized AI agents with specific personas, system prompts, and maintain conversation history across sessions.

## Features

- **Custom Agents**: Create AI agents with unique names, personas, and behaviors
- **Persistent History**: Conversation history is saved and restored across sessions
- **Local & Private**: All processing happens locally using Ollama - no data leaves your machine
- **Web Search**: Enable agents to search the web and fetch pages for current information
- **Database Access**: Connect agents to Oracle, PostgreSQL, MySQL, or SQLite databases for data analysis
- **RAG (Retrieval-Augmented Generation)**: Enable agents to query external documents, web pages, and database tables as knowledge sources
- **MCP Server Integration**: Connect agents to Model Context Protocol servers for extended tool capabilities
- **Library Support**: Use as a CLI tool or import as a Python library

## Requirements

- Python 3.13+
- [Ollama](https://ollama.ai/) installed and running locally
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

### From Source

```bash
# Clone the repository
git clone <repo-url>
cd offline-chat

# Install dependencies
make install

# Or with dev dependencies (testing, linting)
make install-dev
```

### As a Library

```bash
uv add git+<repo-url>
```

## Quick Start

1. **Ensure Ollama is running**:
   ```bash
   ollama serve
   ```

2. **Start the application**:
   ```bash
   make run
   ```

3. **Create your first agent** from the main menu and start chatting!

## Usage

### CLI Application

Start the interactive CLI:

```bash
make run
```

This opens the main menu:

```
Offline Chat - Main Menu

1. Create new agent
2. List agents
3. Chat with agent
4. Delete agent
5. Exit
6. Update agent

Select option: 
```

### Creating an Agent

Select option `1` from the main menu:

```
Create New Agent
================

Agent name (kebab-case): german-tutor
Display name: German Language Tutor
Base model [llama3:latest]: 
System prompt: You are a friendly German language tutor. Help users learn 
German through conversation, correct their mistakes gently, and explain 
grammar rules when asked.
Temperature (0.0-1.0) [0.7]: 
Response language [English]: 
Enable web search? (y/N): 

Creating agent 'german-tutor'... Done!
```

- **Agent name**: Unique identifier using lowercase letters, numbers, and hyphens
- **Display name**: Human-readable name shown in chat
- **Base model**: Ollama model to use (press Enter for default)
- **System prompt**: Define the agent's persona and behavior
- **Temperature**: Controls creativity (0.0 = focused, 1.0 = creative)
- **Web search**: Enable the agent to search the web and fetch pages (requires tool-capable model like llama3.1 or qwen3)

### Listing Agents

Select option `2` to see all created agents:

```
Your Agents
===========

  german-tutor         German Language Tutor      (llama3:latest)
  code-reviewer        Code Reviewer              (llama3:latest)

Total: 2 agents
```

Or use the make target:

```bash
make agents
```

### Chatting with an Agent

Select option `3`, then choose an agent:

```
Select an agent:
  1. German Language Tutor (german-tutor)
  2. Code Reviewer (code-reviewer)
  0. Cancel

Select agent: 1

[German Language Tutor] - Commands: exit, clear
================================================

You: How do I say hello in German?

German Language Tutor: In German, you say "Hallo" for a casual greeting, 
or "Guten Tag" for a more formal hello...

You: exit
Saving conversation... Done!
```

**Chat commands:**
- Type your message and press Enter to send
- `exit` - Save conversation and return to main menu
- `clear` - Reset conversation history (start fresh)
- `Ctrl+C` - Emergency exit (saves pending data)

### Deleting an Agent

Select option `4`, choose the agent, and confirm:

```
Select an agent to delete:
  1. German Language Tutor (german-tutor)
  2. Code Reviewer (code-reviewer)
  0. Cancel

Select agent: 1

Are you sure you want to delete 'German Language Tutor'? (y/N): y

Deleting agent 'german-tutor'... Done!
```

This removes:
- The Ollama model
- Agent configuration files
- All conversation history

### Updating an Agent

Select option `6`, choose the agent, and select what to update:

```
Update Agent
========================================

Available agents:
  1. german-tutor (German Language Tutor)
  2. code-reviewer (Code Reviewer)
  0. Cancel

Select agent to update: 1

Update Options for: german-tutor
----------------------------------------
  1. Update base model
  2. Update database connections
  3. Manage guidelines
  4. Configure RAG capabilities
  5. Back to agent selection

Select option: 
```

#### Updating Base Model

Select option `1` to change the Ollama model an agent uses:

```
Update Base Model: german-tutor
========================================

Current base model: llama3:latest

Recommended models for tool calling:
  - llama3.2:latest (recommended)
  - mistral:latest (fast alternative)
  - qwen2.5:latest (best for tools)

Other options:
  - llama3.1:latest (current, limited tool support)
  - llama3:latest (older version)

Enter new base model (or 'cancel' to abort): llama3.2:latest

Change base model from 'llama3:latest' to 'llama3.2:latest'?
Continue? (y/N): y

Updating base model... Done!

✓ Base model updated to 'llama3.2:latest' successfully.

Note: The agent will use the new model in the next chat session.

Tip: Make sure the model is available in Ollama:
  ollama pull llama3.2:latest
```

This is particularly useful when:
- Upgrading to a model with better tool calling support
- Switching to a faster or more capable model
- Testing different models for your use case
- Fixing issues with models that have limited tool support

**Note**: Make sure to pull the new model with `ollama pull <model-name>` before using it.

#### Configuring RAG Capabilities

Select option `4` to enable or configure RAG (Retrieval-Augmented Generation) for an agent:

```
Configure RAG: german-tutor
========================================

RAG Status: ✗ Disabled

Would you like to enable RAG for this agent?

Enable RAG? (y/N): y

Enable RAG Configuration
----------------------------------------
Top-K (number of chunks to retrieve) [5]: 
Minimum similarity threshold (0.0-1.0) [0.3]: 
Chunk size (characters) [512]: 
Chunk overlap (characters) [50]: 

Embedding models:
  1. all-MiniLM-L6-v2 (fast, recommended)
  2. all-mpnet-base-v2 (better quality, slower)
  3. paraphrase-multilingual-MiniLM-L12-v2 (multilingual)
Select embedding model [1]: 

Configuring RAG... Done!

✓ RAG configured successfully for 'german-tutor'.

⚠️  Important: RAG is currently DISABLED
   RAG will be automatically enabled when you add knowledge sources.

Next steps:
  1. Add knowledge sources via 'Manage RAG knowledge sources' menu
  2. Ingest the sources to build the vector store
  3. RAG will be enabled automatically
  4. Start chatting with RAG-enhanced responses
```

For agents with RAG already enabled, you can:
- **Modify RAG parameters**: Adjust top-k, similarity threshold, chunk size, and overlap
- **Disable RAG**: Turn off RAG while keeping knowledge sources and vector store intact

**RAG Configuration Options**:
- **Top-K**: Number of relevant chunks to retrieve (1-20, default: 5)
- **Min Similarity**: Minimum similarity score for retrieval (0.0-1.0, default: 0.3)
- **Chunk Size**: Size of text chunks in characters (100-2000, default: 512)
- **Chunk Overlap**: Overlap between chunks in characters (0-500, default: 50)
- **Embedding Model**: Sentence transformer model for generating embeddings

See the [RAG section](#rag-retrieval-augmented-generation) for more details on RAG capabilities and knowledge source management.

### Viewing Agent Information

Use make targets to inspect agents without starting the CLI:

```bash
# List all agents
make agents

# List available Ollama models
make models

# View agent configuration
make agent-info AGENT=german-tutor

# View chat history
make history AGENT=german-tutor
```

### Library Usage

Import `offline_chat` into your Python project to programmatically manage agents and chat sessions.

#### Installation in Your Project

```bash
# Using uv
uv add git+<repo-url>

# Or using pip
pip install git+<repo-url>
```

#### Basic Example

```python
from offline_chat import Agent, AgentManager, ChatSession

# Create an agent manager (uses default data directory)
manager = AgentManager()

# Create a new agent
agent = Agent(
    name="code-helper",
    display_name="Code Helper",
    base_model="llama3:latest",
    system_prompt="You are a helpful coding assistant.",
    temperature=0.7,
    language="English",  # Language for responses (default: English)
    web_search_enabled=False  # Enable web search (default: False)
)
manager.create_agent(agent)

# Start a chat session
session = ChatSession(manager)
session.start("code-helper")

# Send messages (returns a generator for streaming)
for chunk in session.send_message("How do I write a for loop in Python?"):
    print(chunk, end="", flush=True)

# End the session (saves history)
session.end()
```

#### Managing Agents

```python
from offline_chat import Agent, AgentManager

manager = AgentManager()

# List all agents
agents = manager.list_agents()
for agent in agents:
    print(f"{agent.name}: {agent.display_name}")

# Get a specific agent
agent = manager.get_agent("code-helper")
if agent:
    print(f"Found: {agent.display_name}")

# Check if an agent exists
if manager.agent_exists("code-helper"):
    print("Agent exists!")

# Delete an agent (removes model, config, and history)
manager.delete_agent("code-helper")
```

#### Updating Agents

Update an existing agent's configuration programmatically:

```python
from offline_chat import AgentManager
from offline_chat.database.result import is_ok, unwrap, unwrap_err

manager = AgentManager()

# Update base model (automatically recreates Ollama model)
result = manager.update_agent(
    "code-helper",
    {"base_model": "llama3.2:latest"}
)

if is_ok(result):
    agent = unwrap(result)
    print(f"Updated agent to use {agent.base_model}")
else:
    print(f"Update failed: {unwrap_err(result)}")

# Update multiple fields at once
result = manager.update_agent(
    "code-helper",
    {
        "base_model": "qwen2.5:latest",
        "system_prompt": "You are an expert code reviewer with a focus on security.",
        "temperature": 0.4,
        "language": "English"
    }
)

# Update web search setting
result = manager.update_agent(
    "research-assistant",
    {"web_search_enabled": True}
)

# Update guidelines
result = manager.update_agent(
    "data-analyst",
    {"guidelines": [
        "Always explain SQL queries before executing",
        "Provide data visualizations when possible",
        "Focus on actionable insights"
    ]}
)

# Enable RAG on an existing agent
from offline_chat.rag.models import RAGConfig

result = manager.update_agent(
    "python-expert",
    {"rag_config": RAGConfig(
        enabled=True,
        top_k=8,
        min_similarity=0.25,
        chunk_size=512,
        chunk_overlap=50,
        embedding_model="all-MiniLM-L6-v2",
        knowledge_sources=[]
    )}
)

# Modify RAG parameters on a RAG-enabled agent
result = manager.update_agent(
    "python-expert",
    {"rag_config": RAGConfig(
        enabled=True,
        top_k=10,  # Increased from 8
        min_similarity=0.4,  # Increased from 0.25
        chunk_size=512,
        chunk_overlap=50,
        embedding_model="all-MiniLM-L6-v2",
        knowledge_sources=[]  # Preserve existing sources
    )}
)

# Disable RAG (keeps vector store and knowledge sources intact)
result = manager.update_agent(
    "python-expert",
    {"rag_config": None}
)
```

**Supported update fields**:
- `base_model` (str) - Ollama model name (e.g., "llama3.2:latest")
- `system_prompt` (str) - Agent's persona and behavior
- `temperature` (float) - Response creativity (0.0-1.0)
- `language` (str) - Response language
- `web_search_enabled` (bool) - Enable/disable web search
- `connection_assignments` (list) - Database connection assignments
- `mcp_servers` (list) - MCP server configurations
- `guidelines` (list[str]) - Agent guidelines
- `rag_config` (RAGConfig | None) - RAG configuration for knowledge retrieval

**Note**: When updating `base_model`, the Ollama model is automatically recreated with the new base model. Make sure the new model is available in Ollama (`ollama pull <model-name>`) before updating.

#### Working with Chat Sessions

```python
from offline_chat import AgentManager, ChatSession

manager = AgentManager()
session = ChatSession(manager)

# Start a session with an existing agent
session.start("german-tutor")

# Send a message - returns a generator that streams the response
# Option 1: Stream response in real-time (prints as agent responds)
print("Agent: ", end="")
for chunk in session.send_message("Wie geht es dir?"):
    print(chunk, end="", flush=True)
print()  # Newline after response

# Option 2: Collect the full response as a string
response = "".join(session.send_message("How do I say goodbye?"))
print(f"Agent: {response}")

# Access the full conversation history
print("\n--- Conversation History ---")
for msg in session.history.messages:
    role = "You" if msg.role == "user" else "Agent"
    print(f"[{msg.timestamp}] {role}: {msg.content}")

# Get just the last message (the agent's most recent response)
if session.history.messages:
    last_msg = session.history.messages[-1]
    print(f"\nLast response: {last_msg.content}")

# Clear conversation history (start fresh)
session.clear_history()

# End session (automatically saves history to disk)
session.end()
```

#### Complete Chat Loop Example

```python
from offline_chat import AgentManager, ChatSession

def chat_with_agent(agent_name: str):
    """Interactive chat loop with an agent."""
    manager = AgentManager()
    session = ChatSession(manager)
    
    try:
        session.start(agent_name)
        print(f"Chatting with {session.get_display_name()}")
        print("Type 'quit' to exit, 'history' to see conversation\n")
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() == "quit":
                break
            elif user_input.lower() == "history":
                for msg in session.history.messages:
                    role = "You" if msg.role == "user" else "Agent"
                    print(f"  {role}: {msg.content[:50]}...")
                continue
            elif not user_input:
                continue
            
            # Send message and stream response
            print(f"{session.get_display_name()}: ", end="")
            for chunk in session.send_message(user_input):
                print(chunk, end="", flush=True)
            print()
    
    finally:
        session.end()
        print("\nConversation saved!")

# Usage
chat_with_agent("german-tutor")
```

#### Error Handling

```python
from offline_chat import Agent, AgentManager
from offline_chat.exceptions import (
    AgentExistsError,
    AgentNotFoundError,
    InvalidAgentNameError,
    OllamaConnectionError,
    OllamaCommandError,
    MCPConfigError,
)

manager = AgentManager()

try:
    agent = Agent(
        name="my-agent",
        display_name="My Agent",
        base_model="llama3:latest",
        system_prompt="You are helpful.",
        temperature=0.7
    )
    manager.create_agent(agent)
except InvalidAgentNameError:
    print("Agent name must be kebab-case (lowercase, numbers, hyphens)")
except AgentExistsError:
    print("An agent with this name already exists")
except OllamaCommandError as e:
    print(f"Ollama error: {e}")
except MCPConfigError as e:
    print(f"MCP configuration error: {e}")
```

## Agent Configuration

Each agent is defined by:

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Unique identifier (kebab-case) | `german-tutor` |
| `display_name` | Human-readable name | `German Language Tutor` |
| `base_model` | Ollama model to use | `llama3:latest` |
| `system_prompt` | Persona and behavior definition | `You are a friendly German tutor...` |
| `temperature` | Response creativity (0.0-1.0) | `0.7` |
| `language` | Language for agent responses | `English` |
| `web_search_enabled` | Enable web search and fetch tools | `False` |
| `mcp_servers` | List of MCP server configurations | `[]` |
| `rag_config` | Optional RAG configuration for knowledge retrieval | `None` |

### Example Agents

**German Tutor**:
```
Name: german-tutor
Base Model: llama3:latest
System Prompt: You are a friendly German language tutor. Help users learn 
German through conversation, correct their mistakes gently, and explain 
grammar rules when asked.
Temperature: 0.7
Language: English
```

**Code Reviewer**:
```
Name: code-reviewer
Base Model: llama3:latest
System Prompt: You are an expert code reviewer. Analyze code for bugs, 
security issues, and style violations. Provide constructive feedback.
Temperature: 0.3
Language: English
```

## Data Storage

Agent data is stored in `~/.offline-chat/` by default:

```
~/.offline-chat/
├── agents/                    # Agent configurations
│   └── {agent_name}/
│       ├── config.json        # Agent settings
│       └── Modelfile          # Ollama Modelfile
├── history/                   # Conversation histories
│   └── {agent_name}.json
└── data/
    └── rag/                   # RAG vector store data
        └── {agent_name}/      # Per-agent vector collections
```

## RAG (Retrieval-Augmented Generation)

Agents can be configured with RAG capabilities to retrieve and use information from external knowledge sources during conversations. This allows agents to provide accurate, context-aware responses based on your documents, web pages, and database tables.

### Understanding RAG Concepts

Before configuring RAG, it's helpful to understand these key concepts:

#### What is RAG?

**Retrieval-Augmented Generation (RAG)** is a technique that enhances AI responses by retrieving relevant information from external sources before generating an answer. Instead of relying solely on the model's training data, RAG allows your agent to:
- Access up-to-date information from documents and databases
- Provide accurate answers based on your specific data
- Cite sources for transparency and verification

#### Key RAG Parameters Explained

**Top-K (Number of Chunks to Retrieve)**
- **What it is**: How many relevant text chunks to retrieve from your knowledge base
- **Example**: If set to 5, the agent will find the 5 most relevant pieces of information
- **When to adjust**:
  - Increase (7-10) for complex questions needing more context
  - Decrease (3-5) for simple questions or faster responses
- **Default**: 5 chunks

**Minimum Similarity Threshold**
- **What it is**: How similar a chunk must be to your question to be included (0.0 = no match, 1.0 = perfect match)
- **Example**: With 0.3 threshold, only chunks scoring 0.3 or higher are used
- **When to adjust**:
  - Lower (0.2-0.3) to retrieve more loosely related information
  - Raise (0.4-0.5) to only get highly relevant matches
- **Default**: 0.3

**Chunk Size**
- **What it is**: How many characters each piece of text contains when documents are split
- **Example**: A 512-character chunk is roughly 1-2 paragraphs
- **When to adjust**:
  - Larger (800-1000) for documents with long, connected ideas
  - Smaller (256-400) for structured data or short facts
- **Default**: 512 characters

**Chunk Overlap**
- **What it is**: How many characters overlap between consecutive chunks to preserve context
- **Example**: With 50-character overlap, the last 50 characters of one chunk appear in the next
- **When to adjust**:
  - Increase (100-150) to preserve more context across chunk boundaries
  - Decrease (0-25) for independent facts or structured data
- **Default**: 50 characters

**Embedding Model**
- **What it is**: The AI model that converts text into numerical vectors for similarity comparison
- **Available options**:
  - `all-MiniLM-L6-v2`: Fast, good quality, recommended for most use cases
  - `all-mpnet-base-v2`: Better quality but slower, for critical applications
  - `paraphrase-multilingual-MiniLM-L12-v2`: For non-English content
- **Default**: all-MiniLM-L6-v2

### How RAG Works

1. **Ingestion**: Documents, web pages, or database rows are chunked and embedded into a vector store
2. **Retrieval**: When you ask a question, relevant chunks are retrieved based on semantic similarity
3. **Augmentation**: Retrieved context is added to the prompt with source attribution
4. **Generation**: The agent responds based only on the provided context, citing sources

### RAG Configuration

RAG is configured per-agent using the `RAGConfig` dataclass:

```python
from offline_chat import Agent, AgentManager
from offline_chat.rag.models import RAGConfig, KnowledgeSource

manager = AgentManager()

# Create RAG configuration
rag_config = RAGConfig(
    enabled=True,                          # Enable RAG for this agent
    top_k=5,                               # Number of chunks to retrieve
    min_similarity=0.3,                    # Minimum similarity threshold (0.0-1.0)
    chunk_size=512,                        # Size of text chunks in characters
    chunk_overlap=50,                      # Overlap between chunks
    embedding_model="all-MiniLM-L6-v2",   # Sentence transformer model
    knowledge_sources=[                    # List of knowledge sources
        KnowledgeSource(
            source_type="web",
            identifier="https://docs.python.org/3/",
            status="pending"
        ),
        KnowledgeSource(
            source_type="database",
            identifier="products",         # Table name
            status="pending"
        )
    ]
)

# Create agent with RAG
agent = Agent(
    name="python-expert",
    display_name="Python Expert",
    base_model="llama3:latest",
    system_prompt="You are a Python expert who answers questions based on documentation.",
    temperature=0.7,
    rag_config=rag_config
)
manager.create_agent(agent)
# Vector collection is automatically created when the agent is created
```

**Note**: When you create an agent with RAG enabled, a vector collection is automatically created in the vector store. The collection is named after the agent and configured with the appropriate embedding dimensions. You can then ingest knowledge sources to populate the collection.

**Best Practice**: If you're adding knowledge sources incrementally, consider starting with `enabled=False` and letting the system enable RAG automatically when you add and ingest your first knowledge source. This ensures RAG is only active when there's actual content to retrieve from.

### Enabling RAG on Existing Agents

You can enable RAG on agents that were created without it, or modify RAG settings on existing RAG-enabled agents:

```python
from offline_chat import AgentManager
from offline_chat.rag.models import RAGConfig
from offline_chat.database.result import is_ok, unwrap_err

manager = AgentManager()

# Enable RAG on an existing agent
rag_config = RAGConfig(
    enabled=True,
    top_k=5,
    min_similarity=0.3,
    chunk_size=512,
    chunk_overlap=50,
    embedding_model="all-MiniLM-L6-v2",
    knowledge_sources=[]  # Start with empty sources, add later
)

result = manager.update_agent("existing-agent", {"rag_config": rag_config})

if is_ok(result):
    print("✓ RAG enabled successfully")
    # Now add knowledge sources and ingest them
else:
    print(f"✗ Failed: {unwrap_err(result)}")

# Modify RAG parameters on a RAG-enabled agent
updated_config = RAGConfig(
    enabled=True,
    top_k=10,  # Increased from 5
    min_similarity=0.4,  # Increased from 0.3
    chunk_size=512,
    chunk_overlap=50,
    embedding_model="all-MiniLM-L6-v2",
    knowledge_sources=[]  # Preserve existing sources
)

result = manager.update_agent("existing-agent", {"rag_config": updated_config})

# Disable RAG (keeps vector store and knowledge sources intact)
result = manager.update_agent("existing-agent", {"rag_config": None})

if is_ok(result):
    print("✓ RAG disabled - vector store and sources preserved")
    # Can re-enable later without re-ingesting
```

**Important Notes**:
- Enabling RAG creates a vector collection if it doesn't exist
- **Best Practice**: Start with `enabled=False` and let the system enable RAG automatically when you add knowledge sources
- Disabling RAG (setting to `None`) keeps the vector store and knowledge sources intact
- You can re-enable RAG later without re-ingesting sources
- Modifying parameters (top_k, min_similarity, etc.) takes effect immediately
- Changing chunk_size or chunk_overlap requires re-ingesting sources to take effect

### Knowledge Source Types

**Web Sources**:
- Scrape and index content from URLs
- Automatically extracts text from HTML
- Supports retry logic and rate limiting

**Database Sources**:
- Index rows from database tables
- Converts rows to text representations
- Preserves column names and values

### RAG Parameters Reference

| Parameter | Description | Default | Recommended Range |
|-----------|-------------|---------|-------------------|
| `enabled` | Enable/disable RAG for this agent | `False` | `True`/`False` |
| `top_k` | Number of most relevant chunks to retrieve per query | `5` | 3-10 (higher for complex topics) |
| `min_similarity` | Minimum similarity score (0.0-1.0) for a chunk to be included | `0.3` | 0.2-0.5 (lower = more results) |
| `chunk_size` | Size of each text chunk in characters | `512` | 256-1000 (larger for connected ideas) |
| `chunk_overlap` | Characters that overlap between consecutive chunks | `50` | 0-150 (higher preserves context) |
| `embedding_model` | Sentence transformer model for generating embeddings | `"all-MiniLM-L6-v2"` | See embedding model options above |

**Tuning Tips**:
- Start with defaults and adjust based on response quality
- If responses lack context, increase `top_k` or lower `min_similarity`
- If responses include irrelevant information, decrease `top_k` or raise `min_similarity`
- For technical documentation, use larger `chunk_size` (800-1000)
- For FAQs or structured data, use smaller `chunk_size` (256-400)

### Managing Knowledge Sources

After creating a RAG-enabled agent, you can add, re-index, and list knowledge sources programmatically:

#### Adding Knowledge Sources

Add new knowledge sources to an agent and optionally trigger immediate ingestion:

```python
from offline_chat import AgentManager
from offline_chat.database.result import is_ok, unwrap, unwrap_err

manager = AgentManager()

# Add a web source with immediate ingestion
result = manager.add_knowledge_source(
    agent_name="python-expert",
    source_type="web",
    identifier="https://docs.python.org/3/tutorial/",
    ingest=True,  # Trigger ingestion immediately (default: True)
    progress_callback=lambda msg: print(f"  {msg}")  # Optional progress updates
)

if is_ok(result):
    print("Knowledge source added and ingested successfully!")
else:
    print(f"Error: {unwrap_err(result)}")

# Add a database source without immediate ingestion
result = manager.add_knowledge_source(
    agent_name="data-analyst",
    source_type="database",
    identifier="sales_table",
    ingest=False  # Add to config but don't ingest yet
)

if is_ok(result):
    print("Knowledge source added. Run re-index to ingest content.")
```

**Parameters**:
- `agent_name` (str): Name of the agent to update
- `source_type` (str): Type of source - `"web"` or `"database"`
- `identifier` (str): URL for web sources, table name for database sources
- `ingest` (bool): If `True`, trigger ingestion immediately (default: `True`)
- `progress_callback` (callable): Optional callback function for progress updates

**Returns**: `Result[None, str]` - Success or error message

#### Re-indexing Knowledge Sources

Re-index existing knowledge sources to update their content:

```python
from offline_chat import AgentManager
from offline_chat.database.result import is_ok, unwrap_err

manager = AgentManager()

# Re-index a web source (useful when content has changed)
result = manager.reindex_knowledge_source(
    agent_name="python-expert",
    source_identifier="https://docs.python.org/3/tutorial/",
    progress_callback=lambda msg: print(f"  {msg}")
)

if is_ok(result):
    print("Knowledge source re-indexed successfully!")
else:
    print(f"Error: {unwrap_err(result)}")

# Re-index a database source
result = manager.reindex_knowledge_source(
    agent_name="data-analyst",
    source_identifier="sales_table"
)
```

**Parameters**:
- `agent_name` (str): Name of the agent
- `source_identifier` (str): URL or table name of the source to re-index
- `progress_callback` (callable): Optional callback function for progress updates

**Returns**: `Result[None, str]` - Success or error message

**Note**: Re-indexing clears old embeddings and re-ingests the content. This is useful when:
- Web page content has been updated
- Database table data has changed
- You want to refresh the knowledge base

#### Listing Knowledge Sources

List all configured knowledge sources for an agent with their status:

```python
from offline_chat import AgentManager
from offline_chat.database.result import is_ok, unwrap, unwrap_err

manager = AgentManager()

# List all knowledge sources for an agent
result = manager.list_knowledge_sources("python-expert")

if is_ok(result):
    sources = unwrap(result)
    
    print(f"Knowledge sources for 'python-expert': {len(sources)}")
    for source in sources:
        print(f"\n  Type: {source.source_type}")
        print(f"  Identifier: {source.identifier}")
        print(f"  Status: {source.status}")
        
        if source.last_indexed:
            print(f"  Last indexed: {source.last_indexed.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if source.error_message:
            print(f"  Error: {source.error_message}")
else:
    print(f"Error: {unwrap_err(result)}")
```

**Parameters**:
- `agent_name` (str): Name of the agent

**Returns**: `Result[list[KnowledgeSource], str]` - List of knowledge sources or error message

**Knowledge Source Status Values**:
- `"pending"` - Source added but not yet ingested
- `"active"` - Source successfully ingested and available
- `"failed"` - Ingestion failed (check `error_message` for details)

#### Complete Management Example

```python
from offline_chat import Agent, AgentManager
from offline_chat.rag.models import RAGConfig
from offline_chat.database.result import is_ok, unwrap, unwrap_err

manager = AgentManager()

# Create RAG-enabled agent
agent = Agent(
    name="docs-assistant",
    display_name="Documentation Assistant",
    base_model="llama3:latest",
    system_prompt="You help users understand documentation.",
    temperature=0.5,
    rag_config=RAGConfig(
        enabled=True,
        top_k=5,
        min_similarity=0.3,
        knowledge_sources=[]  # Start with empty sources
    )
)
manager.create_agent(agent)

# Add multiple knowledge sources
sources_to_add = [
    ("web", "https://docs.python.org/3/tutorial/"),
    ("web", "https://docs.python.org/3/library/"),
    ("database", "documentation_table")
]

for source_type, identifier in sources_to_add:
    print(f"\nAdding {source_type} source: {identifier}")
    result = manager.add_knowledge_source(
        agent_name="docs-assistant",
        source_type=source_type,
        identifier=identifier,
        ingest=True,
        progress_callback=lambda msg: print(f"  {msg}")
    )
    
    if is_ok(result):
        print("  ✓ Success")
    else:
        print(f"  ✗ Failed: {unwrap_err(result)}")

# List all sources with their status
print("\n" + "="*50)
print("Knowledge Sources Summary")
print("="*50)

result = manager.list_knowledge_sources("docs-assistant")
if is_ok(result):
    sources = unwrap(result)
    for source in sources:
        status_icon = {
            "active": "✓",
            "failed": "✗",
            "pending": "○"
        }.get(source.status, "?")
        
        print(f"\n[{status_icon}] {source.source_type}: {source.identifier}")
        print(f"    Status: {source.status}")
        if source.last_indexed:
            print(f"    Last indexed: {source.last_indexed.strftime('%Y-%m-%d %H:%M')}")
        if source.error_message:
            print(f"    Error: {source.error_message}")

# Re-index a specific source if needed
print("\n" + "="*50)
print("Re-indexing a source")
print("="*50)

result = manager.reindex_knowledge_source(
    agent_name="docs-assistant",
    source_identifier="https://docs.python.org/3/tutorial/",
    progress_callback=lambda msg: print(f"  {msg}")
)

if is_ok(result):
    print("✓ Re-indexing complete")
else:
    print(f"✗ Re-indexing failed: {unwrap_err(result)}")
```

### Using RAG in Chat Sessions

When chatting with a RAG-enabled agent, responses are based on retrieved context:

```python
from offline_chat import AgentManager, ChatSession

manager = AgentManager()
session = ChatSession(manager)

session.start("python-expert")

# Agent retrieves relevant context and cites sources
for chunk in session.send_message("How do I use list comprehensions?"):
    print(chunk, end="", flush=True)

session.end()
```

The agent will:
1. Retrieve relevant chunks from knowledge sources
2. Include context in the prompt with source attribution
3. Respond based only on the provided context
4. Cite sources in the response

### RAG Instructions

RAG-enabled agents are automatically instructed to:
- Respond only based on provided context
- Cite sources for all information
- Acknowledge when information is insufficient
- Never fabricate or hallucinate information
- Quote or paraphrase directly from context

### Vector Store

RAG uses ChromaDB for vector storage:
- Persistent storage in `~/.offline-chat/data/rag/`
- One collection per agent
- Automatic embedding generation using sentence-transformers
- Efficient similarity search with configurable thresholds

### Example: Documentation Assistant

```python
from offline_chat import Agent, AgentManager
from offline_chat.rag.models import RAGConfig, KnowledgeSource

rag_config = RAGConfig(
    enabled=True,
    top_k=8,
    min_similarity=0.4,
    knowledge_sources=[
        KnowledgeSource(
            source_type="web",
            identifier="https://docs.python.org/3/tutorial/",
            status="pending"
        ),
        KnowledgeSource(
            source_type="web",
            identifier="https://docs.python.org/3/library/",
            status="pending"
        )
    ]
)

agent = Agent(
    name="python-docs",
    display_name="Python Documentation Assistant",
    base_model="llama3:latest",
    system_prompt="You help users understand Python by referencing official documentation.",
    temperature=0.5,
    rag_config=rag_config
)
```

### RAG Examples

The `examples_rag_agents.py` script demonstrates how to create RAG-enabled agents with different types of knowledge sources. Run it to see complete examples:

```bash
uv run python examples_rag_agents.py
```

**Example 1: Web Sources Only**
- Agent that answers questions about Python using official documentation
- Demonstrates web scraping and indexing
- Shows how to configure RAG parameters for web content

**Example 2: Database Sources Only**
- Agent that analyzes company sales data from database tables
- Demonstrates database table indexing
- Shows optimal RAG settings for structured data (smaller chunks, lower threshold)

**Example 3: Mixed Sources (Web + Database)**
- Agent that combines external documentation with internal data
- Demonstrates multi-source knowledge integration
- Shows how to handle diverse content types

**Example 4: Interactive Chat Demo**
- Complete workflow from agent creation to chat interaction
- Demonstrates knowledge source ingestion
- Shows source citation in responses

Each example includes:
- Complete agent configuration with RAG settings
- Knowledge source definitions
- Usage instructions and sample questions
- Best practices for different source types

See the script for full implementation details and copy-paste ready code.

### RAG Error Handling and Resilience

The RAG system includes robust error handling to ensure reliable operation:

**Automatic Fallback to Non-RAG Mode**:
- If the vector store is unavailable, the agent automatically falls back to standard chat
- Logs warnings for debugging while continuing to function
- No user intervention required

**Graceful Ingestion Failures**:
- Web scraping failures (404, timeouts, network errors) are logged but don't stop other sources
- Embedding generation failures are caught and reported per-source
- Failed sources are marked with status and error messages for troubleshooting

**Corrupted Collection Recovery**:
```python
from offline_chat import AgentManager
from offline_chat.rag.orchestrator import RAGOrchestrator
from offline_chat.rag.vector_store import VectorStore
from pathlib import Path

# Check collection health
manager = AgentManager()
agent = manager.get_agent("python-expert")

# Create RAG components
data_dir = Path.home() / ".offline-chat" / "data" / "rag"
vector_store = VectorStore(data_dir)

# Check if collection is corrupted
is_corrupted, error_msg = vector_store.is_collection_corrupted(agent.name)
if is_corrupted:
    print(f"Collection corrupted: {error_msg}")
    
    # Rebuild the collection
    success, message = vector_store.rebuild_collection(
        collection_name=agent.name,
        embedding_dimension=384,
        force=False  # Only rebuild if corrupted
    )
    
    if success:
        print(message)
        # Re-ingest knowledge sources to restore data
    else:
        print(f"Rebuild failed: {message}")
```

**Mixed Success Handling**:
- When ingesting multiple sources, failures in one don't affect others
- Each source gets an individual success/failure status
- Partial ingestion is supported - successfully indexed sources remain available

**Error Indicators**:
```python
from offline_chat.rag.models import KnowledgeSource

# After ingestion, check source status
source = KnowledgeSource(
    source_type="web",
    identifier="https://example.com/docs",
    status="pending"
)

results = orchestrator.ingest_knowledge_sources([source])

for result in results:
    if result.success:
        print(f"✓ {result.source.identifier}: {result.chunks_processed} chunks")
    else:
        print(f"✗ {result.source.identifier}: {result.error_message}")
        print(f"  Status: {result.source.status}")
```

## Data Storage

Agent data is stored in `~/.offline-chat/` by default:

```
~/.offline-chat/
├── agents/                    # Agent configurations
│   └── {agent_name}/
│       ├── config.json        # Agent settings
│       └── Modelfile          # Ollama Modelfile
└── history/                   # Conversation histories
    └── {agent_name}.json
```

## Web Search

Agents can be enabled to search the web and fetch page content using Ollama's tool calling capabilities. For full functionality, use a tool-capable model like `llama3.1` or `qwen3`. If the model doesn't support tools, the agent will automatically fall back to regular chat without web search.

### Creating a Web-Enabled Agent

```python
from offline_chat import Agent, AgentManager

manager = AgentManager()

agent = Agent(
    name="research-assistant",
    display_name="Research Assistant",
    base_model="llama3.1:latest",  # Must be tool-capable
    system_prompt="You are a research assistant that helps find current information.",
    temperature=0.7,
    web_search_enabled=True  # Enable web search
)
manager.create_agent(agent)
```

### Using Search and Fetch Tools Directly

```python
from offline_chat import DuckDuckGoProvider, WebSearchTool, WebFetchTool

# Search the web
provider = DuckDuckGoProvider(timeout=10)
results = provider.search("Python 3.13 new features", max_results=5)
for result in results:
    print(f"{result.title}: {result.href}")

# Or use the tool interface
search_tool = WebSearchTool(provider)
output = search_tool.execute(query="latest ollama release", max_results=3)
print(output)

# Fetch and extract content from a page
fetch_tool = WebFetchTool(timeout=10)
content = fetch_tool.execute(url="https://example.com", max_length=5000)
print(content)
```

### Chat Indicators

When chatting with a web-enabled agent, you'll see indicators when tools are used:

```
You: What's the latest version of Python?

Searching...
Fetching page...

Research Assistant: Based on my search, the latest stable version of Python is...
```

## MCP Server Integration

Agents can connect to [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers to access external tools like filesystem access, database queries, API integrations, and more. MCP servers run as separate processes and communicate via stdio transport.

### Creating an Agent with MCP Servers

#### Via CLI

When creating an agent, you can select from pre-configured MCP servers:

```
Create New Agent
================

Agent name (kebab-case): file-assistant
Display name: File Assistant
Base model [llama3:latest]: llama3.1:latest
System prompt: You are a helpful assistant that can read and manage files.
Temperature (0.0-1.0) [0.7]: 
Response language [English]: 
Enable web search? (y/N): n

Add MCP servers? (y/N): y

----------------------------------------
MCP Server Configuration
----------------------------------------

Available MCP servers:
  1. fetch
     Fetch and extract content from URLs
     Command: uvx mcp-server-fetch
  2. filesystem
     Read/write files (configure path after selection)
     Command: npx -y @modelcontextprotocol/server-filesystem ~
  3. github
     GitHub API integration (requires token)
     Command: npx -y @modelcontextprotocol/server-github
  4. memory
     Persistent memory/knowledge graph
     Command: npx -y @modelcontextprotocol/server-memory

  5. Add custom MCP server
  0. Done adding servers

Select option: 1

--- Configure 'fetch' ---
Command: uvx mcp-server-fetch

Add this server? (Y/n): y

MCP server 'fetch' added.

Available MCP servers:
  1. fetch [added]
     ...
  2. filesystem
     ...

Select option: 0

Creating agent 'file-assistant'... Done!
```

#### Via Library

```python
from offline_chat import Agent, AgentManager, MCPServerConfig

manager = AgentManager()

# Configure MCP servers
mcp_servers = [
    MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/documents"],
    ),
    MCPServerConfig(
        name="fetch",
        command="uvx",
        args=["mcp-server-fetch"],
    ),
]

agent = Agent(
    name="file-assistant",
    display_name="File Assistant",
    base_model="llama3.1:latest",
    system_prompt="You are a helpful assistant that can read and manage files.",
    temperature=0.7,
    mcp_servers=mcp_servers,
)
manager.create_agent(agent)
```

### Using MCP Tools in Chat Sessions

When an agent has MCP servers configured, the chat session automatically connects to them and makes their tools available:

```python
import asyncio
from offline_chat import AgentManager, ChatSession

async def chat_with_mcp_agent():
    manager = AgentManager()
    session = ChatSession(manager)
    
    # Use async methods for MCP-enabled agents
    await session.start_async("file-assistant")
    
    try:
        # The agent can now use MCP tools
        for chunk in session.send_message("List the files in my documents folder"):
            print(chunk, end="", flush=True)
        print()
    finally:
        await session.end_async()

asyncio.run(chat_with_mcp_agent())
```

### MCPServerConfig Options

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `name` | str | Unique identifier for the server | Required |
| `command` | str | Command to launch the server (e.g., `npx`, `uvx`, `python`) | Required |
| `args` | list[str] | Arguments to pass to the command | `[]` |
| `env` | dict[str, str] | Environment variables for the server process | `{}` |
| `disabled` | bool | Whether to skip this server when connecting | `False` |
| `database_type` | str \| None | Database type for database MCP servers ("oracle", "postgresql", "mysql", "sqlite") | `None` |
| `oracle_connection_name` | str \| None | SQLcl connection name for Oracle databases | `None` |
| `oracle_tns_name` | str \| None | TNS alias for Oracle databases | `None` |
| `database_path` | str \| None | File path for SQLite databases | `None` |
| `database_host` | str \| None | Host for Oracle/PostgreSQL/MySQL databases | `None` |
| `database_port` | int \| None | Port for Oracle/PostgreSQL/MySQL databases | `None` |
| `database_name` | str \| None | Database/service name | `None` |
| `database_user` | str \| None | Database username | `None` |
| `database_password` | str \| None | Database password | `None` |

### Popular MCP Servers

Here are some commonly used MCP servers:

| Server | Command | Description |
|--------|---------|-------------|
| [mcp-server-fetch](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) | `uvx mcp-server-fetch` | Fetch and extract content from URLs |
| [server-filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) | `npx -y @modelcontextprotocol/server-filesystem /path` | Read/write files in specified directories |
| [server-github](https://github.com/modelcontextprotocol/servers/tree/main/src/github) | `npx -y @modelcontextprotocol/server-github` | GitHub API integration |
| [server-postgres](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres) | `npx -y @modelcontextprotocol/server-postgres` | PostgreSQL database queries |
| [server-memory](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | `npx -y @modelcontextprotocol/server-memory` | Persistent memory/knowledge graph |

### Managing MCP Presets

You can add custom MCP server presets that appear in the selection list when creating agents:

```python
from offline_chat import (
    MCPServerConfig,
    add_preset,
    remove_preset,
    load_presets,
    get_all_available_presets,
)

# Add a custom preset
custom_server = MCPServerConfig(
    name="my-custom-server",
    command="python",
    args=["-m", "my_mcp_server"],
    env={"API_KEY": "your-key"},
)
add_preset(custom_server)

# List all available presets (built-in + custom)
for config, description in get_all_available_presets():
    print(f"{config.name}: {description}")

# Load only user-defined presets
user_presets = load_presets()

# Remove a custom preset
remove_preset("my-custom-server")
```

Presets are stored in `~/.offline-chat/mcp_presets.json`.

### Error Handling

MCP server connections are resilient - if a server fails to connect, the agent continues with the remaining servers:

```python
from offline_chat import MCPServerConfig, MCPConfigError

# Validate configuration before creating agent
config = MCPServerConfig(
    name="my-server",
    command="uvx",
    args=["my-mcp-server"],
)

try:
    config.validate()
except MCPConfigError as e:
    print(f"Invalid configuration: {e}")
```

### Combining MCP with Web Search

MCP servers and built-in web search can be used together:

```python
agent = Agent(
    name="research-assistant",
    display_name="Research Assistant",
    base_model="llama3.1:latest",
    system_prompt="You are a research assistant with file and web access.",
    temperature=0.7,
    web_search_enabled=True,  # Built-in web search
    mcp_servers=[
        MCPServerConfig(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/research"],
        ),
    ],
)
```

## Database Access

Agents can connect to databases (Oracle, PostgreSQL, MySQL, SQLite) through MCP servers to query data, discover schemas, and analyze information during conversations. **Oracle Database is the primary supported database**, accessed through Oracle SQLcl's built-in MCP server.

> **Quick Start**: Want to try database access right away? See the [Sample Database Guide](SAMPLE_DATABASE_GUIDE.md) for a ready-to-use SQLite database with company sales data and step-by-step setup instructions.

### Supported Databases

| Database | MCP Server | Primary Support |
|----------|------------|-----------------|
| **Oracle** | Oracle SQLcl (built-in) | ✅ Primary |
| PostgreSQL | `@modelcontextprotocol/server-postgres` | ✅ Supported |
| MySQL | `mysql-mcp-server` | ✅ Supported |
| SQLite | `mcp-server-sqlite-npx` | ✅ Supported |

### Oracle Database Setup

Oracle Database is accessed through [Oracle SQLcl](https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/), which includes a built-in MCP server.

#### Prerequisites

1. **Install Oracle SQLcl**:
   - Download from [Oracle SQLcl Downloads](https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/download/)
   - Add `sql` command to your PATH

2. **Verify Installation**:
   ```bash
   sql -version
   ```

#### Creating an Agent with Oracle Database Access

##### Via CLI

When creating an agent, select Oracle as the database type:

```
Create New Agent
================

Agent name (kebab-case): data-analyst
Display name: Data Analyst
Base model [llama3:latest]: llama3.1:latest
System prompt: You are a data analyst who can query and analyze database information.
Temperature (0.0-1.0) [0.7]: 
Response language [English]: 
Enable web search? (y/N): n

Add database access? (y/N): y

----------------------------------------
Database Configuration
----------------------------------------

Database types:
  1. Oracle
  2. PostgreSQL
  3. MySQL
  4. SQLite
  0. Done adding databases

Select database type: 1

--- Oracle Database Configuration ---

Existing SQLcl connections:
  1. PROD_DB
  2. DEV_DB
  3. Create new connection

Select connection (1-3): 1

Testing connection... Done!
✓ Database 'prod_db' configured successfully

Add another database? (y/N): n

Creating agent 'data-analyst'... Done!
```

**Connection Options**:

1. **Use Existing SQLcl Connection** (Recommended):
   - If you have SQLcl connections configured, they'll be listed
   - Select one to reuse existing credentials

2. **Use TNS Alias**:
   - Requires TNS names configured in `tnsnames.ora`
   - Prompts for username and password

3. **Full Connection Details**:
   - Host, port, service name, username, password
   - Creates connection string: `user/pass@host:port/service`

##### Via Library

```python
from offline_chat import Agent, AgentManager, MCPServerConfig
from offline_chat.database_config import create_database_mcp_config

manager = AgentManager()

# Option 1: Use existing SQLcl connection
oracle_config = create_database_mcp_config(
    "oracle",
    "prod_db",
    connection_name="PROD_ANALYTICS"  # Existing SQLcl connection
)

# Option 2: Use TNS alias
oracle_config = create_database_mcp_config(
    "oracle",
    "prod_db",
    tns_name="PROD_TNS",
    username="analyst",
    password="secure_password"
)

# Option 3: Full connection details
oracle_config = create_database_mcp_config(
    "oracle",
    "prod_db",
    host="db.example.com",
    port=1521,
    service_name="PRODDB",
    username="analyst",
    password="secure_password"
)

agent = Agent(
    name="data-analyst",
    display_name="Data Analyst",
    base_model="llama3.1:latest",
    system_prompt="You are a data analyst who can query databases.",
    temperature=0.7,
    mcp_servers=[oracle_config]
)
manager.create_agent(agent)
```

#### Oracle-Specific Features

**Audit Logging**:
- All queries are logged in the `DBTOOLS$MCP_LOG` table
- Tracks query text, execution time, and session information
- Useful for compliance and debugging

**Session Tracking**:
- Queries appear in `V$SESSION` with identifiable session info
- Monitor active database sessions from agents

**Available Tools**:
- `run-sql`: Execute SQL queries (read-only by default)
- `list-connections`: List available SQLcl connections
- Additional Oracle-specific tools for Data Pump, Data Guard, AWR, etc.

### PostgreSQL Database Setup

#### Prerequisites

Install the PostgreSQL MCP server:

```bash
# Using npx (recommended - no installation needed)
npx -y @modelcontextprotocol/server-postgres --help

# Or install globally with npm
npm install -g @modelcontextprotocol/server-postgres
```

#### Creating an Agent with PostgreSQL Access

##### Via CLI

```
Database types:
  1. Oracle
  2. PostgreSQL
  3. MySQL
  4. SQLite
  0. Done adding databases

Select database type: 2

--- PostgreSQL Database Configuration ---

Host [localhost]: db.example.com
Port [5432]: 5432
Database name: analytics
Username: analyst
Password: ********

Testing connection... Done!
✓ Database 'analytics_db' configured successfully
```

##### Via Library

```python
from offline_chat.database_config import create_database_mcp_config

postgres_config = create_database_mcp_config(
    "postgresql",
    "analytics_db",
    host="db.example.com",
    port=5432,
    database="analytics",
    username="analyst",
    password="secure_password"
)

agent = Agent(
    name="data-analyst",
    display_name="Data Analyst",
    base_model="llama3.1:latest",
    system_prompt="You are a data analyst.",
    temperature=0.7,
    mcp_servers=[postgres_config]
)
```

### MySQL Database Setup

#### Prerequisites

Install the MySQL MCP server:

```bash
# Using uvx (recommended)
uvx mysql-mcp-server --help

# Or install globally with npm
npm install -g @modelcontextprotocol/server-mysql
```

#### Creating an Agent with MySQL Access

##### Via CLI

```
Select database type: 3

--- MySQL Database Configuration ---

Host [localhost]: db.example.com
Port [3306]: 3306
Database name: sales
Username: analyst
Password: ********

Testing connection... Done!
✓ Database 'sales_db' configured successfully
```

##### Via Library

```python
from offline_chat.database_config import create_database_mcp_config

mysql_config = create_database_mcp_config(
    "mysql",
    "sales_db",
    host="db.example.com",
    port=3306,
    database="sales",
    username="analyst",
    password="secure_password"
)
```

### SQLite Database Setup

#### Prerequisites

Install the SQLite MCP server:

```bash
# Using npx (recommended)
npx -y mcp-server-sqlite-npx --help
```

#### Creating an Agent with SQLite Access

##### Via CLI

```
Select database type: 4

--- SQLite Database Configuration ---

Database file path: /path/to/database.db

Testing connection... Done!
✓ Database 'local_db' configured successfully
```

##### Via Library

```python
from offline_chat.database_config import create_database_mcp_config

sqlite_config = create_database_mcp_config(
    "sqlite",
    "local_db",
    path="/path/to/database.db"
)
```

### Using Database Tools in Chat

Once an agent has database access configured, it can use database tools during conversations:

```python
import asyncio
from offline_chat import AgentManager, ChatSession

async def chat_with_database_agent():
    manager = AgentManager()
    session = ChatSession(manager)
    
    # Use async methods for database-enabled agents
    await session.start_async("data-analyst")
    
    try:
        # Agent can now query the database
        print("You: What are the top 5 customers by revenue?")
        print("Agent: ", end="")
        for chunk in session.send_message("What are the top 5 customers by revenue?"):
            print(chunk, end="", flush=True)
        print("\n")
        
        # Agent can discover schema
        print("You: What tables are available?")
        print("Agent: ", end="")
        for chunk in session.send_message("What tables are available?"):
            print(chunk, end="", flush=True)
        print("\n")
        
    finally:
        await session.end_async()

asyncio.run(chat_with_database_agent())
```

### Available Database Tools

Database MCP servers provide these standard tools:

| Tool | Description | Oracle Tool Name |
|------|-------------|------------------|
| Query execution | Execute read-only SQL queries | `run-sql` |
| List tables | List all tables in the database | `list-connections` |
| Describe table | Get schema info for a specific table | `describe_table` |
| Get schema | Get complete database schema | `get_schema` |

**Note**: Oracle SQLcl uses slightly different tool names. The agent automatically adapts to the available tools.

### Multiple Database Access

Agents can connect to multiple databases simultaneously:

```python
from offline_chat.database_config import create_database_mcp_config

# Configure multiple databases
oracle_config = create_database_mcp_config(
    "oracle", "prod_db", connection_name="PROD"
)

postgres_config = create_database_mcp_config(
    "postgresql", "analytics_db",
    host="localhost", port=5432, database="analytics",
    username="analyst", password="password"
)

sqlite_config = create_database_mcp_config(
    "sqlite", "local_cache", path="/tmp/cache.db"
)

agent = Agent(
    name="multi-db-analyst",
    display_name="Multi-Database Analyst",
    base_model="llama3.1:latest",
    system_prompt="You are a data analyst with access to multiple databases.",
    temperature=0.7,
    mcp_servers=[oracle_config, postgres_config, sqlite_config]
)
```

When multiple databases are configured, tools are automatically namespaced by database name to prevent conflicts:
- `prod_db_run_sql`
- `analytics_db_query_database`
- `local_cache_query_database`

**Note**: Single database configurations use original tool names without namespacing. Regular (non-database) MCP servers always use original tool names.

### Access Control and Security

Offline Chat provides fine-grained access control for database connections through **access levels**. Each agent-to-database connection assignment can specify what operations are allowed and which tables can be accessed.

#### Access Levels

| Access Level | Description | Allowed Operations | Table Restrictions |
|--------------|-------------|-------------------|-------------------|
| `READ_ONLY` | Read-only access to all tables | SELECT only | All tables |
| `READ_WRITE` | Read and write access to all tables | SELECT, INSERT, UPDATE, DELETE | All tables |
| `TABLE_SPECIFIC_READ` | Read-only access to specific tables | SELECT only | Specified tables only |
| `TABLE_SPECIFIC_READ_WRITE` | Read and write access to specific tables | SELECT, INSERT, UPDATE, DELETE | Specified tables only |

**Note**: DDL operations (CREATE, DROP, ALTER, TRUNCATE) are always blocked for safety, regardless of access level.

#### Configuring Access Levels

##### Via Library

```python
from offline_chat import Agent, AgentManager
from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.mcp_config import MCPServerConfig

manager = AgentManager()

# Example 1: Read-only access to all tables
agent = Agent(
    name="data-viewer",
    display_name="Data Viewer",
    base_model="llama3.1:latest",
    system_prompt="You can view database data but not modify it.",
    temperature=0.7,
    connection_assignments=[
        AgentConnectionAssignment(
            connection_name="prod_db",
            access_level=AccessLevel.READ_ONLY,
            allowed_tables=None  # All tables accessible
        )
    ],
    mcp_servers=[
        MCPServerConfig(
            name="prod_db",
            command="sql",
            args=["-mcp", "user/pass@host:port/service"],
            database_type="oracle"
        )
    ]
)
manager.create_agent(agent)

# Example 2: Read-write access to specific tables only
agent = Agent(
    name="sales-updater",
    display_name="Sales Data Updater",
    base_model="llama3.1:latest",
    system_prompt="You can read and update sales data.",
    temperature=0.7,
    connection_assignments=[
        AgentConnectionAssignment(
            connection_name="sales_db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["sales", "customers", "orders"]
        )
    ],
    mcp_servers=[
        MCPServerConfig(
            name="sales_db",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@host:5432/sales"],
            database_type="postgresql"
        )
    ]
)
manager.create_agent(agent)

# Example 3: Multiple connections with different access levels
agent = Agent(
    name="data-analyst",
    display_name="Data Analyst",
    base_model="llama3.1:latest",
    system_prompt="You can analyze production data (read-only) and update reports.",
    temperature=0.7,
    connection_assignments=[
        AgentConnectionAssignment(
            connection_name="prod_db",
            access_level=AccessLevel.READ_ONLY,
            allowed_tables=None
        ),
        AgentConnectionAssignment(
            connection_name="reports_db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["reports", "dashboards"]
        )
    ],
    mcp_servers=[
        MCPServerConfig(name="prod_db", command="sql", args=["-mcp", "..."], database_type="oracle"),
        MCPServerConfig(name="reports_db", command="npx", args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@host:5432/reports"], database_type="postgresql")
    ]
)
manager.create_agent(agent)
```

##### Via CLI

When creating an agent with database access through the CLI, you'll be prompted to select an access level:

```
--- Configure Database Connection ---

Database name: prod_db
Database type: Oracle

Select access level:
  1. Read-only (SELECT queries only, all tables)
  2. Read-write (SELECT, INSERT, UPDATE, DELETE on all tables)
  3. Table-specific read (SELECT queries only, specific tables)
  4. Table-specific read-write (SELECT, INSERT, UPDATE, DELETE on specific tables)

Select access level (1-4): 3

Enter allowed tables (comma-separated): customers,orders,products

✓ Access level configured: table-specific-read
  Allowed tables: customers, orders, products
```

#### Query Validation

All database queries are automatically validated against the assigned access level before execution:

```python
import asyncio
from offline_chat import AgentManager, ChatSession

async def demo_access_control():
    manager = AgentManager()
    session = ChatSession(manager)
    
    # Agent has READ_ONLY access
    await session.start_async("data-viewer")
    
    # This query will succeed (SELECT is allowed)
    print("You: Show me the top 10 customers")
    for chunk in session.send_message("Show me the top 10 customers"):
        print(chunk, end="", flush=True)
    print("\n")
    
    # This query will be blocked (INSERT not allowed with READ_ONLY)
    print("You: Add a new customer named 'Test Corp'")
    for chunk in session.send_message("Add a new customer named 'Test Corp'"):
        print(chunk, end="", flush=True)
    # Output: "Access denied: INSERT operation not permitted with read-only access"
    print("\n")
    
    await session.end_async()

asyncio.run(demo_access_control())
```

#### Access Violation Examples

**READ_ONLY Access**:
```python
# ✓ Allowed
"SELECT * FROM customers"
"SELECT COUNT(*) FROM orders WHERE status = 'completed'"

# ✗ Blocked
"INSERT INTO customers (name) VALUES ('New Customer')"
"UPDATE orders SET status = 'cancelled' WHERE id = 123"
"DELETE FROM customers WHERE id = 456"
```

**TABLE_SPECIFIC_READ Access** (allowed tables: `customers`, `orders`):
```python
# ✓ Allowed
"SELECT * FROM customers"
"SELECT * FROM orders WHERE customer_id = 123"

# ✗ Blocked - wrong table
"SELECT * FROM admin_secrets"
"SELECT * FROM employees"

# ✗ Blocked - write operation
"INSERT INTO customers (name) VALUES ('Test')"
```

**TABLE_SPECIFIC_READ_WRITE Access** (allowed tables: `reports`, `dashboards`):
```python
# ✓ Allowed
"SELECT * FROM reports"
"INSERT INTO reports (title, data) VALUES ('Q1 Report', '{}')"
"UPDATE dashboards SET last_updated = NOW() WHERE id = 1"
"DELETE FROM reports WHERE id = 999"

# ✗ Blocked - wrong table
"SELECT * FROM customers"
"INSERT INTO orders (customer_id) VALUES (123)"

# ✗ Blocked - DDL operation (always blocked)
"DROP TABLE reports"
"ALTER TABLE dashboards ADD COLUMN new_col VARCHAR(100)"
```

#### Error Messages

When a query violates access restrictions, the agent receives a clear error message:

```
Access denied: INSERT operation not permitted with read-only access
Access denied: Table 'admin_secrets' not in allowed list: [customers, orders]
Access denied: DDL operations (DROP, ALTER, CREATE) are not permitted
```

The agent can see these errors and understand the restrictions, allowing it to adjust its approach or inform the user about the limitations.

#### Security Best Practices

1. **Principle of Least Privilege**:
   - Start with `READ_ONLY` access by default
   - Only grant `READ_WRITE` when necessary
   - Use `TABLE_SPECIFIC_*` levels to limit scope

2. **Separate Agents by Role**:
   ```python
   # Viewer agent - read-only
   viewer = Agent(
       name="data-viewer",
       connection_assignments=[
           AgentConnectionAssignment(
               connection_name="prod_db",
               access_level=AccessLevel.READ_ONLY
           )
       ]
   )
   
   # Editor agent - write access to specific tables
   editor = Agent(
       name="data-editor",
       connection_assignments=[
           AgentConnectionAssignment(
               connection_name="prod_db",
               access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
               allowed_tables=["reports", "logs"]
           )
       ]
   )
   ```

3. **Audit and Monitor**:
   - Review conversation history to see what queries were executed
   - For Oracle databases, check `DBTOOLS$MCP_LOG` table for query audit trail
   - Monitor agent behavior and adjust access levels as needed

4. **Database-Level Permissions**:
   - Access levels are enforced at the application level
   - Also configure database user permissions as a second layer of defense
   - Use database roles and grants to limit what the database user can do

5. **Testing Access Levels**:
   ```python
   from offline_chat.database.access_validator import AccessLevelValidator
   from offline_chat.database.access_level import AccessLevel
   
   # Test if a query would be allowed
   result = AccessLevelValidator.validate_query(
       "INSERT INTO customers (name) VALUES ('Test')",
       AccessLevel.READ_ONLY,
       []
   )
   
   if result.is_err():
       print(f"Query would be blocked: {result.unwrap_err()}")
   ```

### Additional Security Features

**Credential Storage**:
- Database credentials are stored in agent configuration files
- Passwords are masked in CLI displays and logs
- Configuration files should have appropriate file permissions (600)

**Connection Management**:
- Connections are established when chat sessions start
- Connections are reused within a session for efficiency
- All connections are properly closed when sessions end
- Failed connections are logged but don't crash the session

**Query Logging** (Oracle):
- All queries to Oracle databases are logged in `DBTOOLS$MCP_LOG` table
- Includes query text, execution time, and session information
- Useful for compliance and security auditing

### Viewing Database Configuration

List agents with database access:

```bash
make agents
```

Output shows database status:

```
Your Agents
===========

  data-analyst         Data Analyst           (llama3.1:latest)
    Databases: oracle(prod_db), postgresql(analytics_db)
  
  code-reviewer        Code Reviewer          (llama3:latest)
    No database access

Total: 2 agents
```

View detailed configuration:

```bash
make agent-info AGENT=data-analyst
```

Output shows masked credentials:

```
========================================
Agent: Data Analyst
========================================

Name: data-analyst
Display Name: Data Analyst
Base Model: llama3.1:latest
Temperature: 0.7
Language: English
Web Search: Disabled
Created: 2025-01-20 10:30

Purpose/Persona:
  You are a data analyst who can query and analyze database information.

Database Connections:

  Connection: prod_db
  Type: oracle
  Access Level: read_only
  Host: db.example.com
  Port: 1521
  Database: PRODDB
  Username: analyst
  Password: ****

  Connection: analytics_db
  Type: postgresql
  Access Level: read_write
  Allowed Tables: sales, customers, products
  Host: analytics.example.com
  Port: 5432
  Database: analytics
  Username: analyst
  Password: ****

========================================
```

### Database Access Examples

#### Example 1: Sales Data Analysis Agent

Create an agent that analyzes sales data from an Oracle database:

```python
import asyncio
from offline_chat import Agent, AgentManager, ChatSession
from offline_chat.database_config import create_database_mcp_config

async def create_sales_analyst():
    manager = AgentManager()
    
    # Configure Oracle database connection
    oracle_config = create_database_mcp_config(
        "oracle",
        "sales_db",
        connection_name="SALES_PROD"  # Existing SQLcl connection
    )
    
    # Create agent with database access
    agent = Agent(
        name="sales-analyst",
        display_name="Sales Data Analyst",
        base_model="llama3.1:latest",
        system_prompt="""You are a sales data analyst with access to the company's 
        sales database. Help analyze sales trends, customer behavior, and revenue 
        metrics. Always provide data-driven insights and visualize trends when possible.""",
        temperature=0.3,  # Lower temperature for factual analysis
        mcp_servers=[oracle_config]
    )
    
    manager.create_agent(agent)
    
    # Start a chat session
    session = ChatSession(manager)
    await session.start_async("sales-analyst")
    
    try:
        # Ask for sales analysis
        print("You: What were our top 5 products by revenue last quarter?")
        print("Agent: ", end="")
        for chunk in session.send_message(
            "What were our top 5 products by revenue last quarter?"
        ):
            print(chunk, end="", flush=True)
        print("\n")
        
        # Follow-up question
        print("You: Show me the customer distribution by region")
        print("Agent: ", end="")
        for chunk in session.send_message(
            "Show me the customer distribution by region"
        ):
            print(chunk, end="", flush=True)
        print("\n")
        
    finally:
        await session.end_async()

asyncio.run(create_sales_analyst())
```

#### Example 2: Multi-Database Data Integration Agent

Create an agent that can query multiple databases for comprehensive analysis:

```python
import asyncio
from offline_chat import Agent, AgentManager, ChatSession
from offline_chat.database_config import create_database_mcp_config

async def create_integration_analyst():
    manager = AgentManager()
    
    # Configure multiple databases
    oracle_prod = create_database_mcp_config(
        "oracle", "production_db",
        connection_name="PROD_ANALYTICS"
    )
    
    postgres_warehouse = create_database_mcp_config(
        "postgresql", "warehouse_db",
        host="warehouse.company.com",
        port=5432,
        database="data_warehouse",
        username="analyst",
        password="secure_password"
    )
    
    sqlite_cache = create_database_mcp_config(
        "sqlite", "local_cache",
        path="/tmp/analysis_cache.db"
    )
    
    # Create agent with access to all databases
    agent = Agent(
        name="integration-analyst",
        display_name="Data Integration Analyst",
        base_model="llama3.1:latest",
        system_prompt="""You are a data integration analyst with access to multiple 
        databases: production Oracle database, PostgreSQL data warehouse, and local 
        SQLite cache. Help users query and correlate data across these systems.""",
        temperature=0.3,
        mcp_servers=[oracle_prod, postgres_warehouse, sqlite_cache]
    )
    
    manager.create_agent(agent)
    
    # Use the agent
    session = ChatSession(manager)
    await session.start_async("integration-analyst")
    
    try:
        # Agent can now query all three databases
        print("You: Compare sales data from production with warehouse aggregates")
        print("Agent: ", end="")
        for chunk in session.send_message(
            "Compare sales data from production with warehouse aggregates"
        ):
            print(chunk, end="", flush=True)
        print("\n")
        
    finally:
        await session.end_async()

asyncio.run(create_integration_analyst())
```

#### Example 3: Schema Explorer Agent

Create an agent that helps explore and understand database schemas:

```python
import asyncio
from offline_chat import Agent, AgentManager, ChatSession
from offline_chat.database_config import create_database_mcp_config

async def create_schema_explorer():
    manager = AgentManager()
    
    # Configure database
    db_config = create_database_mcp_config(
        "postgresql", "app_db",
        host="localhost",
        port=5432,
        database="application",
        username="developer",
        password="dev_password"
    )
    
    # Create schema exploration agent
    agent = Agent(
        name="schema-explorer",
        display_name="Database Schema Explorer",
        base_model="llama3.1:latest",
        system_prompt="""You are a database schema expert. Help users understand 
        database structure, relationships between tables, and suggest optimal queries. 
        Always start by exploring the schema before answering questions.""",
        temperature=0.5,
        mcp_servers=[db_config]
    )
    
    manager.create_agent(agent)
    
    # Interactive session
    session = ChatSession(manager)
    await session.start_async("schema-explorer")
    
    try:
        # Explore schema
        questions = [
            "What tables are available in this database?",
            "Describe the users table structure",
            "What are the relationships between users and orders tables?",
            "Show me a query to get all orders for a specific user"
        ]
        
        for question in questions:
            print(f"\nYou: {question}")
            print("Agent: ", end="")
            for chunk in session.send_message(question):
                print(chunk, end="", flush=True)
            print()
        
    finally:
        await session.end_async()

asyncio.run(create_schema_explorer())
```

#### Example 4: CLI-Based Database Agent Creation

Create a database-enabled agent using the CLI:

```bash
# Start the application
make run

# Select "Create new agent"
# Follow the prompts:

Agent name: data-analyst
Display name: Data Analyst
Base model: llama3.1:latest
System prompt: You are a data analyst with database access
Temperature: 0.3
Enable web search: n

Add database access? y

Database types:
  1. Oracle
  2. PostgreSQL
  3. MySQL
  4. SQLite

Select database type: 1

Existing SQLcl connections:
  1. PROD_DB
  2. DEV_DB
  3. Create new connection

Select connection: 1

Testing connection... Done!
✓ Database 'prod_db' configured successfully

Add another database? n

Creating agent 'data-analyst'... Done!
```

#### Example 5: Validating Database Configuration

Test database connections before creating agents:

```python
from offline_chat.database_config import create_database_mcp_config
from offline_chat.connection_validator import validate_database_connection

# Create configuration
config = create_database_mcp_config(
    "postgresql",
    "test_db",
    host="localhost",
    port=5432,
    database="testdb",
    username="testuser",
    password="testpass"
)

# Validate connection before using
success, error_message = validate_database_connection(config)

if success:
    print("✓ Connection successful!")
    # Proceed with agent creation
else:
    print(f"✗ Connection failed: {error_message}")
    # Fix configuration and retry
```

#### Example 6: Query Safety Validation

Ensure queries are read-only before execution:

```python
from offline_chat.query_validator import is_read_only_query

# Safe queries
safe_queries = [
    "SELECT * FROM customers",
    "SELECT COUNT(*) FROM orders WHERE status = 'completed'",
    "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
]

for query in safe_queries:
    assert is_read_only_query(query), f"Query should be safe: {query}"
    print(f"✓ Safe: {query}")

# Unsafe queries (will be rejected)
unsafe_queries = [
    "INSERT INTO users (name) VALUES ('test')",
    "UPDATE orders SET status = 'cancelled'",
    "DELETE FROM customers WHERE id = 1",
    "DROP TABLE users"
]

for query in unsafe_queries:
    assert not is_read_only_query(query), f"Query should be rejected: {query}"
    print(f"✗ Rejected: {query}")
```

## Troubleshooting

### Tool Calling Issues

**Agent outputs SQL code blocks instead of executing queries**:

This happens when the agent's system prompt doesn't emphasize tool usage, or when using models with weak tool calling support.

**Solution**:
1. Update the agent's system prompt to emphasize direct tool usage:
   ```python
   system_prompt = """You are a database analyst. Your job is to query databases and provide insights.
   
   IMPORTANT: You have direct access to database tools. When users ask questions:
   1. Use the tools to query the database
   2. Analyze the results
   3. Provide clear, concise answers
   
   DO NOT explain what queries you would run. Just run them and report the findings.
   DO NOT write SQL code in your responses. The tools handle that automatically.
   
   Focus on delivering insights, not explaining your process."""
   ```

2. Use a model with strong tool calling support:
   - **Best**: `qwen2.5:latest` - Excellent tool calling, fast
   - **Good**: `llama3.2:latest` - Reliable tool calling
   - **Fast**: `mistral:latest` - Quick responses, decent tools
   - **Avoid**: `llama3.1:latest` - Limited tool support, often outputs JSON/SQL as text

3. Update the agent's base model:
   ```bash
   # Via CLI
   make run
   # Select "Update agent" → Choose agent → "Update base model"
   
   # Via library
   from offline_chat import AgentManager
   manager = AgentManager()
   manager.update_agent("agent-name", {"base_model": "qwen2.5:latest"})
   ```

**Agent gives incomplete responses or stops mid-sentence**:

The agent announces it will use a tool (e.g., "Let me run a query...") but then stops without actually calling the tool or providing results.

**Common causes**:
1. Model has weak tool calling support
2. TypeError when processing tool calls (if `tool_calls` is `None` instead of `[]`)
3. Missing debug logging causing silent failures

**Solution**:
1. **Use a model with strong tool calling support** (most important):
   - **Best**: `qwen2.5:latest` - Excellent tool calling, fast, reliable
   - **Good**: `llama3.2:latest` - Reliable tool calling
   - **Avoid**: `mistral:latest` - Fast but weak tool calling for database work
   - **Avoid**: `llama3.1:latest` - Very limited tool support

2. **Update the agent's base model**:
   ```bash
   # Via CLI
   make run
   # Select "Update agent" → Choose agent → "Update base model" → Enter "qwen2.5:latest"
   
   # Via library
   from offline_chat import AgentManager
   manager = AgentManager()
   manager.update_agent("agent-name", {"base_model": "qwen2.5:latest"})
   ```

3. **Ensure the model is available**:
   ```bash
   # Pull the model if not already available
   ollama pull qwen2.5:latest
   ```

4. **Check for errors in logs**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

**Note**: This issue was resolved in recent versions by fixing TypeError handling when `tool_calls` is `None` and adding proper debug logging. If you're still experiencing issues after updating to a better model, ensure you're running the latest version of the code.

**Agent stops mid-task or hits iteration limit**:

The agent loop has a 20-iteration safety limit to prevent infinite loops. For complex queries requiring many tool calls, the agent will automatically summarize findings and prompt for follow-up questions.

**What happens**:
- Agent makes up to 20 tool calls per message
- If limit is reached, agent summarizes findings so far
- A note appears: "[Note: This was a complex query. Feel free to ask follow-up questions for more details.]"
- Conversation history preserves all context for continuation

**Solution**:
- Break complex questions into smaller parts
- Use follow-up questions to continue analysis
- Type `clear` to reset conversation if agent seems confused
- Consider if the query is too broad and needs refinement

**Example**:
```
You: Analyze top customers, their products, and buying patterns over 6 months

Agent: Based on my analysis, I found:
- Top 5 customers by revenue: Customer A ($50k), Customer B ($45k)...
- Most popular products: Product X (1000 units), Product Y (800 units)...

I was analyzing buying patterns but need more queries to complete that analysis.

[Note: This was a complex query. Feel free to ask follow-up questions for more details.]

You: Show me the buying patterns for Customer A

Agent: Customer A's buying patterns show...
```

### Connection Issues

**"Cannot connect to database"**:
- Verify database server is running and accessible
- Check connection parameters (host, port, credentials)
- For Oracle: Ensure SQLcl is installed and in PATH
  ```bash
  # Test SQLcl installation
  sql -version
  
  # Test SQLcl connection manually
  sql username/password@host:port/service
  ```
- Test connection manually before configuring agent
- Check firewall rules and network connectivity

**"Connection test failed"**:
- Database credentials may be incorrect
- Network connectivity issues
- Firewall blocking connection
- For Oracle: TNS configuration may be incorrect
  ```bash
  # Check TNS configuration
  cat $ORACLE_HOME/network/admin/tnsnames.ora
  
  # Test TNS alias
  tnsping YOUR_TNS_ALIAS
  ```
- For PostgreSQL/MySQL: Verify host allows remote connections

**"MCP server failed to start"**:
- Check MCP server installation
  ```bash
  # For PostgreSQL
  npx -y @modelcontextprotocol/server-postgres --help
  
  # For SQLite
  npx -y mcp-server-sqlite-npx --help
  ```
- Verify command and arguments in configuration
- Check server logs for detailed error messages
- Ensure required dependencies are installed

#### Query Issues

**"No query tool found"**:
- MCP server may not have started correctly
- Check MCP server installation
- Verify configuration in agent's `mcp_servers` list
- For Oracle: Ensure `run-sql` tool is available
- For others: Ensure `query_database` tool is available

**Query Errors**:
- **Syntax errors**: Check SQL syntax for your database type
  ```python
  # Oracle uses different syntax than PostgreSQL
  # Oracle: SELECT * FROM DUAL
  # PostgreSQL: SELECT 1
  ```
- **Table or column doesn't exist**: Use schema discovery tools first
  ```python
  # Ask agent to list tables first
  "What tables are available?"
  
  # Then describe specific table
  "Describe the customers table"
  ```
- **Insufficient database permissions**: Verify user has SELECT privileges
  ```sql
  -- Oracle: Check user privileges
  SELECT * FROM USER_TAB_PRIVS;
  
  -- PostgreSQL: Check table permissions
  SELECT * FROM information_schema.table_privileges 
  WHERE grantee = 'your_username';
  ```
- **Query timeout** (default: 30 seconds): Optimize query or increase timeout

**"Write operation rejected"**:
- All database access is read-only by default
- INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, REPLACE are blocked
- This is a security feature to prevent accidental data modification
- If you need write access, you must modify the query validator

#### Oracle-Specific Issues

**"SQLcl not found"**:
```bash
# Install SQLcl
# Download from: https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/download/

# Add to PATH (macOS/Linux)
export PATH=$PATH:/path/to/sqlcl/bin

# Verify installation
sql -version
```

**"TNS: could not resolve the connect identifier"**:
- TNS alias not found in `tnsnames.ora`
- Check `ORACLE_HOME` environment variable
- Verify `tnsnames.ora` file location and contents
```bash
# Check ORACLE_HOME
echo $ORACLE_HOME

# View tnsnames.ora
cat $ORACLE_HOME/network/admin/tnsnames.ora
```

**"ORA-01017: invalid username/password"**:
- Credentials are incorrect
- Account may be locked
- Password may have expired
```sql
-- Check account status (as DBA)
SELECT username, account_status FROM dba_users WHERE username = 'YOUR_USER';
```

**"Cannot access DBTOOLS$MCP_LOG table"**:
- This is normal - the table is created automatically by SQLcl MCP server
- Only visible when using Oracle SQLcl MCP server
- Used for audit logging of all queries

#### Configuration Issues

**"Invalid database type"**:
- Only "oracle", "postgresql", "mysql", "sqlite" are supported
- Check spelling and case (must be lowercase)

**"Missing required parameters"**:
- Each database type requires specific parameters:
  - Oracle: `connection_name` OR (`host`, `port`, `service_name`, `username`, `password`) OR (`tns_name`, `username`, `password`)
  - PostgreSQL/MySQL: `host`, `port`, `database`, `username`, `password`
  - SQLite: `path`

**"SQLite database file not found"**:
- Verify file path is correct and absolute
- Check file permissions (must be readable)
- Create database file if it doesn't exist:
  ```bash
  sqlite3 /path/to/database.db "CREATE TABLE test (id INTEGER);"
  ```

#### Performance Issues

**Slow query execution**:
- Add indexes to frequently queried columns
- Limit result sets with `LIMIT` or `ROWNUM`
- Use `EXPLAIN` to analyze query performance
- Consider creating views for complex queries

**Connection timeouts**:
- Check network latency to database server
- Verify database server isn't overloaded
- Consider using connection pooling (not currently supported)

#### Debugging Tips

**Enable verbose logging**:
```python
import logging

# Enable debug logging for database operations
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('offline_chat.session')
logger.setLevel(logging.DEBUG)
```

**Test MCP server manually**:
```bash
# Test Oracle SQLcl MCP server
sql -mcp username/password@host:port/service

# Test PostgreSQL MCP server
npx -y @modelcontextprotocol/server-postgres postgresql://user:pass@localhost:5432/dbname
```

**Verify agent configuration**:
```bash
# View agent configuration including database settings
make agent-info AGENT=your-agent-name

# Check for masked passwords and connection details
```

**Check MCP server logs**:
- MCP servers log to stderr
- Check terminal output when starting chat session
- Look for connection errors or tool registration issues

### Database Access Best Practices

#### Security

1. **Use Read-Only Accounts**:
   ```sql
   -- Oracle: Create read-only user
   CREATE USER analyst IDENTIFIED BY secure_password;
   GRANT CONNECT TO analyst;
   GRANT SELECT ON schema.table_name TO analyst;
   
   -- PostgreSQL: Create read-only user
   CREATE USER analyst WITH PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE mydb TO analyst;
   GRANT USAGE ON SCHEMA public TO analyst;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst;
   ```

2. **Store Credentials Securely**:
   - Use environment variables for passwords
   - Consider using Oracle Wallet for Oracle connections
   - Restrict file permissions on agent configuration files
   ```bash
   chmod 600 ~/.offline-chat/agents/*/config.json
   ```

3. **Use Existing SQLcl Connections** (Oracle):
   - Leverage SQLcl's secure credential storage
   - Avoid storing passwords in agent configurations
   - Reuse tested, working connections

4. **Limit Database Access**:
   - Grant access only to necessary tables/schemas
   - Use database views to restrict data visibility
   - Implement row-level security where appropriate

#### Performance

1. **Optimize Queries**:
   - Use specific column names instead of `SELECT *`
   - Add `LIMIT` clauses to prevent large result sets
   - Create indexes on frequently queried columns
   ```sql
   -- Good: Specific columns with limit
   SELECT customer_id, name, email FROM customers LIMIT 100;
   
   -- Avoid: Unbounded SELECT *
   SELECT * FROM large_table;
   ```

2. **Use Schema Discovery Wisely**:
   - Cache schema information in conversation context
   - Ask agent to list tables once, then reference them
   - Use `describe_table` before querying unfamiliar tables

3. **Connection Reuse**:
   - Connections are automatically reused within a session
   - Avoid ending and restarting sessions unnecessarily
   - Multiple queries in one session are more efficient

4. **Result Set Management**:
   - Results are automatically truncated at 100 rows
   - Use aggregation queries for large datasets
   - Consider creating summary tables or views

#### Agent Design

1. **Clear System Prompts**:
   ```python
   # Good: Specific instructions
   system_prompt = """You are a sales analyst with access to the sales database.
   
   Guidelines:
   - Always start by exploring available tables
   - Use aggregation for large datasets
   - Provide insights, not just raw data
   - Format results as tables when appropriate
   - Explain your queries before executing them
   """
   
   # Avoid: Vague instructions
   system_prompt = "You can query databases."
   ```

2. **Appropriate Temperature**:
   - Use lower temperature (0.2-0.4) for factual data analysis
   - Use higher temperature (0.6-0.8) for exploratory analysis
   - Adjust based on use case

3. **Combine with Other Tools**:
   ```python
   # Agent with database + web search
   agent = Agent(
       name="research-analyst",
       display_name="Research Analyst",
       base_model="llama3.1:latest",
       system_prompt="You can query internal databases and search the web.",
       temperature=0.5,
       web_search_enabled=True,  # For external context
       mcp_servers=[db_config]    # For internal data
   )
   ```

#### Workflow Patterns

1. **Schema-First Approach**:
   ```python
   # Good workflow
   questions = [
       "What tables are available?",
       "Describe the customers table",
       "Show me the top 10 customers by revenue"
   ]
   ```

2. **Iterative Analysis**:
   ```python
   # Start broad, then drill down
   "What's the total revenue this quarter?"
   "Which product category contributed most?"
   "Show me the top products in that category"
   "What regions are buying these products?"
   ```

3. **Error Recovery**:
   ```python
   # If query fails, ask agent to fix it
   "The query failed with 'column not found'. Can you check the schema and try again?"
   ```

#### Monitoring and Auditing

1. **Oracle Audit Logging**:
   ```sql
   -- View query history (Oracle)
   SELECT * FROM DBTOOLS$MCP_LOG 
   ORDER BY execution_time DESC;
   ```

2. **Track Agent Usage**:
   ```python
   # Log database queries in your application
   import logging
   
   logger = logging.getLogger('database_access')
   logger.info(f"Agent {agent_name} queried {db_name}")
   ```

3. **Review Conversation History**:
   ```bash
   # Check what queries were executed
   make history AGENT=data-analyst
   ```

#### Multi-Database Strategies

1. **Logical Separation**:
   ```python
   # Separate agents for different databases
   prod_agent = Agent(name="prod-analyst", mcp_servers=[prod_db])
   dev_agent = Agent(name="dev-analyst", mcp_servers=[dev_db])
   ```

2. **Unified Access**:
   ```python
   # Single agent with multiple databases
   unified_agent = Agent(
       name="unified-analyst",
       system_prompt="You have access to production, warehouse, and cache databases.",
       mcp_servers=[prod_db, warehouse_db, cache_db]
   )
   ```

3. **Clear Naming**:
   ```python
   # Use descriptive database names
   create_database_mcp_config("oracle", "sales_production", ...)
   create_database_mcp_config("postgresql", "analytics_warehouse", ...)
   create_database_mcp_config("sqlite", "local_cache", ...)
   ```

### Database Access Limitations

**Current Limitations**:
- Read-only access only (no INSERT, UPDATE, DELETE)
- Query timeout: 30 seconds (not configurable)
- Result limit: 100 rows per query
- No transaction support
- No stored procedure execution
- No connection pooling

**Workarounds**:
- Use database views for complex queries
- Create summary tables for large datasets
- Use aggregation queries instead of fetching all rows
- Break complex analysis into multiple queries

**Future Enhancements** (under consideration):
- Configurable query timeouts
- Configurable result limits
- Write access with explicit confirmation
- Connection pooling for better performance
- Support for stored procedures
- Query result caching

### Database Access Quick Reference

#### Supported Databases

| Database | Command | Config Function |
|----------|---------|-----------------|
| Oracle (Primary) | `sql -mcp` | `create_database_mcp_config("oracle", ...)` |
| PostgreSQL | `npx -y @modelcontextprotocol/server-postgres` | `create_database_mcp_config("postgresql", ...)` |
| MySQL | `npx -y @modelcontextprotocol/server-mysql` | `create_database_mcp_config("mysql", ...)` |
| SQLite | `npx -y mcp-server-sqlite-npx` | `create_database_mcp_config("sqlite", ...)` |

#### Oracle Connection Methods

```python
# Method 1: Existing SQLcl connection (recommended)
create_database_mcp_config("oracle", "db_name", connection_name="PROD")

# Method 2: TNS alias
create_database_mcp_config("oracle", "db_name", 
    tns_name="PROD_TNS", username="user", password="pass")

# Method 3: Full connection details
create_database_mcp_config("oracle", "db_name",
    host="db.example.com", port=1521, service_name="PRODDB",
    username="user", password="pass")
```

#### Common Database Tools

| Tool | Oracle Name | Description |
|------|-------------|-------------|
| Query execution | `run-sql` | Execute SELECT queries |
| List tables | `list-connections` | List tables/connections |
| Describe table | `describe_table` | Get table schema |
| Get schema | `get_schema` | Get complete database schema |

#### Quick Start Commands

```bash
# Create database-enabled agent (CLI)
make run
# Select "Create new agent" → Enable database access

# View agents with database info
make agents

# View agent database configuration
make agent-info AGENT=agent-name

# Test SQLcl installation (Oracle)
sql -version

# Test MCP server installation
npx -y @modelcontextprotocol/server-postgres --help
npx -y mcp-server-sqlite-npx --help
```

#### Code Snippets

**Create Oracle agent**:
```python
from offline_chat import Agent, AgentManager
from offline_chat.database_config import create_database_mcp_config

manager = AgentManager()
oracle_config = create_database_mcp_config("oracle", "prod_db", connection_name="PROD")
agent = Agent(name="analyst", display_name="Analyst", base_model="llama3.1:latest",
              system_prompt="You are a data analyst.", temperature=0.3,
              mcp_servers=[oracle_config])
manager.create_agent(agent)
```

**Chat with database agent**:
```python
import asyncio
from offline_chat import AgentManager, ChatSession

async def chat():
    session = ChatSession(AgentManager())
    await session.start_async("analyst")
    for chunk in session.send_message("What tables are available?"):
        print(chunk, end="", flush=True)
    await session.end_async()

asyncio.run(chat())
```

**Validate connection**:
```python
from offline_chat.database_config import create_database_mcp_config
from offline_chat.connection_validator import validate_database_connection

config = create_database_mcp_config("postgresql", "db", host="localhost",
                                   port=5432, database="test", 
                                   username="user", password="pass")
success, error = validate_database_connection(config)
print("✓ Connected" if success else f"✗ Failed: {error}")
```

### Sample Database for Testing

A sample SQLite database with realistic company sales data is included for testing database-connected agents.

#### Quick Setup

1. **Generate the sample database**:
   ```bash
   uv run python create_sample_db.py
   ```

   This creates `sample_company.db` with:
   - 10 customers (various companies)
   - 10 products (software, hardware, services)
   - 5 sales representatives
   - 50 orders (last 6 months)
   - 113 order items
   - ~$470K in total sales

2. **Get the absolute path**:
   ```bash
   ./setup_demo_agent.sh
   ```
   
   This displays the full path you'll need for the connection.

3. **Create a database connection** (via CLI):
   ```bash
   make run
   # Select: 7. Manage database connections
   # Select: 1. Create new connection
   # Name: company-sales-db
   # Type: sqlite
   # Path: /full/path/to/sample_company.db (from step 2)
   ```

4. **Create a sales analyst agent**:
   ```bash
   # Select: 1. Create new agent
   # Name: sales-analyst
   # Display: Sales Data Analyst
   # Model: llama3.1:latest
   # Prompt: You are a sales data analyst...
   # Temperature: 0.3
   ```

5. **Assign the database**:
   ```bash
   # Select: 6. Update agent
   # Select: sales-analyst
   # Select: 2. Update database connections
   # Select: 1. Assign connection
   # Select: company-sales-db
   # Access level: 1. READ_ONLY
   ```

6. **Start analyzing**:
   ```bash
   # Select: 4. Chat with agent
   # Select: sales-analyst
   # Ask: "What were our total sales last month?"
   ```

#### Sample Questions

Try these questions with your sales analyst agent:

- "What were our total sales last month?"
- "Who are our top 5 customers by revenue?"
- "Which products are selling best?"
- "Show me sales trends over the last 6 months"
- "Which sales rep has the highest performance?"
- "What's our average order value?"
- "Which product category generates the most revenue?"
- "Are there any customers who haven't ordered recently?"

#### Database Schema

**Tables**:
- `customers` - Company customer information (10 records)
- `products` - Product catalog with categories (10 records)
- `sales_reps` - Sales team members (5 records)
- `orders` - Customer orders with status (50 records)
- `order_items` - Individual line items (113 records)

**Sample Queries**:
```sql
-- Monthly sales trend
SELECT strftime('%Y-%m', order_date) as month, 
       COUNT(*) as orders,
       SUM(total_amount) as revenue
FROM orders
WHERE status = 'Completed'
GROUP BY month
ORDER BY month DESC;

-- Top customers
SELECT c.company_name, 
       COUNT(o.order_id) as order_count,
       SUM(o.total_amount) as total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'Completed'
GROUP BY c.customer_id
ORDER BY total_revenue DESC
LIMIT 5;

-- Product performance
SELECT p.product_name,
       p.category,
       SUM(oi.quantity) as units_sold,
       SUM(oi.subtotal) as revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'Completed'
GROUP BY p.product_id
ORDER BY revenue DESC;
```

#### Regenerating Sample Data

To create a fresh database with new random data:

```bash
uv run python create_sample_db.py
```

This deletes the existing database and creates a new one with different random orders.

#### Testing Access Levels

The sample database is perfect for testing different access levels:

```python
from offline_chat import Agent, AgentManager
from offline_chat.database import DatabaseConnectionManager, AgentConnectionAssignment, AccessLevel

db_manager = DatabaseConnectionManager()
agent_manager = AgentManager(db_manager=db_manager)

# Create connection
from offline_chat.database import DatabaseConnection
conn = DatabaseConnection(
    name="company-sales-db",
    database_type="sqlite",
    file_path="/path/to/sample_company.db"
)
db_manager.create_connection(conn)

# Create agent with table-specific read access
agent = Agent(
    name="limited-analyst",
    display_name="Limited Analyst",
    base_model="llama3.1:latest",
    system_prompt="You can only view orders and customers.",
    temperature=0.3,
    connection_assignments=[
        AgentConnectionAssignment(
            connection_name="company-sales-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["orders", "customers", "order_items"]
        )
    ]
)
agent_manager.create_agent(agent)
```

## Configuration

### Custom Data Location

You can change where Offline Chat stores its data using several methods:

#### Method 1: Environment Variable (Recommended)

Set the `OFFLINE_CHAT_DATA_DIR` environment variable before running the application:

```bash
# Temporary (current session only)
export OFFLINE_CHAT_DATA_DIR=/path/to/my/data
make run

# Permanent (add to your shell profile)
echo 'export OFFLINE_CHAT_DATA_DIR=/path/to/my/data' >> ~/.zshrc
source ~/.zshrc
```

This affects both the CLI and library usage. The environment variable is evaluated at runtime, so you can change it between runs.

#### Method 2: Programmatic Configuration

When using as a library, specify custom paths directly:

```python
from offline_chat import AgentManager, ChatSession

# Custom paths for both agents and history
manager = AgentManager(
    agents_dir="/custom/path/agents",
    history_dir="/custom/path/history"
)

# Or customize just one
manager = AgentManager(
    agents_dir="/custom/agents"  # history uses default location
)

# Use the manager as normal
session = ChatSession(manager)
```

#### Method 3: Per-Project Configuration

For project-specific data isolation, set the environment variable in your project's run script:

```python
import os
os.environ["OFFLINE_CHAT_DATA_DIR"] = "/my/project/data"

# Import after setting the env var
from offline_chat import AgentManager
manager = AgentManager()  # Uses /my/project/data
```

### Configuration Precedence

1. Explicit paths passed to `AgentManager()` (highest priority)
2. `OFFLINE_CHAT_DATA_DIR` environment variable
3. Default: `~/.offline-chat/` (lowest priority)

## Development

### Available Make Targets

Run `make help` to see all available targets:

```
Installation:
  install              Install project dependencies using uv
  install-dev          Install project with dev dependencies

Running:
  run                  Start the CLI application

Agent Management:
  agents               List all created agents
  models               List available Ollama models
  history              Show chat history (usage: make history AGENT=name)
  agent-info           Show agent config (usage: make agent-info AGENT=name)

Database Management:
  connections          List all database connections
  migrate              Run migration from inline database configs

Testing:
  test                 Run the test suite using pytest
  test-verbose         Run tests with verbose output
  test-coverage        Run tests with coverage report
  test-pbt             Run only property-based tests (hypothesis)

Code Quality:
  lint                 Run code quality checks using ruff
  lint-fix             Run linter and automatically fix issues
  format               Format code using ruff
  format-check         Check code formatting without making changes
  check                Run all code quality checks (lint + format check)

Versioning:
  bump                 Bump version based on conventional commits (auto-detect)
  bump-minor           Bump minor version (new features)
  bump-major           Bump major version (breaking changes)
  changelog            Generate/update CHANGELOG.md from commits

Cleanup:
  clean                Remove Python caches and build artifacts
  clean-data           Remove runtime data (agents and history)
  clean-all            Remove all generated files including data

Composite:
  all                  Run all checks and tests
  dev                  Full development workflow: install, lint, format, test
```

### Running Tests

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run only property-based tests
make test-pbt

# Run with coverage
make test-coverage

# Verify RAG infrastructure setup (for RAG development)
uv run python verify_rag_setup.py
```

#### Test Structure

The test suite includes:

**Unit Tests**:
- Configuration and validation logic
- Query safety validation
- Result formatting
- Credential masking

**Property-Based Tests** (using Hypothesis):
- Configuration serialization round-trips
- Database type validation
- Query safety across all inputs
- Result formatting consistency

**Integration Tests**:
- `test_oracle_integration.py` - Oracle database access through SQLcl MCP server
- `test_sqlite_integration.py` - SQLite database access
- `test_database_integration.py` - Multi-database scenarios
- `test_schema_discovery_integration.py` - Schema discovery tools
- `test_error_scenarios_integration.py` - Error handling and graceful degradation

Integration tests validate complete workflows including agent creation, session management, tool calling, and connection lifecycle.

### Code Quality

```bash
# Check for issues
make lint

# Auto-fix issues
make lint-fix

# Format code
make format

# Run all checks
make check
```

## Project Structure

```
offline-chat/
├── main.py                    # Entry point
├── pyproject.toml             # Package configuration
├── Makefile                   # Build tasks
├── offline_chat/              # Main package
│   ├── __init__.py            # Package exports
│   ├── agent.py               # Agent dataclass
│   ├── manager.py             # AgentManager implementation
│   ├── session.py             # ChatSession implementation
│   ├── history.py             # HistoryStore implementation
│   ├── cli.py                 # CLI implementation
│   ├── exceptions.py          # Custom exceptions
│   ├── mcp_client.py          # MCP client and manager
│   ├── mcp_config.py          # MCP server configuration
│   ├── mcp_presets.py         # MCP server presets management
│   ├── database_config.py     # Database MCP configuration factory
│   ├── database_config_cli.py # Database configuration CLI
│   ├── connection_validator.py # Database connection validation
│   ├── credential_utils.py    # Credential masking utilities
│   ├── query_validator.py     # SQL query safety validation
│   ├── query_result.py        # Query result formatting
│   ├── tools.py               # Web search tools
│   ├── search.py              # Search providers
│   └── fetch.py               # Web fetch tool
└── tests/                     # Test suite
    ├── test_agent.py
    ├── test_manager.py
    ├── test_session.py
    ├── test_history.py
    ├── test_cli.py
    ├── test_mcp_client.py
    ├── test_mcp_config.py
    ├── test_database_config.py
    ├── test_database_config_factory.py
    ├── test_database_config_cli.py
    ├── test_connection_validator.py
    ├── test_credential_utils.py
    ├── test_query_validator.py
    ├── test_query_result.py
    ├── test_oracle_integration.py        # Oracle database integration tests
    ├── test_sqlite_integration.py        # SQLite database integration tests
    ├── test_database_integration.py      # Multi-database integration tests
    ├── test_schema_discovery_integration.py  # Schema discovery tests
    ├── test_error_scenarios_integration.py   # Error handling tests
    ├── test_database_tool_discovery.py
    ├── test_tools.py
    ├── test_search.py
    └── test_fetch.py
```

Runtime data is stored in `~/.offline-chat/` (see [Data Storage](#data-storage)).

## Troubleshooting

### "Cannot connect to Ollama. Is it running?"

Ensure Ollama is running:
```bash
ollama serve
```

### "Agent 'name' not found"

The agent doesn't exist. Use the "List agents" option to see available agents.

### "Invalid agent name"

Agent names must use only lowercase letters, numbers, and hyphens (e.g., `my-agent-1`).

## Versioning

This project uses [Semantic Versioning](https://semver.org/) with [Conventional Commits](https://www.conventionalcommits.org/).

### Automatic Releases (GitLab CI/CD)

Releases are automated via GitLab CI/CD using [semantic-release](https://semantic-release.gitbook.io/):

1. Commits to `main` trigger the pipeline
2. `semantic-release` analyzes commits since last release
3. Version is bumped based on commit types:
   - `feat:` → MINOR (0.x.0)
   - `fix:` → PATCH (0.0.x)
   - `BREAKING CHANGE:` → MAJOR (x.0.0)
4. CHANGELOG.md is updated automatically
5. GitLab release is created with release notes

### Manual Version Bumps

```bash
# Bump version based on commits (auto-detect)
make bump

# Bump minor version (new features)
make bump-minor

# Bump major version (breaking changes)
make bump-major

# Generate changelog
make changelog
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit message guidelines.

## Roadmap

### Completed

- ✅ **MCP Server Integration**: Connect agents to Model Context Protocol servers for extended tool capabilities
- ✅ **Database Access**: Query Oracle, PostgreSQL, MySQL, and SQLite databases with read-only access, schema discovery, and audit logging
- ✅ **RAG (Retrieval-Augmented Generation)**: Query external documents, web pages, and database tables as knowledge sources with automatic source citation

### Future Features

Features under consideration:

- **Multi-agent Conversations**: Support conversations between multiple agents
- **Export/Import Agents**: Share agent configurations between users
- **Agent Templates**: Pre-configured agent templates for common use cases
- **Tool Usage Analytics**: Track and visualize tool usage patterns across sessions
- **Database Write Access**: Optional write operations with explicit user confirmation

## Third-Party Dependencies

Offline Chat uses several open-source libraries to provide its functionality. All dependencies use permissive open-source licenses.

For detailed license information, see [DEPENDENCIES.md](DEPENDENCIES.md).

### Core Dependencies

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| [ollama](https://github.com/ollama/ollama-python) | >=0.4.0 | MIT | Python client for Ollama API |
| [requests](https://github.com/psf/requests) | >=2.32.0 | Apache 2.0 | HTTP library for web requests |
| [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) | >=4.12.0 | MIT | HTML/XML parsing for web scraping |
| [mcp](https://github.com/modelcontextprotocol/python-sdk) | >=1.0.0 | MIT | Model Context Protocol SDK |

### Web Search Dependencies

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| [ddgs](https://github.com/deedy5/duckduckgo_search) | >=7.0.0 | MIT | DuckDuckGo search integration |

### RAG Dependencies

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| [chromadb](https://github.com/chroma-core/chroma) | >=1.4.1 | Apache 2.0 | Vector database for embeddings |
| [sentence-transformers](https://github.com/UKPLab/sentence-transformers) | >=5.2.0 | Apache 2.0 | Local embedding generation |

### Development Dependencies

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| [pytest](https://github.com/pytest-dev/pytest) | >=8.0.0 | MIT | Testing framework |
| [hypothesis](https://github.com/HypothesisWorks/hypothesis) | >=6.100.0 | MPL 2.0 | Property-based testing |
| [ruff](https://github.com/astral-sh/ruff) | >=0.8.0 | MIT | Linting and formatting |
| [commitizen](https://github.com/commitizen-tools/commitizen) | >=4.0.0 | MIT | Commit message standardization |

### License Compliance

All dependencies use permissive open-source licenses (MIT, Apache 2.0, MPL 2.0) that allow:
- Commercial use
- Modification
- Distribution
- Private use

**RAG-Specific Compliance**:
- **ChromaDB** (Apache 2.0): Vector database with no usage restrictions
- **sentence-transformers** (Apache 2.0): Local embedding models with no API dependencies
- **No proprietary dependencies**: All RAG components are fully open-source

For detailed license information, see each package's repository or run:
```bash
uv pip show <package-name>
```

## License

MIT
