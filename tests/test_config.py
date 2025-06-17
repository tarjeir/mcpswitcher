import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_switcher import models
from mcp_switcher.config import (
    _extract_description,
    _extract_unique_name,
    get_config_files,
    load_config,
    save_config,
)


class TestExtractUniqueName:
    """Test the unique name extraction logic."""
    
    def test_single_directory(self):
        """Test extraction from single directory structure."""
        path = Path("project/config.json")
        used_names = set()
        result = _extract_unique_name(path, used_names)
        assert result == "project"
    
    def test_multiple_directories_first_unique(self):
        """Test extraction when first directory is unique."""
        path = Path("project/subdir/config.json")
        used_names = set()
        result = _extract_unique_name(path, used_names)
        assert result == "project"
    
    def test_multiple_directories_second_unique(self):
        """Test extraction when first directory is taken."""
        path = Path("project/subdir/config.json")
        used_names = {"project"}
        result = _extract_unique_name(path, used_names)
        assert result == "subdir"
    
    def test_all_directories_taken_uses_combination(self):
        """Test fallback to directory combinations."""
        path = Path("project/subdir/config.json")
        used_names = {"project", "subdir"}
        result = _extract_unique_name(path, used_names)
        assert result == "project_subdir"
    
    def test_no_directories_uses_filename(self):
        """Test fallback to filename when no directories."""
        path = Path("config.json")
        used_names = set()
        result = _extract_unique_name(path, used_names)
        assert result == "config"
    
    def test_filename_taken_adds_counter(self):
        """Test adding counter when filename is taken."""
        path = Path("config.json")
        used_names = {"config"}
        result = _extract_unique_name(path, used_names)
        assert result == "config_1"
    
    def test_deep_directory_structure(self):
        """Test with deep directory structure."""
        path = Path("a/b/c/d/config.json")
        used_names = {"a", "b"}
        result = _extract_unique_name(path, used_names)
        assert result == "c"


class TestExtractDescription:
    """Test config file description extraction."""
    
    def test_valid_mcp_config_with_servers(self):
        """Test description extraction from valid config with servers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "mcpServers": {
                    "server1": {"command": "test"},
                    "server2": {"command": "test"},
                    "server3": {"command": "test"},
                    "server4": {"command": "test"}
                }
            }
            json.dump(config, f)
            f.flush()
            
            result = _extract_description(Path(f.name))
            assert result == "Includes: server1, server2, server3"
            
            Path(f.name).unlink()
    
    def test_config_without_servers(self):
        """Test description for config without mcpServers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {"other": "data"}
            json.dump(config, f)
            f.flush()
            
            result = _extract_description(Path(f.name))
            assert result == "MCP configuration"
            
            Path(f.name).unlink()
    
    def test_invalid_json_file(self):
        """Test description for invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json {")
            f.flush()
            
            result = _extract_description(Path(f.name))
            assert result == "Configuration file"
            
            Path(f.name).unlink()


class TestGetConfigFiles:
    """Test the main config file discovery functionality."""
    
    def setup_method(self):
        """Set up temporary directory structure for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.configs_dir = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_config_file(self, relative_path: str, content: dict):
        """Helper to create config files in test directory."""
        file_path = self.configs_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(content, f)
        return file_path
    
    def test_valid_mcp_configs_found(self):
        """Test that valid MCP configs are found and named correctly."""
        # Create valid MCP configs
        self.create_config_file("project1/config.json", {
            "mcpServers": {"server1": {"command": "test"}}
        })
        self.create_config_file("project2/setup.json", {
            "mcpServers": {"server2": {"command": "test"}}
        })
        
        result = get_config_files(self.configs_dir)
        
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Check names are extracted correctly
        names = {config.name for config in result}
        assert names == {"project1", "project2"}
    
    def test_invalid_configs_filtered_out(self):
        """Test that invalid configs are filtered out."""
        # Create valid configs
        self.create_config_file("valid1/config.json", {
            "mcpServers": {"server1": {"command": "test"}}
        })
        self.create_config_file("valid2/config.json", {"other": "data"})  # Valid JSON without mcpServers
        
        # Create invalid configs - these should be filtered out
        self.create_config_file("invalid1/config.json", {
            "mcpServers": "not an object"  # Invalid mcpServers structure
        })
        
        invalid2_path = self.configs_dir / "invalid2.json"
        with open(invalid2_path, 'w') as f:
            f.write("invalid json {")  # Invalid JSON
        
        result = get_config_files(self.configs_dir)
        
        assert isinstance(result, list)
        # Only the valid configs should be included
        assert len(result) == 2
        names = {config.name for config in result}
        assert names == {"valid1", "valid2"}
    
    def test_recursive_search(self):
        """Test that configs are found recursively."""
        self.create_config_file("a/b/c/deep.json", {
            "mcpServers": {"deep_server": {"command": "test"}}
        })
        
        result = get_config_files(self.configs_dir)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "a"
    
    def test_unique_naming_with_conflicts(self):
        """Test unique naming when directory names conflict."""
        self.create_config_file("project/config1.json", {
            "mcpServers": {"server1": {"command": "test"}}
        })
        self.create_config_file("project/subdir/config2.json", {
            "mcpServers": {"server2": {"command": "test"}}
        })
        
        result = get_config_files(self.configs_dir)
        
        assert isinstance(result, list)
        assert len(result) == 2
        
        names = {config.name for config in result}
        # First one gets "project", second gets "subdir"
        assert names == {"project", "subdir"}
    
    def test_nonexistent_directory_returns_error(self):
        """Test error handling for nonexistent directory."""
        nonexistent = Path("/nonexistent/directory")
        result = get_config_files(nonexistent)
        
        assert isinstance(result, models.ConfigError)
        assert "does not exist" in result.message
    
    def test_file_instead_of_directory_returns_error(self):
        """Test error handling when path is a file, not directory."""
        file_path = self.configs_dir / "file.txt"
        file_path.write_text("test")
        
        result = get_config_files(file_path)
        
        assert isinstance(result, models.ConfigError)
        assert "not a directory" in result.message


class TestConfigSaveLoad:
    """Test config file save/load functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        # Create test config
        config = models.AppConfig(
            configs_directory=Path("/test/configs"),
            target_client=models.MCPClient.CLAUDE_DESKTOP
        )
        
        # Test save
        with patch('mcp_switcher.config.CONFIG_FILE', self.config_file):
            save_result = save_config(config)
            assert save_result is True
            assert self.config_file.exists()
            
            # Test load
            load_result = load_config()
            
            assert isinstance(load_result, models.AppConfig)
            assert load_result.configs_directory == config.configs_directory
            assert load_result.target_client == config.target_client
    
    @patch('mcp_switcher.config.CONFIG_FILE')
    def test_load_nonexistent_config_returns_error(self, mock_config_file):
        """Test loading nonexistent config returns error."""
        mock_config_file.exists.return_value = False
        
        result = load_config()
        
        assert isinstance(result, models.ConfigError)
        assert "not found" in result.message


if __name__ == "__main__":
    pytest.main([__file__])