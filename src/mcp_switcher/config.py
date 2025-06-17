import json
from pathlib import Path
from typing import Union

from mcp_switcher import models


CONFIG_FILE = Path.home() / ".mcp-switch-config.json"


def load_config() -> Union[models.AppConfig, models.ConfigError]:
    """
    Load the application configuration from the config file.
    
    Returns:
        Union[models.AppConfig, models.ConfigError]: The loaded configuration or error.
    """
    if not CONFIG_FILE.exists():
        return models.ConfigError(message="Configuration file not found. Run 'mcp-switch config --dir <path>' first.")
    
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        
        return models.AppConfig(**data)
    except (json.JSONDecodeError, ValueError) as e:
        return models.ConfigError(message=f"Invalid configuration file: {e}")
    except Exception as e:
        return models.ConfigError(message=f"Failed to load configuration: {e}")


def save_config(config: models.AppConfig) -> Union[bool, models.ConfigError]:
    """
    Save the application configuration to the config file.
    
    Args:
        config (models.AppConfig): The configuration to save.
    
    Returns:
        Union[bool, models.ConfigError]: True if successful, or error.
    """
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config.model_dump(mode="json"), f, indent=2, default=str)
        
        return True
    except Exception as e:
        return models.ConfigError(message=f"Failed to save configuration: {e}")


def get_config_files(configs_dir: Path) -> Union[list[models.ConfigInfo], models.ConfigError]:
    """
    Get all JSON configuration files with valid MCP spec in the specified directory.
    Searches recursively and uses the first unique directory name in the path as the config name.
    
    Args:
        configs_dir (Path): Directory to search for config files.
    
    Returns:
        Union[list[models.ConfigInfo], models.ConfigError]: List of config files or error.
    """
    if not configs_dir.exists():
        return models.ConfigError(message=f"Configs directory does not exist: {configs_dir}")
    
    if not configs_dir.is_dir():
        return models.ConfigError(message=f"Path is not a directory: {configs_dir}")
    
    try:
        from mcp_switcher.switcher import validate_config_file
        
        config_files = []
        used_names = set()
        
        for json_file in configs_dir.rglob("*.json"):
            if json_file.is_file():
                # Validate that this is a proper MCP config file
                validation_result = validate_config_file(json_file)
                if isinstance(validation_result, models.ValidationError):
                    continue  # Skip invalid files
                
                # Extract unique name from directory structure
                relative_path = json_file.relative_to(configs_dir)
                name = _extract_unique_name(relative_path, used_names)
                used_names.add(name)
                
                description = _extract_description(json_file)
                
                config_files.append(models.ConfigInfo(
                    name=name,
                    path=json_file,
                    description=description
                ))
        
        return sorted(config_files, key=lambda x: x.name)
    except Exception as e:
        return models.ConfigError(message=f"Failed to scan configs directory: {e}")


def _extract_unique_name(relative_path: Path, used_names: set) -> str:
    """
    Extract a unique name from the directory structure, using the first unique directory name.
    
    Args:
        relative_path (Path): Relative path from configs directory to the JSON file.
        used_names (set): Set of already used names to ensure uniqueness.
    
    Returns:
        str: A unique name for the configuration.
    """
    # Start with the directory parts (excluding the file)
    path_parts = relative_path.parts[:-1]  # Remove filename
    
    # If no directory structure, use filename without extension
    if not path_parts:
        base_name = relative_path.stem
        if base_name not in used_names:
            return base_name
        # If base name is used, add numeric suffix
        counter = 1
        while f"{base_name}_{counter}" in used_names:
            counter += 1
        return f"{base_name}_{counter}"
    
    # Try each directory name from first to last
    for part in path_parts:
        if part not in used_names:
            return part
    
    # If all directory names are used, try combinations
    for i in range(len(path_parts)):
        for j in range(i + 1, len(path_parts) + 1):
            candidate = "_".join(path_parts[i:j])
            if candidate not in used_names:
                return candidate
    
    # Last resort: use full path with underscores and add counter if needed
    full_path_name = str(relative_path.with_suffix("")).replace("/", "_").replace("\\", "_")
    if full_path_name not in used_names:
        return full_path_name
    
    counter = 1
    while f"{full_path_name}_{counter}" in used_names:
        counter += 1
    return f"{full_path_name}_{counter}"


def _extract_description(config_path: Path) -> str:
    """
    Extract description from config file by looking at server names.
    
    Args:
        config_path (Path): Path to the config file.
    
    Returns:
        str: Description of the config.
    """
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        
        if "mcpServers" in data and isinstance(data["mcpServers"], dict):
            servers = list(data["mcpServers"].keys())
            if servers:
                return f"Includes: {', '.join(servers[:3])}"
        
        return "MCP configuration"
    except Exception:
        return "Configuration file"