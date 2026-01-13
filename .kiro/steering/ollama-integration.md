# Ollama Integration Guide

## Ollama Python Client

### Installation
```bash
pip install ollama
```

### Basic Chat Usage
```python
import ollama

response = ollama.chat(
    model='agent_name',
    messages=[
        {'role': 'user', 'content': 'Your message here'}
    ]
)

print(response['message']['content'])
```

### Streaming Responses
```python
import ollama

stream = ollama.chat(
    model='agent_name',
    messages=[{'role': 'user', 'content': 'Hello'}],
    stream=True
)

for chunk in stream:
    print(chunk['message']['content'], end='', flush=True)
```

## Modelfile Structure

### Creating Agent Modelfiles
Each agent requires a Modelfile with this structure:

```
FROM <base_model>

SYSTEM "<system_prompt_defining_persona>"

PARAMETER temperature <0.0-1.0>
```

### Example: German Tutor Agent
```
FROM llama3:latest

SYSTEM "You are a friendly German language tutor. Help users learn German through conversation, correct their mistakes gently, and explain grammar rules when asked. Always provide translations and pronunciation tips. Respond in a mix of German and English appropriate to the user's level."

PARAMETER temperature 0.7
```

### Example: Code Reviewer Agent
```
FROM llama3:latest

SYSTEM "You are an expert code reviewer. Analyze code for bugs, security issues, performance problems, and style violations. Provide constructive feedback with specific suggestions for improvement. Be thorough but encouraging."

PARAMETER temperature 0.3
```

## Ollama CLI Commands

### Create Model from Modelfile
```bash
ollama create <agent_name> -f /path/to/Modelfile
```

### List Available Models
```bash
ollama list
```

### Delete a Model
```bash
ollama rm <agent_name>
```

### Check Ollama Status
```bash
ollama ps
```

## Python Subprocess Integration
When creating models programmatically:

```python
import subprocess

def create_ollama_model(name: str, modelfile_path: str) -> bool:
    result = subprocess.run(
        ['ollama', 'create', name, '-f', modelfile_path],
        capture_output=True,
        text=True
    )
    return result.returncode == 0
```

## Error Handling
- Check if Ollama is running before operations
- Handle model not found errors
- Timeout handling for slow responses
- Graceful degradation when Ollama is unavailable
