## 1.0.0 (2026-01-29)

### ⚠ BREAKING CHANGES

* Repository migrated from GitLab to GitHub
* Initial release

### Features

* add database access for agents through MCP servers ([2071e1b](https://github.com/ultrasardine/offline-chat/commit/2071e1b7057f12057bfdef62837da9dbd4337238))
* **cli:** add view history option and agent language field ([44ce31a](https://github.com/ultrasardine/offline-chat/commit/44ce31abc526048c6c20f9c9bfb456d148f7a220))
* initial release of offline-chat application ([11b302b](https://github.com/ultrasardine/offline-chat/commit/11b302bec5adb0b7f7ac9494c0731ccf459d3e28))
* migrate to GitHub with open-source standards ([8742bd6](https://github.com/ultrasardine/offline-chat/commit/8742bd665392c02cfa5e3063b0ad60a14cfdd4f8))

### Bug Fixes

* improve context retention and fix flaky test ([cb0fdc1](https://github.com/ultrasardine/offline-chat/commit/cb0fdc12e8adfb813bd8bd956604cb807d904222))
* resolve CI/CD issues - fix test assertions, linting errors, and release workflow ([af1c7a6](https://github.com/ultrasardine/offline-chat/commit/af1c7a603add8f0015e5c4faafe966d24b3e960d))
* resolve linting and formatting issues ([85f8b18](https://github.com/ultrasardine/offline-chat/commit/85f8b18618ecadf89899485754d04f2812a7f250))
* resolve Modelfile generation and tool calling issues ([7bf3c37](https://github.com/ultrasardine/offline-chat/commit/7bf3c373a982c73f3814e4ae3a65676b287e05cc)), closes [#issue](https://github.com/ultrasardine/offline-chat/issues/issue) [#issue](https://github.com/ultrasardine/offline-chat/issues/issue) [#issue](https://github.com/ultrasardine/offline-chat/issues/issue)
* tool calling now works correctly with web search and MCP ([5821565](https://github.com/ultrasardine/offline-chat/commit/58215651e1105dda4924cb966be75b15f4b5ab62))

### Documentation

* add roadmap section to README ([c472d67](https://github.com/ultrasardine/offline-chat/commit/c472d67eb296aa3128dd30e99226b042e8d30bdc))
* add troubleshooting section for incomplete agent responses ([8b4551b](https://github.com/ultrasardine/offline-chat/commit/8b4551bed112dfe232c98ca5a047bf845a2400e4))
* improve README with CLI usage and library examples ([34a1565](https://github.com/ultrasardine/offline-chat/commit/34a15654290846d0018db130b1b46e7c744a37e8))
* update library usage examples with recommended models ([ac84bd9](https://github.com/ultrasardine/offline-chat/commit/ac84bd96cdc47c0fa7744ff848bdd7b225c3a0b7))

## [1.1.0](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/compare/v1.0.0...v1.1.0) (2026-01-16)

### Features

* add database access for agents through MCP servers ([2071e1b](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/2071e1b7057f12057bfdef62837da9dbd4337238))

### Bug Fixes

* resolve linting and formatting issues ([85f8b18](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/85f8b18618ecadf89899485754d04f2812a7f250))
* tool calling now works correctly with web search and MCP ([5821565](https://gitlab.com/eosts/internal/eosportugal/tools/offline_chat/commit/58215651e1105dda4924cb966be75b15f4b5ab62))

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
