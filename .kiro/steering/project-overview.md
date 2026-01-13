# Offline Chat - Project Overview

## Description
Offline Chat is a terminal-based chatbot application that uses Ollama models locally. Users can create personalized AI agents with specific purposes, names, and personas. Each agent maintains its own conversation history and context across sessions.

## Core Concepts

### Agents
An agent is a customized Ollama model with:
- A unique name (e.g., "german-tutor", "code-reviewer")
- A base Ollama model (e.g., "llama3:latest", "mistral")
- A system prompt defining its persona and purpose
- Persistent conversation history
- Custom parameters (temperature, etc.)

### Modelfile Integration
Each agent is backed by an Ollama Modelfile that defines:
```
FROM <base_model>
SYSTEM "<persona and purpose>"
PARAMETER temperature <value>
```

## Technology Stack
- Python 3.13+
- Ollama Python client (`ollama` package)
- Local file storage for agent configs and history
- Terminal UI for interaction

## Project Structure
```
offline-chat/
├── main.py              # Entry point
├── agents/              # Agent management
│   ├── __init__.py
│   ├── agent.py         # Agent class
│   └── manager.py       # Agent CRUD operations
├── chat/                # Chat functionality
│   ├── __init__.py
│   └── session.py       # Chat session handling
├── storage/             # Persistence
│   ├── __init__.py
│   └── history.py       # Conversation history
├── data/                # Runtime data (gitignored)
│   ├── agents/          # Agent Modelfiles
│   └── history/         # Chat histories
└── tests/               # Test suite
```

## Key Commands
- `ollama create <agent_name> -f <modelfile>` - Create agent model
- `ollama list` - List available models
- `ollama run <agent_name>` - Run model interactively
