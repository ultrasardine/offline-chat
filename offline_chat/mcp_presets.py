"""MCP Server presets management for Offline Chat application.

This module provides functionality to manage a list of pre-configured
MCP servers that users can select from when creating agents.
"""

import json
from pathlib import Path
from typing import Any

from offline_chat.exceptions import MCPConfigError
from offline_chat.manager import get_default_data_dir
from offline_chat.mcp_config import MCPServerConfig

# Default presets file name
MCP_PRESETS_FILE = "mcp_presets.json"


def get_presets_path() -> Path:
    """Get the path to the MCP presets file.

    Returns:
        Path to the mcp_presets.json file.
    """
    return get_default_data_dir() / MCP_PRESETS_FILE


def load_presets() -> list[MCPServerConfig]:
    """Load MCP server presets from the presets file.

    Returns:
        List of MCPServerConfig objects. Empty list if file doesn't exist.
    """
    presets_path = get_presets_path()

    if not presets_path.exists():
        return []

    try:
        with open(presets_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        presets = []
        for item in data.get("servers", []):
            try:
                config = MCPServerConfig.from_dict(item)
                presets.append(config)
            except (KeyError, TypeError):
                # Skip invalid entries
                continue

        return presets

    except (json.JSONDecodeError, OSError):
        return []


def save_presets(presets: list[MCPServerConfig]) -> None:
    """Save MCP server presets to the presets file.

    Args:
        presets: List of MCPServerConfig objects to save.
    """
    presets_path = get_presets_path()

    # Ensure directory exists
    presets_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"servers": [p.to_dict() for p in presets]}

    with open(presets_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_preset(config: MCPServerConfig) -> None:
    """Add a new MCP server preset.

    Args:
        config: The MCPServerConfig to add.

    Raises:
        MCPConfigError: If a preset with the same name already exists.
    """
    config.validate()

    presets = load_presets()

    # Check for duplicate name
    for existing in presets:
        if existing.name == config.name:
            raise MCPConfigError(f"Preset '{config.name}' already exists")

    presets.append(config)
    save_presets(presets)


def remove_preset(name: str) -> bool:
    """Remove an MCP server preset by name.

    Args:
        name: The name of the preset to remove.

    Returns:
        True if the preset was removed, False if not found.
    """
    presets = load_presets()
    original_count = len(presets)

    presets = [p for p in presets if p.name != name]

    if len(presets) < original_count:
        save_presets(presets)
        return True

    return False


def get_preset(name: str) -> MCPServerConfig | None:
    """Get a specific preset by name.

    Args:
        name: The name of the preset.

    Returns:
        MCPServerConfig if found, None otherwise.
    """
    presets = load_presets()

    for preset in presets:
        if preset.name == name:
            return preset

    return None


# Built-in presets that are always available
BUILTIN_PRESETS: list[dict[str, Any]] = [
    {
        "name": "fetch",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "disabled": False,
        "description": "Fetch and extract content from URLs",
    },
    {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "~"],
        "env": {},
        "disabled": False,
        "description": "Read/write files (configure path after selection)",
    },
    {
        "name": "github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""},
        "disabled": False,
        "description": "GitHub API integration (requires token)",
    },
    {
        "name": "memory",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "disabled": False,
        "description": "Persistent memory/knowledge graph",
    },
]


def get_all_available_presets() -> list[tuple[MCPServerConfig, str]]:
    """Get all available presets (built-in + user-defined).

    Returns:
        List of tuples (MCPServerConfig, description).
        Built-in presets come first, then user-defined.
    """
    result: list[tuple[MCPServerConfig, str]] = []

    # Add built-in presets
    for builtin in BUILTIN_PRESETS:
        config = MCPServerConfig(
            name=builtin["name"],
            command=builtin["command"],
            args=builtin["args"].copy(),
            env=builtin.get("env", {}).copy(),
            disabled=builtin.get("disabled", False),
        )
        result.append((config, builtin.get("description", "")))

    # Add user-defined presets
    user_presets = load_presets()
    for preset in user_presets:
        # Skip if name conflicts with built-in
        if any(b["name"] == preset.name for b in BUILTIN_PRESETS):
            continue
        result.append((preset, "User-defined"))

    return result
