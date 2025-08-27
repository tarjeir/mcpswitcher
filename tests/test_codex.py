import re
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_switcher import models
from mcp_switcher.codex import update_codex_from_active


def write_active(path: Path, servers: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump({"mcpServers": servers}, f)


class TestCodexSingleServer:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.codex_home = self.tmpdir / "home"
        self.codex_home.mkdir(parents=True, exist_ok=True)
        self.active = self.tmpdir / "active.json"

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def make_app_config(self) -> models.AppConfig:
        # configs_directory is unused by update_codex_from_active
        return models.AppConfig(configs_directory=self.tmpdir, target_client=models.MCPClient.CLAUDE_DESKTOP)

    def test_creates_file_and_writes_block(self):
        servers = {
            "myMCP": {
                "command": "npx",
                "args": ["-y", "@codex-data/codex-mcp"],
                "env": {"CODEX_API_KEY": "abc123"},
            }
        }
        write_active(self.active, servers)

        app_config = self.make_app_config()
        with patch.object(type(app_config), "get_target_path", return_value=self.active):
            with patch("pathlib.Path.home", return_value=self.codex_home):
                result = update_codex_from_active(app_config)
                assert result is True

                out = (self.codex_home / ".codex" / "config.toml").read_text()
                assert "[mcp_servers.myMCP]" in out
                assert 'command = "npx"' in out
                assert 'args = ["-y", "@codex-data/codex-mcp"]' in out
                assert 'env = { "CODEX_API_KEY" = "abc123" }' in out

    def test_preserves_unrelated_keys_and_replaces_existing_block(self):
        # Seed an existing TOML with unrelated keys and an old block
        codex_file = self.codex_home / ".codex" / "config.toml"
        codex_file.parent.mkdir(parents=True, exist_ok=True)
        codex_file.write_text(
            "projects = { \"/x\" = { trust_level = \"trusted\" } }\n"
            "[mcp_servers.myMCP]\n"
            "command = \"old\"\n"
        )

        servers = {"myMCP": {"command": "npx", "args": ["-y"], "env": {}}}
        write_active(self.active, servers)

        app_config = self.make_app_config()
        with patch.object(type(app_config), "get_target_path", return_value=self.active):
            with patch("pathlib.Path.home", return_value=self.codex_home):
                result = update_codex_from_active(app_config)
                assert result is True

                out = codex_file.read_text()
                # Unrelated key preserved
                assert out.startswith("projects = ")
                # Old block replaced by new command
                assert "[mcp_servers.myMCP]" in out
                assert 'command = "npx"' in out
                assert 'command = "old"' not in out


class TestCodexMultiServer:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.codex_home = self.tmpdir / "home"
        self.codex_home.mkdir(parents=True, exist_ok=True)
        self.active = self.tmpdir / "active.json"

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def make_app_config(self) -> models.AppConfig:
        return models.AppConfig(configs_directory=self.tmpdir, target_client=models.MCPClient.CLAUDE_DESKTOP)

    def test_writes_all_servers(self):
        servers = {
            "s1": {"command": "a", "args": ["1"], "env": {"K": "V"}},
            "s2": {"command": "b"},
            "s3": {"command": "c", "env": {"X": "Y"}},
        }
        write_active(self.active, servers)

        app_config = self.make_app_config()
        with patch.object(type(app_config), "get_target_path", return_value=self.active):
            with patch("pathlib.Path.home", return_value=self.codex_home):
                result = update_codex_from_active(app_config)
                assert result is True
                out = (self.codex_home / ".codex" / "config.toml").read_text()
                for name in servers.keys():
                    assert f"[mcp_servers.{name}]" in out

    def test_missing_command_errors(self):
        servers = {"bad": {"args": ["x"]}}
        write_active(self.active, servers)
        app_config = self.make_app_config()
        with patch.object(type(app_config), "get_target_path", return_value=self.active):
            with patch("pathlib.Path.home", return_value=self.codex_home):
                result = update_codex_from_active(app_config)
                assert isinstance(result, models.SwitchError)
                assert "missing 'command'" in result.message


class TestCodexErrors:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.codex_home = self.tmpdir / "home"
        self.active = self.tmpdir / "active.json"

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def make_app_config(self) -> models.AppConfig:
        return models.AppConfig(configs_directory=self.tmpdir, target_client=models.MCPClient.CLAUDE_DESKTOP)

    def test_no_active_config_file(self):
        app_config = self.make_app_config()
        with patch.object(type(app_config), "get_target_path", return_value=self.active):
            with patch("pathlib.Path.home", return_value=self.codex_home):
                result = update_codex_from_active(app_config)
                assert isinstance(result, models.SwitchError)
                assert "No active configuration" in result.message

    def test_mcpservers_missing(self):
        self.active.write_text("{}")
        app_config = self.make_app_config()
        with patch.object(type(app_config), "get_target_path", return_value=self.active):
            with patch("pathlib.Path.home", return_value=self.codex_home):
                result = update_codex_from_active(app_config)
                assert isinstance(result, models.SwitchError)
                assert "has no 'mcpServers'" in result.message
