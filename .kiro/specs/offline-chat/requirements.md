# Requirements Document

## Introduction

Offline Chat is a terminal-based chatbot application that enables users to create and interact with personalized AI agents powered by local Ollama models. Each agent has its own persona, purpose, and persistent conversation history. The application can be used as a standalone CLI tool or imported as a library in other Python projects via `uv add git+{repo}`.

## Glossary

- **Agent**: A customized Ollama model with a unique name, persona, system prompt, and persistent conversation history
- **Modelfile**: An Ollama configuration file that defines the base model, system prompt, and parameters for an agent
- **Chat_Session**: An interactive conversation between a user and an agent
- **Agent_Manager**: The component responsible for creating, listing, and deleting agents
- **History_Store**: The component responsible for persisting and retrieving conversation history
- **CLI**: The command-line interface for interacting with the application

## Requirements

### Requirement 1: Agent Creation

**User Story:** As a user, I want to create a new AI agent with a specific persona and purpose, so that I can have specialized conversations tailored to my needs.

#### Acceptance Criteria

1. WHEN a user initiates agent creation, THE CLI SHALL prompt for agent name, display name, base model, system prompt, and temperature
2. WHEN a user provides an agent name, THE Agent_Manager SHALL validate that the name uses only lowercase letters, numbers, and hyphens
3. WHEN a user provides an agent name that already exists, THE Agent_Manager SHALL reject the creation and display an error message
4. WHEN all required fields are provided, THE Agent_Manager SHALL generate a valid Modelfile with FROM, SYSTEM, and PARAMETER directives
5. WHEN a Modelfile is generated, THE Agent_Manager SHALL save the agent configuration as JSON and the Modelfile to the data/agents/{agent_name}/ directory
6. WHEN an agent configuration is saved, THE Agent_Manager SHALL execute `ollama create {agent_name} -f {modelfile_path}` to register the model with Ollama
7. IF the Ollama create command fails, THEN THE Agent_Manager SHALL display the error and clean up any partially created files

### Requirement 2: Agent Listing

**User Story:** As a user, I want to see all my created agents, so that I can choose which one to interact with.

#### Acceptance Criteria

1. WHEN a user requests the agent list, THE Agent_Manager SHALL read all agent configurations from the data/agents/ directory
2. WHEN displaying agents, THE CLI SHALL show the agent name, display name, base model, and a truncated purpose summary
3. WHEN no agents exist, THE CLI SHALL display a message indicating no agents are available

### Requirement 3: Chat Session

**User Story:** As a user, I want to chat with an agent and have my conversation history preserved, so that the agent maintains context across sessions.

#### Acceptance Criteria

1. WHEN a user selects an agent to chat with, THE Chat_Session SHALL load the existing conversation history for that agent
2. WHEN a user sends a message, THE Chat_Session SHALL append the message to the conversation history and send it to Ollama
3. WHEN Ollama responds, THE Chat_Session SHALL stream the response character by character to provide a natural feel
4. WHEN a response is complete, THE Chat_Session SHALL append the assistant message to the conversation history
5. WHEN a user types 'exit', THE Chat_Session SHALL save the conversation history and return to the main menu
6. WHEN a user types 'clear', THE Chat_Session SHALL reset the conversation history for that agent
7. IF Ollama is not running or unreachable, THEN THE Chat_Session SHALL display "Cannot connect to Ollama. Is it running?" and return to the main menu

### Requirement 4: Agent Deletion

**User Story:** As a user, I want to delete agents I no longer need, so that I can keep my agent list organized.

#### Acceptance Criteria

1. WHEN a user requests to delete an agent, THE CLI SHALL prompt for confirmation
2. WHEN deletion is confirmed, THE Agent_Manager SHALL execute `ollama rm {agent_name}` to remove the model from Ollama
3. WHEN the Ollama model is removed, THE Agent_Manager SHALL delete the agent directory from data/agents/
4. WHEN the agent directory is deleted, THE Agent_Manager SHALL delete the conversation history file from data/history/
5. IF the agent does not exist, THEN THE Agent_Manager SHALL display "Agent '{name}' not found. Use 'list' to see available agents."

### Requirement 5: Conversation History Persistence

**User Story:** As a user, I want my conversation history to be saved automatically, so that I can continue conversations where I left off.

#### Acceptance Criteria

1. WHEN a chat session ends, THE History_Store SHALL save the conversation history to data/history/{agent_name}.json
2. WHEN saving history, THE History_Store SHALL include the agent name, all messages with roles and timestamps, and a last_updated timestamp
3. WHEN a chat session starts, THE History_Store SHALL load the existing history file if it exists
4. WHEN loading history, THE History_Store SHALL return an empty message list if no history file exists

### Requirement 6: Terminal User Interface

**User Story:** As a user, I want a clear and intuitive terminal interface, so that I can easily navigate and use the application.

#### Acceptance Criteria

1. WHEN the application starts, THE CLI SHALL display a main menu with options: Create agent, List agents, Chat with agent, Delete agent, Exit
2. WHEN displaying the chat interface, THE CLI SHALL show the agent display name and available commands (exit, clear)
3. WHEN displaying user input, THE CLI SHALL prefix messages with "You:"
4. WHEN displaying agent responses, THE CLI SHALL prefix messages with the agent display name
5. WHEN an error occurs, THE CLI SHALL display the error message in a clear format
6. WHEN the user presses Ctrl+C, THE CLI SHALL handle the interruption gracefully and save any pending data

### Requirement 7: Library Integration

**User Story:** As a developer, I want to import this application as a library in my Python projects, so that I can programmatically create and interact with agents.

#### Acceptance Criteria

1. THE package SHALL be installable via `uv add git+{repo}`
2. THE package SHALL expose an AgentManager class for creating, listing, and deleting agents
3. THE package SHALL expose a ChatSession class for programmatic conversation with agents
4. THE package SHALL expose an Agent dataclass representing agent configuration
5. WHEN used as a library, THE package SHALL not display terminal UI elements unless explicitly requested

### Requirement 8: Build and Development Tasks

**User Story:** As a developer, I want a Makefile with all available tasks, so that I can easily build, test, and manage the project.

#### Acceptance Criteria

1. THE Makefile SHALL include an 'install' target that installs dependencies using uv
2. THE Makefile SHALL include a 'test' target that runs the test suite using pytest
3. THE Makefile SHALL include a 'lint' target that runs code quality checks
4. THE Makefile SHALL include a 'format' target that formats code
5. THE Makefile SHALL include a 'clean' target that removes generated files and caches
6. THE Makefile SHALL include a 'run' target that starts the CLI application
7. THE Makefile SHALL group related targets with clear descriptions using comments
8. THE Makefile SHALL include a 'help' target that displays all available targets with descriptions
