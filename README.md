# Offline Chat

A terminal-based chatbot application that uses local Ollama models. Create personalized AI agents with specific personas, system prompts, and maintain conversation history across sessions.

## Features

- **Custom Agents**: Create AI agents with unique names, personas, and behaviors
- **Persistent History**: Conversation history is saved and restored across sessions
- **Local & Private**: All processing happens locally using Ollama - no data leaves your machine
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

```bash
# Start the interactive CLI
make run

# Or directly with uv
uv run python main.py
```

The CLI provides a menu-driven interface:
- **Create agent**: Define a new AI agent with custom persona
- **List agents**: View all created agents
- **Chat with agent**: Start a conversation with an agent
- **Delete agent**: Remove an agent and its history

### Chat Commands

While chatting with an agent:
- Type your message and press Enter to send
- Type `exit` to save and return to the main menu
- Type `clear` to reset conversation history

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
    temperature=0.7
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

# Send a message and stream the response
for chunk in session.send_message("Wie geht es dir?"):
    print(chunk, end="", flush=True)
print()  # Newline after response

# Access conversation history
history = session.history
for msg in history.messages:
    print(f"[{msg.role}]: {msg.content}")

# Clear conversation history
session.clear_history()

# End session (automatically saves history)
session.end()
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

### Example Agents

**German Tutor**:
```
Name: german-tutor
Base Model: llama3:latest
System Prompt: You are a friendly German language tutor. Help users learn 
German through conversation, correct their mistakes gently, and explain 
grammar rules when asked.
Temperature: 0.7
```

**Code Reviewer**:
```
Name: code-reviewer
Base Model: llama3:latest
System Prompt: You are an expert code reviewer. Analyze code for bugs, 
security issues, and style violations. Provide constructive feedback.
Temperature: 0.3
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
│   └── exceptions.py          # Custom exceptions
└── tests/                     # Test suite
    ├── test_agent.py
    ├── test_manager.py
    ├── test_session.py
    ├── test_history.py
    └── test_cli.py
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

## License

MIT
