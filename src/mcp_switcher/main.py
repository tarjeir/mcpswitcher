from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from mcp_switcher import models
from mcp_switcher.config import get_config_files, load_config, save_config
from mcp_switcher.switcher import get_current_config, switch_config
from mcp_switcher.codex import update_codex_from_active

app = typer.Typer(help="Simple MCP configuration switcher CLI tool")
console = Console()


@app.command()
def list_configs():
    """List all available MCP configuration files."""
    config_result = load_config()
    match config_result:
        case models.ConfigError(message=msg):
            console.print(f"[red]Error: {msg}[/red]")
            raise typer.Exit(1)
        case models.AppConfig() as config:
            pass
        case _ as unreachable:
            assert False, f"Unexpected config result: {unreachable}"
    
    configs_result = get_config_files(config.configs_directory)
    match configs_result:
        case models.ConfigError(message=msg):
            console.print(f"[red]Error: {msg}[/red]")
            raise typer.Exit(1)
        case list() as configs:
            pass
        case _ as unreachable:
            assert False, f"Unexpected configs result: {unreachable}"
    
    if not configs:
        console.print(f"[yellow]No configuration files found in {config.configs_directory}[/yellow]")
        return
    
    console.print(f"Available configurations in [blue]{config.configs_directory}[/blue]:")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    
    for config_info in configs:
        table.add_row(config_info.name, config_info.description)
    
    console.print(table)


@app.command()
def use(config_name: str):
    """Switch to a specific configuration."""
    app_config_result = load_config()
    match app_config_result:
        case models.ConfigError(message=msg):
            console.print(f"[red]Error: {msg}[/red]")
            raise typer.Exit(1)
        case models.AppConfig() as app_config:
            pass
        case _ as unreachable:
            assert False, f"Unexpected app config result: {unreachable}"
    
    configs_result = get_config_files(app_config.configs_directory)
    match configs_result:
        case models.ConfigError(message=msg):
            console.print(f"[red]Error: {msg}[/red]")
            raise typer.Exit(1)
        case list() as configs:
            pass
        case _ as unreachable:
            assert False, f"Unexpected configs result: {unreachable}"
    
    target_config = None
    for config_info in configs:
        if config_info.name == config_name:
            target_config = config_info
            break
    
    if not target_config:
        console.print(f"[red]Configuration '{config_name}' not found[/red]")
        console.print("Available configurations:")
        for config_info in configs:
            console.print(f"  {config_info.name}")
        raise typer.Exit(1)
    
    target_path = app_config.get_target_path()
    
    if target_path.exists():
        console.print(f"[yellow]Current configuration will be backed up[/yellow]")
    
    switch_result = switch_config(target_config.path, target_path)
    match switch_result:
        case models.SwitchError(message=msg):
            console.print(f"[red]Failed to switch configuration: {msg}[/red]")
            raise typer.Exit(1)
        case bool():
            pass
        case _ as unreachable:
            assert False, f"Unexpected switch result: {unreachable}"
    
    console.print(f"[green]✓ Successfully switched to {config_name}[/green]")
    console.print(f"[green]✓ Configuration applied to {target_path}[/green]")
    console.print("[yellow]Restart your MCP client to load the new configuration[/yellow]")


@app.command()
def current():
    """Show the currently active configuration."""
    config_result = load_config()
    match config_result:
        case models.ConfigError(message=msg):
            console.print(f"[red]Error: {msg}[/red]")
            raise typer.Exit(1)
        case models.AppConfig() as config:
            pass
        case _ as unreachable:
            assert False, f"Unexpected config result: {unreachable}"
    
    current_result = get_current_config(config)
    match current_result:
        case models.SwitchError(message=msg):
            console.print(f"[red]Error: {msg}[/red]")
            raise typer.Exit(1)
        case models.ConfigInfo() as current_config:
            pass
        case _ as unreachable:
            assert False, f"Unexpected current result: {unreachable}"
    
    console.print(f"Currently using: [cyan]{current_config.name}[/cyan]")
    console.print(f"Source: [blue]{current_config.path}[/blue]")
    console.print(f"Target: [blue]{config.get_target_path()}[/blue]")
    console.print(f"Description: {current_config.description}")


