"""VM models for grovectl.

This module defines the data models for virtual machines
managed via the tart CLI on remote hosts.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class VMState(str, Enum):
    """Possible states for a virtual machine."""

    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"

    @property
    def color(self) -> str:
        """Rich color for this state.

        Returns:
            Color name for Rich console output.
        """
        colors = {
            VMState.RUNNING: "green",
            VMState.STOPPED: "red",
            VMState.STARTING: "yellow",
            VMState.STOPPING: "yellow",
            VMState.SUSPENDED: "blue",
            VMState.UNKNOWN: "dim",
        }
        return colors.get(self, "white")

    @property
    def symbol(self) -> str:
        """Status symbol for this state.

        Returns:
            Unicode symbol representing the state.
        """
        symbols = {
            VMState.RUNNING: "●",
            VMState.STOPPED: "○",
            VMState.STARTING: "◐",
            VMState.STOPPING: "◑",
            VMState.SUSPENDED: "◉",
            VMState.UNKNOWN: "?",
        }
        return symbols.get(self, "?")


class VM(BaseModel):
    """Represents a virtual machine on a remote host.

    Args:
        name: Unique name of the VM on the host.
        host: Name of the host where this VM resides.
        state: Current state of the VM.
        cpu: Number of CPU cores allocated.
        memory: Memory in MB allocated.
        disk: Disk size in GB.
        ip_address: IP address of the VM (if running).
        created_at: When the VM was created.
        source_image: The tart image this VM was created from.

    Example:
        >>> vm = VM(
        ...     name="builder-1",
        ...     host="mac-builder-1",
        ...     state=VMState.RUNNING,
        ...     cpu=4,
        ...     memory=8192,
        ...     ip_address="192.168.64.10"
        ... )
    """

    name: Annotated[str, Field(min_length=1, description="VM name")]
    host: str = Field(description="Host where VM resides")
    state: VMState = Field(default=VMState.UNKNOWN, description="Current VM state")
    cpu: int | None = Field(default=None, ge=1, description="CPU cores")
    memory: int | None = Field(default=None, ge=512, description="Memory in MB")
    disk: int | None = Field(default=None, ge=1, description="Disk size in GB")
    ip_address: str | None = Field(default=None, description="VM IP address")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    source_image: str | None = Field(default=None, description="Source tart image")

    @property
    def status_display(self) -> str:
        """Formatted status string with symbol.

        Returns:
            String like "● running" for display.
        """
        return f"{self.state.symbol} {self.state.value}"

    @property
    def memory_display(self) -> str:
        """Human-readable memory string.

        Returns:
            String like "8 GB" or "N/A" if not set.
        """
        if self.memory is None:
            return "N/A"
        if self.memory >= 1024:
            return f"{self.memory // 1024} GB"
        return f"{self.memory} MB"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON/YAML output.
        """
        data = self.model_dump(exclude_none=True)
        data["state"] = self.state.value
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_tart_output(cls, name: str, host: str, tart_data: dict) -> VM:
        """Create a VM instance from tart list output.

        Args:
            name: Name of the VM.
            host: Host where the VM resides.
            tart_data: Dictionary from tart list JSON output.

        Returns:
            VM instance populated with tart data.
        """
        state_str = tart_data.get("State", "unknown").lower()
        try:
            state = VMState(state_str)
        except ValueError:
            state = VMState.UNKNOWN

        return cls(
            name=name,
            host=host,
            state=state,
            cpu=tart_data.get("CPU"),
            memory=tart_data.get("Memory"),
            disk=tart_data.get("Disk"),
            source_image=tart_data.get("Source"),
        )
