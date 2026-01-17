"""Host models for grovectl.

This module defines the data models for managing remote hosts
that run macOS VMs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class Host(BaseModel):
    """Represents a remote macOS host that can run VMs.

    Args:
        name: Unique identifier for this host.
        hostname: IP address or hostname for SSH connection.
        username: SSH username (defaults to current user if not specified).
        port: SSH port number.
        ssh_key: Path to SSH private key file.

    Example:
        >>> host = Host(
        ...     name="mac-builder-1",
        ...     hostname="192.168.1.100",
        ...     username="admin",
        ...     ssh_key="~/.ssh/id_rsa"
        ... )
    """

    name: Annotated[str, Field(min_length=1, description="Unique host identifier")]
    hostname: Annotated[str, Field(min_length=1, description="IP address or hostname")]
    username: str | None = Field(default=None, description="SSH username")
    port: Annotated[int, Field(ge=1, le=65535)] = Field(
        default=22, description="SSH port"
    )
    ssh_key: str | None = Field(default=None, description="Path to SSH private key")

    @field_validator("ssh_key")
    @classmethod
    def expand_ssh_key_path(cls, v: str | None) -> str | None:
        """Expand ~ in SSH key path."""
        if v is not None:
            return str(Path(v).expanduser())
        return v

    @property
    def display_name(self) -> str:
        """Human-readable display name for this host."""
        return f"{self.name} ({self.hostname})"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return self.model_dump(exclude_none=True)


class HostConfig(BaseModel):
    """Configuration for a collection of hosts.

    This model is used to validate the hosts section of the config file.

    Args:
        hosts: List of host configurations.
    """

    hosts: list[Host] = Field(default_factory=list)

    def get_host(self, name: str) -> Host | None:
        """Get a host by name.

        Args:
            name: The name of the host to find.

        Returns:
            The Host if found, None otherwise.
        """
        for host in self.hosts:
            if host.name == name:
                return host
        return None

    def add_host(self, host: Host) -> None:
        """Add a host to the configuration.

        Args:
            host: The Host to add.

        Raises:
            ValueError: If a host with the same name already exists.
        """
        if self.get_host(host.name) is not None:
            raise ValueError(f"Host '{host.name}' already exists")
        self.hosts.append(host)

    def remove_host(self, name: str) -> bool:
        """Remove a host by name.

        Args:
            name: The name of the host to remove.

        Returns:
            True if the host was removed, False if not found.
        """
        for i, host in enumerate(self.hosts):
            if host.name == name:
                del self.hosts[i]
                return True
        return False

    @property
    def host_names(self) -> list[str]:
        """List of all host names."""
        return [h.name for h in self.hosts]
