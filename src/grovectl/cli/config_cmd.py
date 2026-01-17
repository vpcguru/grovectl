"""Configuration management commands for grovectl.

This module provides CLI commands for viewing and managing
the grovectl configuration file.
"""

from __future__ import annotations

import click
import yaml

from grovectl.cli.main import Context, pass_context
from grovectl.core.config import ConfigManager, get_default_config_path
from grovectl.core.exceptions import ConfigurationError
from grovectl.utils.output import console, print_error, print_info, print_success


@click.group()
def config() -> None:
    """Manage grovectl configuration.

    Commands for viewing, validating, and initializing the
    configuration file.
    """


@config.command("show")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format.",
)
@pass_context
def config_show(ctx: Context, fmt: str) -> None:
    """Show current configuration.

    Displays the full configuration file contents.

    Examples:

        $ grovectl config show

        $ grovectl config show --format json
    """
    config_manager = ctx.init_config()
    data = config_manager.to_dict()

    if fmt == "json":
        import json

        console.print_json(json.dumps(data, indent=2, default=str))
    else:
        console.print(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))

    console.print(f"\n[dim]Config file: {config_manager.path}[/dim]")


@config.command("validate")
@pass_context
def config_validate(ctx: Context) -> None:
    """Validate the configuration file.

    Checks that the configuration file exists and contains
    valid YAML with correct structure.

    Examples:

        $ grovectl config validate
    """
    config_path = get_default_config_path()

    if not config_path.exists():
        print_error(f"Configuration file not found: {config_path}")
        print_info("Run 'grovectl config init' to create a default config.")
        raise SystemExit(1)

    try:
        # Try to load and validate
        config_manager = ConfigManager(config_path)

        print_success(f"Configuration is valid: {config_path}")
        console.print(f"  Hosts: {len(config_manager.hosts)}")
        console.print(f"  Default CPU: {config_manager.config.defaults.vm_cpu}")
        console.print(f"  Default Memory: {config_manager.config.defaults.vm_memory} MB")
        console.print(f"  Default Disk: {config_manager.config.defaults.vm_disk} GB")
        console.print(f"  Log Level: {config_manager.config.logging.level}")

    except ConfigurationError as e:
        print_error(f"Invalid configuration: {e}")
        raise SystemExit(1) from e


@config.command("init")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing configuration.",
)
@pass_context
def config_init(ctx: Context, force: bool) -> None:
    """Create a default configuration file.

    Creates an example configuration file with sample hosts
    and default values.

    Examples:

        $ grovectl config init

        $ grovectl config init --force
    """
    config_path = get_default_config_path()

    if config_path.exists() and not force:
        print_error(f"Configuration already exists: {config_path}")
        print_info("Use --force to overwrite.")
        raise SystemExit(1)

    try:
        path = ConfigManager.create_example_config(config_path)
        print_success(f"Created configuration at: {path}")
        print_info("Edit this file to add your hosts and customize settings.")

    except Exception as e:
        print_error(f"Failed to create configuration: {e}")
        raise SystemExit(1) from e


@config.command("path")
def config_path() -> None:
    """Show the configuration file path.

    Displays the path where grovectl looks for its configuration.

    Examples:

        $ grovectl config path
    """
    path = get_default_config_path()
    console.print(str(path))

    if path.exists():
        console.print("[dim](file exists)[/dim]")
    else:
        console.print("[dim](file does not exist)[/dim]")


@config.command("edit")
@click.option(
    "--editor",
    "-e",
    envvar="EDITOR",
    default="vim",
    help="Editor to use (default: $EDITOR or vim).",
)
@pass_context
def config_edit(ctx: Context, editor: str) -> None:
    """Open configuration file in editor.

    Opens the configuration file in the specified editor.
    Creates the file if it doesn't exist.

    Examples:

        $ grovectl config edit

        $ grovectl config edit --editor nano

        $ EDITOR=code grovectl config edit
    """
    import subprocess

    config_path = get_default_config_path()

    # Create default config if it doesn't exist
    if not config_path.exists():
        print_info(f"Creating new configuration at: {config_path}")
        ConfigManager.create_example_config(config_path)

    try:
        subprocess.run([editor, str(config_path)], check=True)
        print_success("Configuration updated")

        # Validate after editing
        try:
            ConfigManager(config_path)
            print_info("Configuration is valid")
        except ConfigurationError as e:
            print_error(f"Warning: Configuration may be invalid: {e}")

    except subprocess.CalledProcessError as e:
        print_error(f"Editor exited with error: {e}")
        raise SystemExit(1) from e
    except FileNotFoundError:
        print_error(f"Editor not found: {editor}")
        print_info("Set the EDITOR environment variable or use --editor")
        raise SystemExit(1)
