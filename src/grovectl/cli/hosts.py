"""Host management commands for grovectl.

This module provides CLI commands for managing remote hosts
in the grovectl configuration.
"""

from __future__ import annotations

import click

from grovectl.cli.context import Context, pass_context
from grovectl.core.exceptions import ConfigurationError
from grovectl.models.host import Host
from grovectl.utils.output import (
    OutputFormat,
    OutputFormatter,
    print_error,
    print_info,
    print_success,
    print_warning,
)


@click.group()
def hosts() -> None:
    """Manage remote hosts.

    Commands for adding, removing, and testing SSH connectivity
    to remote macOS hosts that run VMs.
    """


@hosts.command("add")
@click.argument("name")
@click.argument("hostname")
@click.option(
    "--username",
    "-u",
    default=None,
    help="SSH username (defaults to current user).",
)
@click.option(
    "--ssh-key",
    "-k",
    default=None,
    help="Path to SSH private key.",
)
@click.option(
    "--port",
    "-p",
    default=22,
    type=int,
    help="SSH port (default: 22).",
)
@pass_context
def hosts_add(
    ctx: Context,
    name: str,
    hostname: str,
    username: str | None,
    ssh_key: str | None,
    port: int,
) -> None:
    """Add a new host to configuration.

    NAME is a unique identifier for this host.
    HOSTNAME is the IP address or DNS name.

    Examples:

        $ grovectl hosts add mac-builder-1 192.168.1.100 --username admin

        $ grovectl hosts add mac-builder-2 builder2.local -u admin -k ~/.ssh/id_rsa
    """
    config = ctx.init_config()

    try:
        host = Host(
            name=name,
            hostname=hostname,
            username=username,
            ssh_key=ssh_key,
            port=port,
        )
        config.add_host(host)
        print_success(f"Added host '{name}' ({hostname})")

    except ConfigurationError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@hosts.command("list")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format.",
)
@pass_context
def hosts_list(ctx: Context, fmt: str) -> None:
    """List all configured hosts.

    Examples:

        $ grovectl hosts list

        $ grovectl hosts list --format json

        $ grovectl hosts list -f yaml
    """
    config = ctx.init_config()
    hosts_list = config.hosts

    if not hosts_list:
        print_info("No hosts configured. Use 'grovectl hosts add' to add a host.")
        return

    formatter = OutputFormatter(OutputFormat(fmt))
    formatter.print_hosts(hosts_list)


@hosts.command("remove")
@click.argument("name")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@pass_context
def hosts_remove(ctx: Context, name: str, yes: bool) -> None:
    """Remove a host from configuration.

    NAME is the identifier of the host to remove.

    Examples:

        $ grovectl hosts remove mac-builder-1

        $ grovectl hosts remove mac-builder-1 --yes
    """
    config = ctx.init_config()

    # Check if host exists
    host = config.get_host(name)
    if host is None:
        print_error(f"Host '{name}' not found")
        raise SystemExit(1)

    # Confirm deletion
    if not yes:
        click.confirm(
            f"Remove host '{name}' ({host.hostname})?",
            abort=True,
        )

    if config.remove_host(name):
        print_success(f"Removed host '{name}'")
    else:
        print_error(f"Failed to remove host '{name}'")
        raise SystemExit(1)


@hosts.command("test")
@click.argument("name")
@click.option(
    "--password",
    "-P",
    is_flag=True,
    help="Prompt for password authentication.",
)
@pass_context
def hosts_test(ctx: Context, name: str, password: bool) -> None:
    """Test SSH connectivity to a host.

    NAME is the identifier of the host to test.

    Examples:

        $ grovectl hosts test mac-builder-1

        $ grovectl hosts test mac-builder-1 --password
    """
    config = ctx.init_config()
    ssh = ctx.init_ssh()

    host = config.get_host(name)
    if host is None:
        print_error(f"Host '{name}' not found")
        raise SystemExit(1)

    # Get password if requested
    passwd = None
    if password:
        passwd = click.prompt("SSH Password", hide_input=True)

    print_info(f"Testing connection to {host.hostname}:{host.port}...")

    success, message = ssh.test_connection(host, password=passwd)

    if success:
        print_success(message)
    else:
        print_error(message)
        raise SystemExit(1)


@hosts.command("show")
@click.argument("name")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format.",
)
@pass_context
def hosts_show(ctx: Context, name: str, fmt: str) -> None:
    """Show details for a specific host.

    NAME is the identifier of the host.

    Examples:

        $ grovectl hosts show mac-builder-1

        $ grovectl hosts show mac-builder-1 --format json
    """
    config = ctx.init_config()

    host = config.get_host(name)
    if host is None:
        print_error(f"Host '{name}' not found")
        print_warning(
            "Available hosts: " + ", ".join(config.config.host_names)
            if config.config.host_names
            else "none"
        )
        raise SystemExit(1)

    formatter = OutputFormatter(OutputFormat(fmt))
    formatter.print_dict(host.to_dict(), title=f"Host: {name}")
