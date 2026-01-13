# Agent Management

## Agent Data Model

### Agent Configuration
```python
@dataclass
class AgentConfig:
    name: str                    # Unique identifier (kebab-case)
    display_name: str            # Human-readable name
    base_model: str              # Ollama base model (e.g., "llama3:latest")
    system_prompt: str           # Persona and purpose definition
    temperature: float = 0.7     # Response creativity (0.0-1.0)
    created_at: datetime         # Creation timestamp
```

### Agent Storage Structure
```
data/
├── agents/
│   ├── german-tutor/
│   │   ├── config.json      # Agent configuration
│   │   └── Modelfile        # Ollama Modelfile
│   └── code-reviewer/
│       ├── config.json
│       └── Modelfile
└── history/
    ├── german-tutor.json    # Conversation history
    └── code-reviewer.json
```

## Agent Lifecycle

### 1. Create Agent
1. Validate agent name (unique, valid characters)
2. Generate Modelfile from config
3. Save config.json
4. Run `ollama create` to register model
5. Initialize empty history

### 2. List Agents
- Read all agent configs from data/agents/
- Display name, base model, purpose summary
- Show last interaction timestamp

### 3. Use Agent
1. Load agent config
2. Load conversation history
3. Start chat session
4. Append messages to history
5. Save history on exit

### 4. Delete Agent
1. Run `ollama rm` to remove model
2. Delete agent directory
3. Delete history file

## Conversation History Format
```json
{
  "agent_name": "german-tutor",
  "messages": [
    {
      "role": "user",
      "content": "How do I say hello?",
      "timestamp": "2025-01-13T10:30:00Z"
    },
    {
      "role": "assistant", 
      "content": "In German, you say 'Hallo'...",
      "timestamp": "2025-01-13T10:30:05Z"
    }
  ],
  "last_updated": "2025-01-13T10:30:05Z"
}
```

## Terminal Commands

### Main Menu
```
Offline Chat - Agent Manager

1. Create new agent
2. List agents
3. Chat with agent
4. Delete agent
5. Exit

Select option: _
```

### Agent Creation Flow
```
Create New Agent
----------------
Agent name (kebab-case): german-tutor
Display name: German Language Tutor
Base model [llama3:latest]: 
Purpose/persona: Help me learn German through conversation
Temperature [0.7]: 

Creating agent... Done!
```

### Chat Interface
```
[German Language Tutor] - Type 'exit' to quit, 'clear' to reset history

You: How do I introduce myself?
Tutor: Great question! In German, you can say...

You: exit
Saving conversation... Done!
```
