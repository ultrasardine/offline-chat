# Coding Standards

## Python Style
- Follow PEP 8 conventions
- Use type hints for all function signatures
- Use dataclasses or Pydantic models for data structures
- Prefer f-strings for string formatting
- Maximum line length: 100 characters
- Always use UV instead of PIP. This is mandatory.
- Never send long chunks of text to the terminal for running as script. It will break the connection to the terminal.
- use venv in the project root "./.venv"

## Naming Conventions
- Classes: PascalCase (e.g., `AgentManager`, `ChatSession`)
- Functions/methods: snake_case (e.g., `create_agent`, `load_history`)
- Constants: UPPER_SNAKE_CASE (e.g., `DEFAULT_TEMPERATURE`)
- Private methods: prefix with underscore (e.g., `_validate_config`)

## Error Handling
- Use custom exceptions for domain-specific errors
- Always provide meaningful error messages
- Handle Ollama connection errors gracefully
- Validate user input before processing

## File Organization
- One class per file when the class is substantial
- Group related utilities in a single module
- Keep imports organized: stdlib, third-party, local

## Documentation
- Docstrings for all public functions and classes
- Use Google-style docstrings format
- Include usage examples for complex functions

## Testing
- Use pytest as the testing framework
- Use hypothesis for property-based testing
- Test files mirror source structure with `test_` prefix
- Aim for high coverage on core logic
