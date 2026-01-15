# Offline Chat

A terminal-based chatbot application that uses local Ollama models. Create personalized AI agents with specific personas, system prompts, and maintain conversation history across sessions.

## Features

- **Custom Agents**: Create AI agents with unique names, personas, and behaviors
- **Persistent History**: Conversation history is saved and restored across sessions
- **Local & Private**: All processing happens locally using Ollama - no data leaves your machine
- **Web Search**: Enable agents to search the web and fetch pages for current information
- **Database Access**: Connect agents to Oracle, PostgreSQL, MySQL, or SQLite databases for data analysis
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

### Supported Databases

| Database | MCP Server | Primary Support |
|----------|------------|-----------------|
| **Oracle** | Oracle SQLcl (built-in) | ✅ Primary |
| PostgreSQL | `postgres-mcp-server` | ✅ Supported |
| MySQL | `mysql-mcp-server` | ✅ Supported |
| SQLite | `sqlite-mcp-server` | ✅ Supported |

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
# Using uvx (recommended)
uvx postgres-mcp-server --help

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
# Using uvx (recommended)
uvx sqlite-mcp-server --help
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

### Security and Safety

**Read-Only Mode**:
- All database queries are validated for safety
- Write operations (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, REPLACE) are rejected
- Only SELECT queries are allowed by default

**Credential Storage**:
- Database credentials are stored in agent configuration files
- Passwords are masked in CLI displays and logs
- Configuration files should have appropriate file permissions

**Connection Management**:
- Connections are established when chat sessions start
- Connections are reused within a session for efficiency
- All connections are properly closed when sessions end

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
Agent: data-analyst
Display Name: Data Analyst
Base Model: llama3.1:latest
Temperature: 0.7

MCP Servers:
  - prod_db (oracle)
    Connection: PROD_ANALYTICS
  
  - analytics_db (postgresql)
    Host: db.example.com:5432
    Database: analytics
    User: analyst
    Password: ****
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

### Troubleshooting Database Access

#### Connection Issues

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
  uvx postgres-mcp-server --help
  
  # For SQLite
  uvx sqlite-mcp-server --help
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
uvx postgres-mcp-server --host localhost --port 5432 --database testdb --user testuser
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
| PostgreSQL | `uvx postgres-mcp-server` | `create_database_mcp_config("postgresql", ...)` |
| MySQL | `uvx mysql-mcp-server` | `create_database_mcp_config("mysql", ...)` |
| SQLite | `uvx sqlite-mcp-server` | `create_database_mcp_config("sqlite", ...)` |

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
uvx postgres-mcp-server --help
uvx sqlite-mcp-server --help
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

### Future Features

Features under consideration:

- **RAG (Retrieval Augmented Generation)**: Allow agents to query external documents and knowledge bases
- **Multi-agent Conversations**: Support conversations between multiple agents
- **Export/Import Agents**: Share agent configurations between users
- **Agent Templates**: Pre-configured agent templates for common use cases
- **Tool Usage Analytics**: Track and visualize tool usage patterns across sessions
- **Database Write Access**: Optional write operations with explicit user confirmation

## License

MIT
