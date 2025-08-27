from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_switcher.models import AppConfig, MCPClient, ConfigInfo


class TestMCPClient:
    """Test MCPClient enum functionality."""
    
    def test_client_values(self):
        """Test that client enum has correct values."""
        assert MCPClient.CLAUDE_DESKTOP == "claude-desktop"
        assert MCPClient.VS_CODE == "vscode"
        assert MCPClient.CURSOR == "cursor"
    
    def test_client_creation(self):
        """Test creating MCPClient from string."""
        assert MCPClient("claude-desktop") == MCPClient.CLAUDE_DESKTOP
        assert MCPClient("vscode") == MCPClient.VS_CODE
        assert MCPClient("cursor") == MCPClient.CURSOR


class TestAppConfig:
    """Test AppConfig model functionality."""
    
    def test_default_values(self):
        """Test default values in AppConfig."""
        config = AppConfig(configs_directory=Path("/test"))
        assert config.target_client == MCPClient.CLAUDE_DESKTOP
        assert config.configs_directory == Path("/test")
    
    def test_target_path_claude_desktop_darwin(self):
        """Test target path for Claude Desktop on macOS."""
        config = AppConfig(
            configs_directory=Path("/test"),
            target_client=MCPClient.CLAUDE_DESKTOP
        )
        
        with patch('platform.system', return_value='Darwin'):
            target_path = config.get_target_path()
            expected = Path.home() / ".config" / "claude-desktop" / "claude_desktop_config.json"
            assert target_path == expected
    
    def test_target_path_claude_desktop_linux(self):
        """Test target path for Claude Desktop on Linux."""
        config = AppConfig(
            configs_directory=Path("/test"),
            target_client=MCPClient.CLAUDE_DESKTOP
        )
        
        with patch('platform.system', return_value='Linux'):
            target_path = config.get_target_path()
            expected = Path.home() / ".config" / "claude-desktop" / "claude_desktop_config.json"
            assert target_path == expected
    
    def test_target_path_claude_desktop_windows(self):
        """Test target path for Claude Desktop on Windows."""
        config = AppConfig(
            configs_directory=Path("/test"),
            target_client=MCPClient.CLAUDE_DESKTOP
        )
        
        with patch('platform.system', return_value='Windows'):
            with patch('os.getenv', return_value='C:\\Users\\Test\\AppData\\Roaming'):
                target_path = config.get_target_path()
                expected = Path("C:\\Users\\Test\\AppData\\Roaming") / "Claude" / "claude_desktop_config.json"
                assert target_path == expected
    
    def test_target_path_claude_desktop_unknown_system(self):
        """Test target path for Claude Desktop on unknown system."""
        config = AppConfig(
            configs_directory=Path("/test"),
            target_client=MCPClient.CLAUDE_DESKTOP
        )
        
        with patch('platform.system', return_value='UnknownOS'):
            target_path = config.get_target_path()
            expected = Path.home() / ".config" / "claude-desktop" / "claude_desktop_config.json"
            assert target_path == expected
    
    def test_target_path_vscode(self):
        """Test target path for VS Code."""
        config = AppConfig(
            configs_directory=Path("/test"),
            target_client=MCPClient.VS_CODE
        )
        
        target_path = config.get_target_path()
        expected = Path.cwd() / ".vscode" / "mcp.json"
        assert target_path == expected
    
    def test_target_path_cursor(self):
        """Test target path for Cursor."""
        config = AppConfig(
            configs_directory=Path("/test"),
            target_client=MCPClient.CURSOR
        )
        
        target_path = config.get_target_path()
        expected = Path.home() / ".cursor" / "mcp.json"
        assert target_path == expected
    
    def test_model_serialization(self):
        """Test that model can be serialized/deserialized."""
        original = AppConfig(
            configs_directory=Path("/test/configs"),
            target_client=MCPClient.VS_CODE
        )
        
        # Test model_dump
        data = original.model_dump(mode="json")
        assert data["configs_directory"] == "/test/configs"
        assert data["target_client"] == "vscode"
        
        # Test reconstruction
        reconstructed = AppConfig(**data)
        assert reconstructed.configs_directory == original.configs_directory
        assert reconstructed.target_client == original.target_client


class TestConfigInfo:
    """Test ConfigInfo model functionality."""
    
    def test_basic_creation(self):
        """Test basic ConfigInfo creation."""
        config_info = ConfigInfo(
            name="test_config",
            path=Path("/test/config.json")
        )
        
        assert config_info.name == "test_config"
        assert config_info.path == Path("/test/config.json")
        assert config_info.description == ""  # Default empty description
    
    def test_with_description(self):
        """Test ConfigInfo with description."""
        config_info = ConfigInfo(
            name="test_config",
            path=Path("/test/config.json"),
            description="Test configuration file"
        )
        
        assert config_info.description == "Test configuration file"
    
    def test_model_serialization(self):
        """Test ConfigInfo serialization."""
        config_info = ConfigInfo(
            name="test_config",
            path=Path("/test/config.json"),
            description="Test config"
        )
        
        data = config_info.model_dump(mode="json")
        assert data["name"] == "test_config"
        assert data["path"] == "/test/config.json"
        assert data["description"] == "Test config"


class TestErrorModels:
    """Test error model functionality."""
    
    def test_switch_error(self):
        """Test SwitchError model."""
        from mcp_switcher.models import SwitchError
        
        error = SwitchError(message="Test error message")
        assert error.message == "Test error message"
    
    def test_config_error(self):
        """Test ConfigError model."""
        from mcp_switcher.models import ConfigError
        
        error = ConfigError(message="Config error message")
        assert error.message == "Config error message"
    
    def test_validation_error(self):
        """Test ValidationError model."""
        from mcp_switcher.models import ValidationError
        
        error = ValidationError(message="Validation error message")
        assert error.message == "Validation error message"


if __name__ == "__main__":
    pytest.main([__file__])
