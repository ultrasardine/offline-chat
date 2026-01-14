# Offline Chat

A terminal-based chatbot application that uses local Ollama models. Create personalized AI agents with specific personas, system prompts, and maintain conversation history across sessions.

## Features

- **Custom Agents**: Create AI agents with unique names, personas, and behaviors
- **Persistent History**: Conversation history is saved and restored across sessions
- **Local & Private**: All processing happens locally using Ollama - no data leaves your machine
- **Web Search**: Enable agents to search the web and fetch pages for current information
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
```

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

### Future Features

Features under consideration:

- **RAG (Retrieval Augmented Generation)**: Allow agents to query external documents and knowledge bases
- **Multi-agent Conversations**: Support conversations between multiple agents
- **Export/Import Agents**: Share agent configurations between users
- **Agent Templates**: Pre-configured agent templates for common use cases
- **Tool Usage Analytics**: Track and visualize tool usage patterns across sessions

## License

MIT
