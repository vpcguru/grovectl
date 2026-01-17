"""Batch operation commands for grovectl.

This module provides CLI commands for performing operations
on multiple VMs at once.
"""

from __future__ import annotations

import click
from rich.table import Table

from grovectl.cli.context import Context, pass_context
from grovectl.core.exceptions import HostNotFoundError
from grovectl.utils.output import console, print_error, print_info, print_success


@click.group()
def batch() -> None:
    """Batch operations on multiple VMs.

    Commands for starting, stopping, or managing multiple VMs
    that match a pattern.
    """


@batch.command("start")
@click.option(
    "--pattern",
    "-p",
    required=True,
    help="Glob pattern to match VM names (e.g., 'test-*').",
)
@click.option(
    "--host",
    "-h",
    "host_name",
    default=None,
    help="Filter by host (default: all hosts).",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@pass_context
def batch_start(
    ctx: Context,
    pattern: str,
    host_name: str | None,
    yes: bool,
) -> None:
    """Start multiple VMs matching a pattern.

    Examples:

        $ grovectl batch start --pattern "test-*"

        $ grovectl batch start --pattern "builder-*" --host mac-builder-1

        $ grovectl batch start --pattern "*" --yes
    """
    try:
        vm_manager = ctx.init_vm_manager()

        # First, list matching VMs
        vms = vm_manager.list_vms(host_name=host_name, pattern=pattern)

        if not vms:
            print_info(f"No VMs matching pattern '{pattern}'")
            return

        # Show what will be started
        console.print(f"\nFound {len(vms)} VM(s) matching '{pattern}':")
        for vm in vms:
            console.print(f"  - {vm.name} on {vm.host} ({vm.status_display})")

        if ctx.dry_run:
            print_info("[DRY RUN] Would start the above VMs")
            return

        if not yes:
            click.confirm("\nStart these VMs?", abort=True)

        # Perform batch start
        console.print()
        results = vm_manager.batch_start(pattern, host_name=host_name)

        # Show results
        _print_batch_results(results, "Start")

    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@batch.command("stop")
@click.option(
    "--pattern",
    "-p",
    required=True,
    help="Glob pattern to match VM names (e.g., 'test-*').",
)
@click.option(
    "--host",
    "-h",
    "host_name",
    default=None,
    help="Filter by host (default: all hosts).",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force stop (kill) VMs.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@pass_context
def batch_stop(
    ctx: Context,
    pattern: str,
    host_name: str | None,
    force: bool,
    yes: bool,
) -> None:
    """Stop multiple VMs matching a pattern.

    Examples:

        $ grovectl batch stop --pattern "test-*"

        $ grovectl batch stop --pattern "builder-*" --host mac-builder-1 --force

        $ grovectl batch stop --pattern "*" --yes
    """
    try:
        vm_manager = ctx.init_vm_manager()

        # First, list matching VMs
        vms = vm_manager.list_vms(host_name=host_name, pattern=pattern)

        if not vms:
            print_info(f"No VMs matching pattern '{pattern}'")
            return

        # Show what will be stopped
        action = "force stop" if force else "stop"
        console.print(f"\nFound {len(vms)} VM(s) matching '{pattern}':")
        for vm in vms:
            console.print(f"  - {vm.name} on {vm.host} ({vm.status_display})")

        if ctx.dry_run:
            print_info(f"[DRY RUN] Would {action} the above VMs")
            return

        if not yes:
            click.confirm(f"\n{action.title()} these VMs?", abort=True)

        # Perform batch stop
        console.print()
        results = vm_manager.batch_stop(pattern, host_name=host_name, force=force)

        # Show results
        _print_batch_results(results, "Stop")

    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@batch.command("list")
@click.option(
    "--pattern",
    "-p",
    required=True,
    help="Glob pattern to match VM names (e.g., 'test-*').",
)
@click.option(
    "--host",
    "-h",
    "host_name",
    default=None,
    help="Filter by host (default: all hosts).",
)
@pass_context
def batch_list(ctx: Context, pattern: str, host_name: str | None) -> None:
    """List VMs matching a pattern.

    Preview which VMs would be affected by a batch operation.

    Examples:

        $ grovectl batch list --pattern "test-*"

        $ grovectl batch list --pattern "builder-*" --host mac-builder-1
    """
    try:
        vm_manager = ctx.init_vm_manager()
        vms = vm_manager.list_vms(host_name=host_name, pattern=pattern)

        if not vms:
            print_info(f"No VMs matching pattern '{pattern}'")
            return

        console.print(f"\nVMs matching '{pattern}':")

        table = Table(show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Host", style="white")
        table.add_column("Status")

        for vm in vms:
            from rich.text import Text

            status = Text(vm.status_display)
            status.stylize(vm.state.color)
            table.add_row(vm.name, vm.host, status)

        console.print(table)
        console.print(f"\nTotal: {len(vms)} VM(s)")

    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


def _print_batch_results(results: list[tuple[str, bool, str]], operation: str) -> None:
    """Print results from a batch operation.

    Args:
        results: List of (vm_name, success, message) tuples.
        operation: Name of the operation (Start, Stop, etc.).
    """
    table = Table(title=f"Batch {operation} Results", show_header=True)
    table.add_column("VM", style="cyan")
    table.add_column("Result")
    table.add_column("Message")

    success_count = 0
    fail_count = 0

    for vm_name, success, message in results:
        if success:
            result = "[green]Success[/green]"
            success_count += 1
        else:
            result = "[red]Failed[/red]"
            fail_count += 1

        table.add_row(vm_name, result, message)

    console.print(table)
    console.print()

    if fail_count == 0:
        print_success(f"All {success_count} VM(s) processed successfully")
    else:
        console.print(f"[green]{success_count} succeeded[/green], [red]{fail_count} failed[/red]")