@app.command()
def config(
    dir: Annotated[Optional[Path], typer.Option("--dir", help="Set the configurations directory")] = None,
    show: Annotated[bool, typer.Option("--show", help="Show current configuration settings")] = False,
    client: Annotated[Optional[str], typer.Option("--client", help="Set the target MCP client or update Codex (claude-desktop, vscode, cursor, codex)")] = None
):
    """Configure the MCP switcher settings."""
    if show:
        config_result = load_config()
        match config_result:
            case models.ConfigError(message=msg):
                console.print(f"[red]Error: {msg}[/red]")
                raise typer.Exit(1)
            case models.AppConfig() as app_config:
                pass
            case _ as unreachable:
                assert False, f"Unexpected config result: {unreachable}"
        
        console.print("[bold]Current Configuration:[/bold]")
        console.print(f"Configs directory: [blue]{app_config.configs_directory}[/blue]")
        console.print(f"Target client: [cyan]{app_config.target_client.value}[/cyan]")
        console.print(f"Target path: [blue]{app_config.get_target_path()}[/blue]")
        return
    
    if not dir and not client:
        console.print("[red]Error: Specify --dir <path> or --client <name> or --show[/red]")
        raise typer.Exit(1)
    
    if dir:
        if not dir.exists():
            create = typer.confirm(f"Directory {dir} does not exist. Create it?")
            if create:
                try:
                    dir.mkdir(parents=True, exist_ok=True)
                    console.print(f"[green]✓ Created directory: {dir}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to create directory: {e}[/red]")
                    raise typer.Exit(1)
            else:
                console.print("[yellow]Directory creation cancelled[/yellow]")
                raise typer.Exit(1)
        
        if not dir.is_dir():
            console.print(f"[red]Error: {dir} is not a directory[/red]")
            raise typer.Exit(1)
        
        existing_config = load_config()
        match existing_config:
            case models.ConfigError():
                app_config = models.AppConfig(configs_directory=dir)
            case models.AppConfig() as app_config:
                app_config.configs_directory = dir
            case _ as unreachable:
                assert False, f"Unexpected existing config result: {unreachable}"
        
        save_result = save_config(app_config)
        match save_result:
            case models.ConfigError(message=msg):
                console.print(f"[red]Failed to save configuration: {msg}[/red]")
                raise typer.Exit(1)
            case bool():
                pass
            case _ as unreachable:
                assert False, f"Unexpected save result: {unreachable}"
        
        console.print(f"[green]✓ Configs directory set to: {dir}[/green]")
    
    if client:
        # Special minimal-scope behavior for Codex: perform write/update now
        if client == "codex":
            existing_config = load_config()
            match existing_config:
                case models.ConfigError(message=msg):
                    console.print(f"[red]Error: {msg}[/red]")
                    console.print("Set configs directory first with --dir")
                    raise typer.Exit(1)
                case models.AppConfig() as app_config:
                    pass
                case _ as unreachable:
                    assert False, f"Unexpected existing config result: {unreachable}"

            codex_result = update_codex_from_active(app_config)
            match codex_result:
                case models.SwitchError(message=msg):
                    console.print(f"[red]{msg}[/red]")
                    raise typer.Exit(1)
                case bool():
                    console.print("[green]✓ Updated ~/.codex/config.toml with active MCP server[/green]")
                    return
                case _ as unreachable:
                    assert False, f"Unexpected Codex update result: {unreachable}"

        try:
            mcp_client = models.MCPClient(client)
        except ValueError:
            console.print(f"[red]Invalid client: {client}[/red]")
            console.print("Valid clients: claude-desktop, vscode, cursor, codex")
            raise typer.Exit(1)
        
        existing_config = load_config()
        match existing_config:
            case models.ConfigError(message=msg):
                console.print(f"[red]Error: {msg}[/red]")
                console.print("Set configs directory first with --dir")
                raise typer.Exit(1)
            case models.AppConfig() as app_config:
                app_config.target_client = mcp_client
            case _ as unreachable:
                assert False, f"Unexpected existing config result: {unreachable}"
        
        save_result = save_config(app_config)
        match save_result:
            case models.ConfigError(message=msg):
                console.print(f"[red]Failed to save configuration: {msg}[/red]")
                raise typer.Exit(1)
            case bool():
                pass
            case _ as unreachable:
                assert False, f"Unexpected save result: {unreachable}"
        
        console.print(f"[green]✓ Target client set to: {client}[/green]")
        console.print(f"Target path: [blue]{app_config.get_target_path()}[/blue]")


if __name__ == "__main__":
    app()
