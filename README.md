# MCP Switcher

A simple CLI tool to manage and switch between different MCP (Model Context Protocol) configuration files.

## Installation

```bash
# Install with uv
uv install .

# Install with pipx (recommended for CLI tools)
pipx install .

# Or install with pip
pip install .
```

## Usage

### Basic Commands

```bash
# List all available configurations
mcp-switch list-configs

# Switch to a specific configuration
mcp-switch use <config-name>

# Show currently active configuration
mcp-switch current

# Configure the tool settings
mcp-switch config --show

# Update Codex CLI with servers from the active config
mcp-switch config --client codex
```

### Configuration

First, set up the directory where your MCP configurations are stored:

```bash
# Set configurations directory
mcp-switch config --dir /path/to/your/mcp-configs

# Set target MCP client (claude-desktop, vscode, cursor)
mcp-switch config --client claude-desktop

# Sync Codex CLI now with the currently active config
mcp-switch config --client codex
```

### Supported Clients

- `claude-desktop` - Claude Desktop application (default)
- `vscode` - VS Code with MCP extension
- `cursor` - Cursor editor
- `codex` - Codex CLI (updates `~/.codex/config.toml` from the active config)

## How It Works

1. Store multiple MCP configuration files anywhere in a designated directory tree
2. The tool automatically discovers valid JSON files with MCP structure recursively
3. Configuration names are extracted from the first unique directory name in the path
4. Use `mcp-switch use <config-name>` to activate a configuration
5. The tool copies the selected configuration to the appropriate location for your MCP client
6. Automatically creates backups of existing configurations before switching
7. For Codex, it reads the active MCP JSON and upserts TOML blocks under `[mcp_servers.<name>]` in `~/.codex/config.toml`, preserving unrelated keys and removing stale server blocks

## Configuration File Structure

Your MCP configuration files should be valid JSON files containing MCP server configurations:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "path/to/server",
      "args": ["arg1", "arg2"]
    }
  }
}
```

## Target Paths

- **Claude Desktop (macOS/Linux)**: `~/.config/claude-desktop/claude_desktop_config.json`
- **Claude Desktop (Windows)**: `%APPDATA%/Claude/claude_desktop_config.json`
- **VS Code**: `.vscode/mcp.json` (in current directory)
- **Cursor**: `~/.cursor/mcp.json`
- **Codex**: `~/.codex/config.toml` (upserted with `[mcp_servers.*]`)

## Features

- ✅ Multiple MCP client support
- ✅ Recursive directory scanning for configuration files
- ✅ Automatic configuration validation
- ✅ Smart naming from directory structure
- ✅ Backup creation before switching
- ✅ Rich console output with colors
- ✅ Cross-platform support
- ✅ Codex sync: upserts `[mcp_servers.*]` from the active config

## Requirements

- Python ≥ 3.12
- typer ≥ 0.12.0
- pydantic ≥ 2.7.0
- rich ≥ 13.0.0

## Development

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_config.py -v

# Run with coverage
uv run pytest tests/ --cov=mcp_switcher
```

### Type Checking

```bash
# Install development dependencies
uv sync --dev

# Run type checking (if pyright is available)
pyright src/
```
