## 1.0.0 (2026-01-13)

### ⚠ BREAKING CHANGES

* Initial release

### Features

* **cli:** add view history option and agent language field ([44ce31a](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/44ce31abc526048c6c20f9c9bfb456d148f7a220))
* initial release of offline-chat application ([11b302b](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/11b302bec5adb0b7f7ac9494c0731ccf459d3e28))

### Bug Fixes

* improve context retention and fix flaky test ([cb0fdc1](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/cb0fdc12e8adfb813bd8bd956604cb807d904222))

### Documentation

* add roadmap section to README ([c472d67](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/c472d67eb296aa3128dd30e99226b042e8d30bdc))
* improve README with CLI usage and library examples ([34a1565](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/34a15654290846d0018db130b1b46e7c744a37e8))

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-13

### Added

- Initial release of Offline Chat
- Agent management (create, list, delete agents)
- Chat sessions with streaming responses
- Persistent conversation history
- CLI interface with menu-driven navigation
- Library API for programmatic usage
- Custom data directory support via `OFFLINE_CHAT_DATA_DIR` environment variable
- Property-based tests with Hypothesis
- Comprehensive test suite (46 tests)

### Agent Features

- Create agents with custom name, display name, base model, system prompt, and temperature
- Kebab-case naming validation for agent names
- Automatic Modelfile generation for Ollama integration
- Agent configuration stored as JSON

### Chat Features

- Start chat sessions with any created agent
- Stream responses character by character
- Clear conversation history with `clear` command
- Exit and save with `exit` command
- Graceful handling of Ctrl+C interrupts

### Storage

- Default data location: `~/.offline-chat/`
- Configurable via environment variable or constructor parameters
- JSON-based persistence for agent configs and history

[Unreleased]: https://github.com/username/offline-chat/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/username/offline-chat/releases/tag/v0.1.0
