import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_switcher import models
from mcp_switcher.switcher import (
    backup_current_config,
    get_current_config,
    switch_config,
    validate_config_file,
)


class TestValidateConfigFile:
    """Test config file validation functionality."""
    
    def test_valid_mcp_config(self):
        """Test validation of valid MCP config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "mcpServers": {
                    "test_server": {
                        "command": "test_command",
                        "args": ["arg1", "arg2"]
                    }
                }
            }
            json.dump(config, f)
            f.flush()
            
            result = validate_config_file(Path(f.name))
            assert result is True
            
            Path(f.name).unlink()
    
    def test_valid_config_without_mcp_servers(self):
        """Test validation of config without mcpServers (should still be valid)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {"other": "data"}
            json.dump(config, f)
            f.flush()
            
            result = validate_config_file(Path(f.name))
            assert result is True
            
            Path(f.name).unlink()
    
    def test_invalid_json(self):
        """Test validation of invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json {")
            f.flush()
            
            result = validate_config_file(Path(f.name))
            assert isinstance(result, models.ValidationError)
            assert "Invalid JSON" in result.message
            
            Path(f.name).unlink()
    
    def test_non_object_json(self):
        """Test validation of JSON that's not an object."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(["array", "not", "object"], f)
            f.flush()
            
            result = validate_config_file(Path(f.name))
            assert isinstance(result, models.ValidationError)
            assert "must contain a JSON object" in result.message
            
            Path(f.name).unlink()
    
    def test_invalid_mcp_servers_structure(self):
        """Test validation of config with invalid mcpServers structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {"mcpServers": "not an object"}
            json.dump(config, f)
            f.flush()
            
            result = validate_config_file(Path(f.name))
            assert isinstance(result, models.ValidationError)
            assert "mcpServers must be an object" in result.message
            
            Path(f.name).unlink()
    
    def test_nonexistent_file(self):
        """Test validation of nonexistent file."""
        result = validate_config_file(Path("/nonexistent/file.json"))
        assert isinstance(result, models.ValidationError)
        assert "does not exist" in result.message


class TestBackupCurrentConfig:
    """Test configuration backup functionality."""
    
    def test_successful_backup(self):
        """Test successful backup creation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"test": "config"}')
            f.flush()
            source_path = Path(f.name)
            
            with patch('mcp_switcher.switcher.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "2023-01-01-12-00-00"
                
                result = backup_current_config(source_path)
                
                assert isinstance(result, Path)
                assert result.name == "backup-2023-01-01-12-00-00.json"
                assert result.exists()
                
                # Verify backup content
                with open(result, 'r') as backup_file:
                    assert backup_file.read() == '{"test": "config"}'
                
                # Clean up
                source_path.unlink()
                result.unlink()
    
    def test_backup_nonexistent_file(self):
        """Test backup of nonexistent file returns error."""
        result = backup_current_config(Path("/nonexistent/file.json"))
        assert isinstance(result, models.SwitchError)
        assert "No current config file to backup" in result.message


class TestSwitchConfig:
    """Test configuration switching functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_valid_config(self, path: Path, content: dict = None):
        """Helper to create a valid config file."""
        if content is None:
            content = {"mcpServers": {"test": {"command": "test"}}}
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(content, f)
        return path
    
    def test_successful_switch_without_existing_target(self):
        """Test successful config switch when no target exists."""
        source = self.create_valid_config(self.temp_path / "source.json")
        target = self.temp_path / "target.json"
        
        result = switch_config(source, target)
        
        assert result is True
        assert target.exists()
        
        # Verify content copied correctly
        with open(target, 'r') as f:
            target_content = json.load(f)
        with open(source, 'r') as f:
            source_content = json.load(f)
        
        assert target_content == source_content
    
    def test_successful_switch_with_existing_target_backup(self):
        """Test successful config switch with backup of existing target."""
        source = self.create_valid_config(self.temp_path / "source.json")
        target = self.create_valid_config(self.temp_path / "target.json", 
                                         {"mcpServers": {"old": {"command": "old"}}})
        
        with patch('mcp_switcher.switcher.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-01-01-12-00-00"
            
            result = switch_config(source, target)
            
            assert result is True
            
            # Verify backup was created
            backup_path = target.parent / "backup-2023-01-01-12-00-00.json"
            assert backup_path.exists()
            
            # Verify backup contains old content
            with open(backup_path, 'r') as f:
                backup_content = json.load(f)
            assert backup_content["mcpServers"]["old"]["command"] == "old"
            
            # Verify target has new content
            with open(target, 'r') as f:
                target_content = json.load(f)
            assert "test" in target_content["mcpServers"]
    
    def test_switch_invalid_source_config(self):
        """Test switch with invalid source config."""
        source = self.temp_path / "invalid.json"
        with open(source, 'w') as f:
            f.write("invalid json {")
        
        target = self.temp_path / "target.json"
        
        result = switch_config(source, target)
        
        assert isinstance(result, models.SwitchError)
        assert "Config validation failed" in result.message
    
    def test_switch_creates_target_directory(self):
        """Test that switch creates target directory if needed."""
        source = self.create_valid_config(self.temp_path / "source.json")
        target = self.temp_path / "subdir" / "target.json"
        
        result = switch_config(source, target)
        
        assert result is True
        assert target.exists()
        assert target.parent.exists()


class TestGetCurrentConfig:
    """Test current configuration detection functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.configs_dir = self.temp_path / "configs"
        self.configs_dir.mkdir()
        self.target_path = self.temp_path / "target.json"
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_config(self, path: Path, content: dict):
        """Helper to create config file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(content, f)
        return path
    
    def test_current_config_found_by_content_match(self):
        """Test finding current config by matching content."""
        config_content = {"mcpServers": {"test": {"command": "test"}}}
        
        # Create config in configs directory
        config_path = self.create_config(self.configs_dir / "test.json", config_content)
        
        # Create matching target
        self.create_config(self.target_path, config_content)
        
        # Create app config
        app_config = models.AppConfig(
            configs_directory=self.configs_dir,
            target_client=models.MCPClient.CLAUDE_DESKTOP
        )
        
        with patch.object(type(app_config), 'get_target_path', return_value=self.target_path):
            with patch('mcp_switcher.switcher._get_config_files_from_app_config') as mock_get_configs:
                mock_get_configs.return_value = [
                    models.ConfigInfo(name="test", path=config_path, description="Test config")
                ]
                
                result = get_current_config(app_config)
                
                assert isinstance(result, models.ConfigInfo)
                assert result.name == "test"
                assert result.path == config_path
    
    def test_current_config_no_target_file(self):
        """Test when no target config file exists."""
        app_config = models.AppConfig(
            configs_directory=self.configs_dir,
            target_client=models.MCPClient.CLAUDE_DESKTOP
        )
        
        with patch.object(type(app_config), 'get_target_path', return_value=self.target_path):
            result = get_current_config(app_config)
            
            assert isinstance(result, models.SwitchError)
            assert "No active configuration found" in result.message
    
    def test_current_config_unknown_source(self):
        """Test when target exists but source is unknown."""
        unknown_content = {"mcpServers": {"unknown": {"command": "unknown"}}}
        self.create_config(self.target_path, unknown_content)
        
        app_config = models.AppConfig(
            configs_directory=self.configs_dir,
            target_client=models.MCPClient.CLAUDE_DESKTOP
        )
        
        with patch.object(type(app_config), 'get_target_path', return_value=self.target_path):
            with patch('mcp_switcher.switcher._get_config_files_from_app_config') as mock_get_configs:
                mock_get_configs.return_value = []
                
                result = get_current_config(app_config)
                
                assert isinstance(result, models.ConfigInfo)
                assert result.name == "unknown"
                assert result.description == "Active configuration (source unknown)"


if __name__ == "__main__":
    pytest.main([__file__])