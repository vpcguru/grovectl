"""VM operation commands for grovectl.

This module provides CLI commands for managing virtual machines
on remote hosts.
"""

from __future__ import annotations

import click

from grovectl.cli.main import Context, pass_context
from grovectl.core.exceptions import HostNotFoundError, VMNotFoundError, VMOperationError
from grovectl.utils.output import (
    OutputFormat,
    OutputFormatter,
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)


@click.group()
def vm() -> None:
    """Manage virtual machines.

    Commands for listing, starting, stopping, and managing VMs
    on remote hosts.
    """


@vm.command("list")
@click.option(
    "--host",
    "-h",
    "host_name",
    default=None,
    help="Filter by host name (default: all hosts).",
)
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format.",
)
@click.option(
    "--pattern",
    "-p",
    default=None,
    help="Filter VMs by glob pattern (e.g., 'test-*').",
)
@pass_context
def vm_list(
    ctx: Context,
    host_name: str | None,
    fmt: str,
    pattern: str | None,
) -> None:
    """List virtual machines.

    Lists VMs across all configured hosts, or filtered by a specific host.

    Examples:

        $ grovectl vm list

        $ grovectl vm list --host mac-builder-1

        $ grovectl vm list --pattern "test-*" --format json
    """
    try:
        vm_manager = ctx.init_vm_manager()
        vms = vm_manager.list_vms(
            host_name=host_name,
            pattern=pattern,
            show_progress=True,
        )

        if not vms:
            if host_name:
                print_info(f"No VMs found on host '{host_name}'")
            elif pattern:
                print_info(f"No VMs matching pattern '{pattern}'")
            else:
                print_info("No VMs found on any configured host")
            return

        formatter = OutputFormatter(OutputFormat(fmt))
        formatter.print_vms(vms)

    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@vm.command("start")
@click.argument("name")
@click.option(
    "--host",
    "-h",
    "host_name",
    required=True,
    help="Host where the VM resides.",
)
@pass_context
def vm_start(ctx: Context, name: str, host_name: str) -> None:
    """Start a virtual machine.

    NAME is the name of the VM to start.

    Examples:

        $ grovectl vm start my-vm --host mac-builder-1
    """
    if ctx.dry_run:
        print_info(f"[DRY RUN] Would start VM '{name}' on '{host_name}'")
        return

    try:
        vm_manager = ctx.init_vm_manager()
        vm = vm_manager.start_vm(name, host_name, show_progress=True)
        print_success(f"Started VM '{name}' on '{host_name}'")

        if vm.ip_address:
            console.print(f"  IP Address: [green]{vm.ip_address}[/green]")

    except VMNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except VMOperationError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@vm.command("stop")
@click.argument("name")
@click.option(
    "--host",
    "-h",
    "host_name",
    required=True,
    help="Host where the VM resides.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force stop (kill) the VM.",
)
@pass_context
def vm_stop(ctx: Context, name: str, host_name: str, force: bool) -> None:
    """Stop a virtual machine.

    NAME is the name of the VM to stop.

    Examples:

        $ grovectl vm stop my-vm --host mac-builder-1

        $ grovectl vm stop my-vm --host mac-builder-1 --force
    """
    if ctx.dry_run:
        action = "force stop" if force else "stop"
        print_info(f"[DRY RUN] Would {action} VM '{name}' on '{host_name}'")
        return

    try:
        vm_manager = ctx.init_vm_manager()
        vm_manager.stop_vm(name, host_name, force=force, show_progress=True)
        action = "Force stopped" if force else "Stopped"
        print_success(f"{action} VM '{name}' on '{host_name}'")

    except VMNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except VMOperationError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@vm.command("delete")
@click.argument("name")
@click.option(
    "--host",
    "-h",
    "host_name",
    required=True,
    help="Host where the VM resides.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
@pass_context
def vm_delete(ctx: Context, name: str, host_name: str, yes: bool) -> None:
    """Delete a virtual machine.

    NAME is the name of the VM to delete. This action is irreversible.

    Examples:

        $ grovectl vm delete my-vm --host mac-builder-1

        $ grovectl vm delete my-vm --host mac-builder-1 --yes
    """
    if ctx.dry_run:
        print_info(f"[DRY RUN] Would delete VM '{name}' on '{host_name}'")
        return

    if not yes:
        click.confirm(
            f"Delete VM '{name}' on '{host_name}'? This cannot be undone.",
            abort=True,
        )

    try:
        vm_manager = ctx.init_vm_manager()
        vm_manager.delete_vm(name, host_name, show_progress=True)
        print_success(f"Deleted VM '{name}' on '{host_name}'")

    except VMNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except VMOperationError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@vm.command("status")
@click.argument("name")
@click.option(
    "--host",
    "-h",
    "host_name",
    required=True,
    help="Host where the VM resides.",
)
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format.",
)
@pass_context
def vm_status(ctx: Context, name: str, host_name: str, fmt: str) -> None:
    """Show status of a virtual machine.

    NAME is the name of the VM.

    Examples:

        $ grovectl vm status my-vm --host mac-builder-1

        $ grovectl vm status my-vm --host mac-builder-1 --format json
    """
    try:
        vm_manager = ctx.init_vm_manager()
        vm = vm_manager.get_vm(name, host_name)

        if vm is None:
            print_error(f"VM '{name}' not found on '{host_name}'")
            raise SystemExit(1)

        # Try to get IP if running
        if vm.state.value == "running":
            ip = vm_manager.get_vm_ip(name, host_name, show_progress=False)
            if ip:
                vm.ip_address = ip

        formatter = OutputFormatter(OutputFormat(fmt))
        formatter.print_vm_status(vm)

    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@vm.command("clone")
