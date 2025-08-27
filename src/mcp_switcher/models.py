from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class MCPClient(str, Enum):
    CLAUDE_DESKTOP = "claude-desktop"
    VS_CODE = "vscode"
    CURSOR = "cursor"


class AppConfig(BaseModel):
    configs_directory: Path
    target_client: MCPClient = MCPClient.CLAUDE_DESKTOP
    
    def get_target_path(self) -> Path:
        """Get the target configuration file path for the selected client."""
        match self.target_client:
            case MCPClient.CLAUDE_DESKTOP:
                return self._get_claude_desktop_path()
            case MCPClient.VS_CODE:
                return Path.cwd() / ".vscode" / "mcp.json"
            case MCPClient.CURSOR:
                return Path.home() / ".cursor" / "mcp.json"
    
    def _get_claude_desktop_path(self) -> Path:
        """Get Claude Desktop config path based on platform."""
        import platform
        
        system = platform.system()
        match system:
            case "Darwin":
                # Align macOS path with Linux for Claude Desktop config
                return Path.home() / ".config" / "claude-desktop" / "claude_desktop_config.json"
            case "Linux":
                return Path.home() / ".config" / "claude-desktop" / "claude_desktop_config.json"
            case "Windows":
                import os
                appdata = os.getenv("APPDATA", "")
                return Path(appdata) / "Claude" / "claude_desktop_config.json"
            case _:
                return Path.home() / ".config" / "claude-desktop" / "claude_desktop_config.json"


class ConfigInfo(BaseModel):
    name: str
    path: Path
    description: str = ""


class SwitchError(BaseModel):
    message: str


class ConfigError(BaseModel):
    message: str


class ValidationError(BaseModel):
    message: str
