"""Main CLI entry point for grovectl.

This module defines the main CLI group and global options that are
shared across all commands.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click
from rich.console import Console

from grovectl import __version__
from grovectl.cli.batch import batch
from grovectl.cli.config_cmd import config
from grovectl.cli.hosts import hosts
from grovectl.cli.vm import vm
from grovectl.core.config import ConfigManager, get_default_config_path
from grovectl.core.exceptions import GrovectlError
from grovectl.core.ssh import SSHManager
from grovectl.core.vm_manager import VMManager
from grovectl.utils.logging import configure_logging
from grovectl.utils.output import error_console, print_error

if TYPE_CHECKING:
    pass


class Context:
    """CLI context object passed to all commands.

    Holds shared state including configuration, SSH manager,
    and CLI options like verbosity and dry-run mode.

    Attributes:
        config: ConfigManager instance.
        ssh: SSHManager instance.
        vm_manager: VMManager instance.
        verbose: Verbosity level (0-3).
        dry_run: Whether to run in dry-run mode.
        debug: Whether to show debug tracebacks.
    """

    def __init__(self) -> None:
        self.config: ConfigManager | None = None
        self.ssh: SSHManager | None = None
        self.vm_manager: VMManager | None = None
        self.verbose: int = 0
        self.dry_run: bool = False
        self.debug: bool = False

    def init_config(self) -> ConfigManager:
        """Initialize configuration manager.

        Returns:
            ConfigManager instance.
        """
        if self.config is None:
            self.config = ConfigManager()
        return self.config

    def init_ssh(self) -> SSHManager:
        """Initialize SSH manager.

        Returns:
            SSHManager instance.
        """
        if self.ssh is None:
            self.ssh = SSHManager()
        return self.ssh

    def init_vm_manager(self) -> VMManager:
        """Initialize VM manager.

        Returns:
            VMManager instance.
        """
        if self.vm_manager is None:
            config = self.init_config()
            ssh = self.init_ssh()
            self.vm_manager = VMManager(config, ssh, dry_run=self.dry_run)
        return self.vm_manager

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.ssh:
            self.ssh.close_all()


pass_context = click.make_pass_decorator(Context, ensure=True)


def version_callback(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    """Print version and exit."""
    if not value or ctx.resilient_parsing:
        return
    console = Console()
    console.print(f"grovectl version [cyan]{__version__}[/cyan]")
    ctx.exit()


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (-v, -vv, -vvv for more).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print commands without executing them.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Show full error tracebacks.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    envvar="GROVECTL_CONFIG",
    help=f"Path to config file (default: {get_default_config_path()}).",
)
@click.option(
    "--version",
    is_flag=True,
    callback=version_callback,
    expose_value=False,
    is_eager=True,
    help="Show version and exit.",
)
@pass_context
def cli(
    ctx: Context,
    verbose: int,
    dry_run: bool,
    debug: bool,
    config_path: str | None,
) -> None:
    """grovectl - Manage macOS VMs on remote hosts.

    A command-line tool for managing virtual machines running on
    remote macOS hosts using the tart virtualization tool.

    Use -v, -vv, or -vvv for increasing levels of verbosity.

    Examples:

        # List all configured hosts

        $ grovectl hosts list

        # List VMs on a specific host

        $ grovectl vm list --host mac-builder-1

        # Start a VM

        $ grovectl vm start my-vm --host mac-builder-1

        # Stop all VMs matching a pattern

        $ grovectl batch stop --pattern "test-*"
    """
    ctx.verbose = verbose
    ctx.dry_run = dry_run
    ctx.debug = debug

    # Configure logging based on verbosity
    configure_logging(verbosity=verbose)

    # Initialize config if path specified
    if config_path:
        from pathlib import Path

        ctx.config = ConfigManager(Path(config_path))


# Register subcommand groups
cli.add_command(hosts)
cli.add_command(vm)
cli.add_command(batch)
cli.add_command(config)


def main() -> None:
    """Main entry point with error handling."""
    try:
        cli(standalone_mode=False)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except GrovectlError as e:
        print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        error_console.print("\n[dim]Interrupted[/dim]")
        sys.exit(130)
    except Exception as e:
        # Check if debug mode is enabled via env or previous parsing
        import os

        if os.environ.get("GROVECTL_DEBUG") or "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        else:
            print_error(f"Unexpected error: {e}")
            error_console.print("[dim]Use --debug for full traceback[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
