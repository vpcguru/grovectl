"""Rich terminal output utilities for grovectl.

This module provides formatted output using the Rich library,
including tables, progress bars, spinners, and color-coded status.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from grovectl.models.host import Host
from grovectl.models.vm import VM, VMState

# Global console instance
console = Console()
error_console = Console(stderr=True)


class OutputFormat(str, Enum):
    """Supported output formats."""

    TABLE = "table"
    JSON = "json"
    YAML = "yaml"


class OutputFormatter:
    """Handles formatting and outputting data in various formats.

    Supports table, JSON, and YAML output formats with color-coded
    status indicators for Rich table output.

    Args:
        format_type: Output format to use (table, json, yaml).
        console: Rich console instance for output.

    Example:
        >>> formatter = OutputFormatter(OutputFormat.TABLE)
        >>> formatter.print_hosts([host1, host2])
        >>> formatter.print_vms([vm1, vm2])
    """

    def __init__(
        self,
        format_type: OutputFormat = OutputFormat.TABLE,
        output_console: Console | None = None,
    ) -> None:
        self.format_type = format_type
        self.console = output_console or console

    def print_hosts(self, hosts: list[Host]) -> None:
        """Print a list of hosts.

        Args:
            hosts: List of Host objects to display.
        """
        if self.format_type == OutputFormat.JSON:
            data = [h.to_dict() for h in hosts]
            self.console.print_json(json.dumps(data, indent=2))
        elif self.format_type == OutputFormat.YAML:
            data = [h.to_dict() for h in hosts]
            self.console.print(yaml.safe_dump(data, default_flow_style=False))
        else:
            self._print_hosts_table(hosts)

    def _print_hosts_table(self, hosts: list[Host]) -> None:
        """Print hosts as a Rich table."""
        table = Table(title="Configured Hosts", show_header=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Hostname", style="white")
        table.add_column("Username", style="yellow")
        table.add_column("Port", justify="right", style="dim")
        table.add_column("SSH Key", style="dim")

        for host in hosts:
            table.add_row(
                host.name,
                host.hostname,
                host.username or "-",
                str(host.port),
                host.ssh_key or "-",
            )

        self.console.print(table)

    def print_vms(self, vms: list[VM]) -> None:
        """Print a list of VMs.

        Args:
            vms: List of VM objects to display.
        """
        if self.format_type == OutputFormat.JSON:
            data = [v.to_dict() for v in vms]
            self.console.print_json(json.dumps(data, indent=2))
        elif self.format_type == OutputFormat.YAML:
            data = [v.to_dict() for v in vms]
            self.console.print(yaml.safe_dump(data, default_flow_style=False))
        else:
            self._print_vms_table(vms)

    def _print_vms_table(self, vms: list[VM]) -> None:
        """Print VMs as a Rich table."""
        table = Table(title="Virtual Machines", show_header=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Host", style="white")
        table.add_column("Status", justify="center")
        table.add_column("CPU", justify="right", style="yellow")
        table.add_column("Memory", justify="right", style="yellow")
        table.add_column("IP Address", style="green")

        for vm in vms:
            status_text = Text(vm.status_display)
            status_text.stylize(vm.state.color)

            table.add_row(
                vm.name,
                vm.host,
                status_text,
                str(vm.cpu) if vm.cpu else "-",
                vm.memory_display,
                vm.ip_address or "-",
            )

        self.console.print(table)

    def print_vm_status(self, vm: VM) -> None:
        """Print detailed status for a single VM.

        Args:
            vm: VM object to display.
        """
        if self.format_type != OutputFormat.TABLE:
            self.print_vms([vm])
            return

        status_color = vm.state.color
        panel = Panel(
            f"[bold]{vm.name}[/bold]\n\n"
            f"Host: {vm.host}\n"
            f"Status: [{status_color}]{vm.status_display}[/{status_color}]\n"
            f"CPU: {vm.cpu or 'N/A'}\n"
            f"Memory: {vm.memory_display}\n"
            f"IP: {vm.ip_address or 'N/A'}",
            title="VM Status",
            border_style=status_color,
        )
        self.console.print(panel)

    def print_dict(self, data: dict[str, Any], title: str | None = None) -> None:
        """Print a dictionary in the configured format.

        Args:
            data: Dictionary to display.
            title: Optional title for table format.
        """
        if self.format_type == OutputFormat.JSON:
            self.console.print_json(json.dumps(data, indent=2, default=str))
        elif self.format_type == OutputFormat.YAML:
            self.console.print(yaml.safe_dump(data, default_flow_style=False))
        else:
            table = Table(title=title, show_header=True)
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="white")

            for key, value in data.items():
                table.add_row(str(key), str(value))

            self.console.print(table)


def print_success(message: str) -> None:
    """Print a success message.

    Args:
        message: Success message to display.
    """
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message to stderr.

    Args:
        message: Error message to display.
    """
    error_console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message.

    Args:
        message: Warning message to display.
    """
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message.

    Args:
        message: Info message to display.
    """
    console.print(f"[blue]ℹ[/blue] {message}")


def create_progress() -> Progress:
    """Create a configured Progress instance for long operations.

    Returns:
        Progress instance with spinner and time elapsed.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def create_spinner_progress() -> Progress:
    """Create a simple spinner progress for indeterminate operations.

    Returns:
        Progress instance with just spinner and description.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def format_vm_state(state: VMState) -> Text:
    """Format a VM state with color coding.

    Args:
        state: VM state to format.

    Returns:
        Rich Text object with color styling.
    """
    text = Text(f"{state.symbol} {state.value}")
    text.stylize(state.color)
    return text


def confirm(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation.

    Args:
        message: Question to ask.
        default: Default value if user presses enter.

    Returns:
        True if confirmed, False otherwise.
    """
    suffix = "[Y/n]" if default else "[y/N]"
    response = console.input(f"{message} {suffix} ").strip().lower()

    if not response:
        return default

    return response in ("y", "yes")
