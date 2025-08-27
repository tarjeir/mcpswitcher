import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple, Union

from mcp_switcher import models


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_server_block(name: str, server: Dict[str, Any]) -> str:
    lines: list[str] = [f"[mcp_servers.{name}]"]
    command = str(server.get("command", "")).strip()
    if not command:
        # Minimal requirement for codex block
        raise ValueError("Selected server is missing 'command'")
    lines.append(f"command = \"{_toml_escape(command)}\"")

    args = server.get("args")
    if isinstance(args, list) and args:
        arg_items = ", ".join(f'"{_toml_escape(str(a))}"' for a in args)
        lines.append(f"args = [{arg_items}]")

    env = server.get("env")
    if isinstance(env, dict) and env:
        env_items = ", ".join(
            f'"{_toml_escape(str(k))}" = "{_toml_escape(str(v))}"' for k, v in env.items()
        )
        lines.append(f"env = {{ {env_items} }}")

    return "\n".join(lines) + "\n"


def _extract_active_servers(target_path: Path) -> Union[Dict[str, Dict[str, Any]], models.SwitchError]:
    if not target_path.exists():
        return models.SwitchError(message="No active configuration found (target file missing)")
    try:
        with target_path.open("r") as f:
            data = json.load(f)
    except Exception as e:
        return models.SwitchError(message=f"Failed to read active config: {e}")

    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return models.SwitchError(message="Active config has no 'mcpServers' object")

    if len(servers) == 0:
        return models.SwitchError(message="Active config contains zero MCP servers")

    # Filter to only dict-shaped servers
    valid: Dict[str, Dict[str, Any]] = {}
    for k, v in servers.items():
        if isinstance(v, dict):
            valid[k] = v
    if not valid:
        return models.SwitchError(message="Active config servers are not objects")
    return valid


def _upsert_codex_config(block: str, server_name: str, codex_config: Path) -> Union[bool, models.SwitchError]:
    try:
        codex_config.parent.mkdir(parents=True, exist_ok=True)
        existing = codex_config.read_text() if codex_config.exists() else ""

        # Remove existing block for this server, if present
        pattern = rf"(?ms)^\[mcp_servers\.{re.escape(server_name)}\][\s\S]*?(?=^\[|\Z)"
        new_text = re.sub(pattern, "", existing)

        # Ensure neat separation
        if new_text and not new_text.endswith("\n\n"):
            if new_text.endswith("\n"):
                new_text += "\n"
            else:
                new_text += "\n\n"

        new_text += block
        if not new_text.endswith("\n"):
            new_text += "\n"

        codex_config.write_text(new_text)
        return True
    except Exception as e:
        return models.SwitchError(message=f"Failed to update Codex config: {e}")


def _upsert_codex_config_multi(blocks: Dict[str, str], codex_config: Path) -> Union[bool, models.SwitchError]:
    try:
        codex_config.parent.mkdir(parents=True, exist_ok=True)
        existing = codex_config.read_text() if codex_config.exists() else ""

        # Remove existing blocks for all these servers first
        new_text = existing
        for server_name in blocks.keys():
            pattern = rf"(?ms)^\[mcp_servers\.{re.escape(server_name)}\][\s\S]*?(?=^\[|\Z)"
            new_text = re.sub(pattern, "", new_text)

        # Ensure neat separation
        if new_text and not new_text.endswith("\n\n"):
            if new_text.endswith("\n"):
                new_text += "\n"
            else:
                new_text += "\n\n"

        # Append each block in deterministic order
        for name in sorted(blocks.keys()):
            new_text += blocks[name]
            if not new_text.endswith("\n"):
                new_text += "\n"

        codex_config.write_text(new_text)
        return True
    except Exception as e:
        return models.SwitchError(message=f"Failed to update Codex config: {e}")


def update_codex_from_active(app_config: models.AppConfig) -> Union[bool, models.SwitchError]:
    """Upsert ~/.codex/config.toml with the single active MCP server.

    - Reads the current target client's config (as selected by mcpswitcher).
    - Requires exactly one server to be present to avoid ambiguity.
    - Non-destructively upserts [mcp_servers.<name>] in Codex config.
    """
    target = app_config.get_target_path()
    active = _extract_active_servers(target)
    match active:
        case models.SwitchError() as err:
            return err
        case dict() as servers:
            pass
        case _ as unreachable:
            assert False, f"Unexpected active servers result: {unreachable}"

    blocks: Dict[str, str] = {}
    try:
        for name, server in servers.items():
            blocks[name] = _build_server_block(name, server)
    except ValueError as e:
        return models.SwitchError(message=str(e))

    codex_config = Path.home() / ".codex" / "config.toml"
    return _upsert_codex_config_multi(blocks, codex_config)
