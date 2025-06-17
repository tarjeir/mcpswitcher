import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Union

from mcp_switcher import models


def validate_config_file(config_path: Path) -> Union[bool, models.ValidationError]:
    """
    Validate that a config file contains valid JSON and basic MCP structure.
    
    Args:
        config_path (Path): Path to the config file to validate.
    
    Returns:
        Union[bool, models.ValidationError]: True if valid, or validation error.
    """
    if not config_path.exists():
        return models.ValidationError(message=f"Config file does not exist: {config_path}")
    
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            return models.ValidationError(message="Config file must contain a JSON object")
        
        if "mcpServers" in data and not isinstance(data["mcpServers"], dict):
            return models.ValidationError(message="mcpServers must be an object")
        
        return True
    except json.JSONDecodeError as e:
        return models.ValidationError(message=f"Invalid JSON: {e}")
    except Exception as e:
        return models.ValidationError(message=f"Failed to read config file: {e}")


def backup_current_config(target_path: Path) -> Union[Path, models.SwitchError]:
    """
    Create a backup of the current configuration file.
    
    Args:
        target_path (Path): Path to the current config file.
    
    Returns:
        Union[Path, models.SwitchError]: Path to backup file or error.
    """
    if not target_path.exists():
        return models.SwitchError(message="No current config file to backup")
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        backup_path = target_path.parent / f"backup-{timestamp}.json"
        
        shutil.copy2(target_path, backup_path)
        return backup_path
    except Exception as e:
        return models.SwitchError(message=f"Failed to create backup: {e}")


def switch_config(source_path: Path, target_path: Path) -> Union[bool, models.SwitchError]:
    """
    Switch to a new configuration by copying the source to target location.
    
    Args:
        source_path (Path): Path to the new config file.
        target_path (Path): Path where the config should be copied.
    
    Returns:
        Union[bool, models.SwitchError]: True if successful, or switch error.
    """
    validation_result = validate_config_file(source_path)
    match validation_result:
        case models.ValidationError(message=msg):
            return models.SwitchError(message=f"Config validation failed: {msg}")
        case bool():
            pass
        case _ as unreachable:
            assert False, f"Unexpected validation result: {unreachable}"
    
    if target_path.exists():
        backup_result = backup_current_config(target_path)
        match backup_result:
            case models.SwitchError() as error:
                return error
            case Path():
                pass
            case _ as unreachable:
                assert False, f"Unexpected backup result: {unreachable}"
    
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        return True
    except Exception as e:
        return models.SwitchError(message=f"Failed to copy config file: {e}")


def get_current_config(app_config: models.AppConfig) -> Union[models.ConfigInfo, models.SwitchError]:
    """
    Determine which configuration is currently active.
    
    Args:
        app_config (models.AppConfig): Application configuration.
    
    Returns:
        Union[models.ConfigInfo, models.SwitchError]: Current config info or error.
    """
    target_path = app_config.get_target_path()
    
    if not target_path.exists():
        return models.SwitchError(message="No active configuration found")
    
    configs_result = _get_config_files_from_app_config(app_config)
    match configs_result:
        case models.ConfigError(message=msg):
            return models.SwitchError(message=f"Failed to scan configs: {msg}")
        case list() as configs:
            pass
        case _ as unreachable:
            assert False, f"Unexpected configs result: {unreachable}"
    
    try:
        with open(target_path, "r") as f:
            current_data = json.load(f)
        
        for config_info in configs:
            try:
                with open(config_info.path, "r") as f:
                    config_data = json.load(f)
                
                if config_data == current_data:
                    return config_info
            except Exception:
                continue
        
        return models.ConfigInfo(
            name="unknown",
            path=target_path,
            description="Active configuration (source unknown)"
        )
    except Exception as e:
        return models.SwitchError(message=f"Failed to read current config: {e}")


def _get_config_files_from_app_config(app_config: models.AppConfig) -> Union[list[models.ConfigInfo], models.ConfigError]:
    """
    Helper to get config files using app config directory.
    
    Args:
        app_config (models.AppConfig): Application configuration.
    
    Returns:
        Union[list[models.ConfigInfo], models.ConfigError]: Config files or error.
    """
    from mcp_switcher.config import get_config_files
    return get_config_files(app_config.configs_directory)