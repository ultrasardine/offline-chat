# Terminal UI Guidelines

## User Experience Principles
- Keep interactions simple and intuitive
- Provide clear feedback for all actions
- Handle errors gracefully with helpful messages
- Support keyboard shortcuts where appropriate

## Input Handling
- Strip whitespace from user input
- Validate input before processing
- Provide default values where sensible
- Allow cancellation with Ctrl+C

## Output Formatting
- Use consistent indentation
- Add blank lines between sections for readability
- Use colors sparingly (optional, with fallback)
- Show progress indicators for long operations

## Chat Session UI
```
┌─────────────────────────────────────────┐
│ [Agent Name] - Commands: exit, clear    │
├─────────────────────────────────────────┤
│                                         │
│ You: <user message>                     │
│                                         │
│ Agent: <response with streaming>        │
│                                         │
└─────────────────────────────────────────┘
```

## Error Messages
- Connection errors: "Cannot connect to Ollama. Is it running?"
- Model not found: "Agent 'name' not found. Use 'list' to see available agents."
- Invalid input: "Invalid agent name. Use lowercase letters, numbers, and hyphens only."

## Streaming Output
- Stream responses character by character for natural feel
- Show typing indicator while waiting for first token
- Handle interruption gracefully (Ctrl+C during response)

## Color Scheme (Optional)
- User input: default/white
- Agent response: cyan/blue
- System messages: yellow
- Errors: red
- Success: green