@click.argument("source")
@click.argument("destination")
@click.option(
    "--host",
    "-h",
    "host_name",
    required=True,
    help="Host where to perform the clone.",
)
@pass_context
def vm_clone(ctx: Context, source: str, destination: str, host_name: str) -> None:
    """Clone a VM or image.

    SOURCE is the source VM or tart image name.
    DESTINATION is the name for the new VM.

    Examples:

        $ grovectl vm clone ghcr.io/cirruslabs/macos-sonoma-base:latest my-vm --host mac-builder-1

        $ grovectl vm clone template-vm new-vm --host mac-builder-1
    """
    if ctx.dry_run:
        print_info(
            f"[DRY RUN] Would clone '{source}' to '{destination}' on '{host_name}'"
        )
        return

    try:
        vm_manager = ctx.init_vm_manager()
        vm = vm_manager.clone_vm(source, destination, host_name, show_progress=True)
        print_success(f"Cloned '{source}' to '{destination}' on '{host_name}'")
        console.print(f"  State: {vm.status_display}")

    except VMOperationError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@vm.command("ip")
@click.argument("name")
@click.option(
    "--host",
    "-h",
    "host_name",
    required=True,
    help="Host where the VM resides.",
)
@pass_context
def vm_ip(ctx: Context, name: str, host_name: str) -> None:
    """Get IP address of a running VM.

    NAME is the name of the VM.

    Examples:

        $ grovectl vm ip my-vm --host mac-builder-1
    """
    try:
        vm_manager = ctx.init_vm_manager()
        ip = vm_manager.get_vm_ip(name, host_name, show_progress=True)

        if ip:
            console.print(ip)
        else:
            print_warning(f"No IP address available for '{name}'")
            print_info("The VM may not be running or may not have an IP yet.")
            raise SystemExit(1)

    except VMNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e


@vm.command("create")
@click.argument("name")
@click.option(
    "--host",
    "-h",
    "host_name",
    required=True,
    help="Host where to create the VM.",
)
@click.option(
    "--image",
    "-i",
    required=True,
    help="Source tart image to clone from.",
)
@click.option(
    "--cpu",
    type=int,
    default=None,
    help="Number of CPU cores (uses default from config).",
)
@click.option(
    "--memory",
    type=int,
    default=None,
    help="Memory in MB (uses default from config).",
)
@click.option(
    "--disk",
    type=int,
    default=None,
    help="Disk size in GB (uses default from config).",
)
@pass_context
def vm_create(
    ctx: Context,
    name: str,
    host_name: str,
    image: str,
    cpu: int | None,
    memory: int | None,
    disk: int | None,
) -> None:
    """Create a new VM from an image.

    NAME is the name for the new VM.

    Examples:

        $ grovectl vm create my-vm --host mac-builder-1 --image ghcr.io/cirruslabs/macos-sonoma-base:latest

        $ grovectl vm create my-vm --host mac-builder-1 --image base-template --cpu 8 --memory 16384
    """
    if ctx.dry_run:
        print_info(f"[DRY RUN] Would create VM '{name}' from '{image}' on '{host_name}'")
        return

    try:
        vm_manager = ctx.init_vm_manager()
        vm = vm_manager.create_vm(
            name=name,
            host_name=host_name,
            source_image=image,
            cpu=cpu,
            memory=memory,
            disk=disk,
            show_progress=True,
        )
        print_success(f"Created VM '{name}' on '{host_name}'")
        console.print(f"  Source: {image}")
        console.print(f"  CPU: {vm.cpu}")
        console.print(f"  Memory: {vm.memory_display}")

    except VMOperationError as e:
        print_error(str(e))
        raise SystemExit(1) from e
    except HostNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1) from e
