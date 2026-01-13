# Contributing to Offline Chat

Thank you for your interest in contributing to Offline Chat! This document provides guidelines and instructions for contributing.

## Development Setup

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd offline-chat
   ```

2. Install dependencies:
   ```bash
   make install-dev
   ```

3. Run tests to verify setup:
   ```bash
   make test
   ```

## Commit Message Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages. This enables automatic changelog generation and semantic versioning.

### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | A new feature | MINOR |
| `fix` | A bug fix | PATCH |
| `docs` | Documentation only changes | - |
| `style` | Code style changes (formatting, semicolons, etc.) | - |
| `refactor` | Code change that neither fixes a bug nor adds a feature | - |
| `perf` | Performance improvement | PATCH |
| `test` | Adding or updating tests | - |
| `build` | Changes to build system or dependencies | - |
| `ci` | Changes to CI configuration | - |
| `chore` | Other changes that don't modify src or test files | - |

### Breaking Changes

For breaking changes, add `!` after the type/scope or include `BREAKING CHANGE:` in the footer:

```
feat!: change default data directory to ~/.offline-chat

BREAKING CHANGE: Data is no longer stored in ./data by default.
Users must migrate existing data or set OFFLINE_CHAT_DATA_DIR.
```

### Examples

```bash
# Feature
feat(agent): add temperature validation

# Bug fix
fix(history): handle empty message list on load

# Documentation
docs: update README with library usage examples

# Breaking change
feat(storage)!: change default data directory location

# With scope and body
feat(cli): add color support for messages

Add optional color formatting for user and agent messages.
Colors can be disabled via NO_COLOR environment variable.

Closes #42
```

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible new features
- **PATCH** version for backwards-compatible bug fixes

Version is maintained in:
- `pyproject.toml` - Package version
- `offline_chat/__init__.py` - `__version__` variable

## Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```

2. Make your changes following the coding standards

3. Ensure all tests pass:
   ```bash
   make check
   make test
   ```

4. Commit using conventional commit format

5. Push and create a pull request

## Code Quality

Before submitting, ensure:

```bash
# Run all checks
make check

# Run tests
make test

# Format code
make format
```

## Testing

- Write tests for new features
- Maintain or improve test coverage
- Use property-based tests (Hypothesis) for universal properties
- Use unit tests for specific examples and edge cases

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run only property-based tests
make test-pbt
```

## Questions?

Open an issue for questions or discussions about contributing.
