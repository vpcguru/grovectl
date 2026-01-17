"""Custom exceptions for grovectl.

This module defines a hierarchy of exceptions used throughout grovectl
to provide meaningful error messages and enable proper error handling.

Exception Hierarchy:
    GrovectlError (base)
    ├── ConfigurationError
    │   └── ConfigNotFoundError
    ├── SSHConnectionError
    │   ├── SSHAuthenticationError
    │   └── SSHTimeoutError
    ├── HostNotFoundError
    └── VMOperationError
        ├── VMNotFoundError
        ├── VMStartError
        └── VMStopError
"""

from __future__ import annotations

from typing import Any


class GrovectlError(Exception):
    """Base exception for all grovectl errors.

    Args:
        message: Human-readable error message.
        details: Optional dictionary with additional error context.

    Attributes:
        message: The error message.
        details: Additional context about the error.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class ConfigurationError(GrovectlError):
    """Raised when there is a configuration-related error.

    Examples:
        - Invalid YAML syntax in config file
        - Missing required configuration fields
        - Invalid configuration values
    """


class ConfigNotFoundError(ConfigurationError):
    """Raised when the configuration file cannot be found.

    Args:
        path: The path where the config was expected.
    """

    def __init__(self, path: str) -> None:
        super().__init__(
            f"Configuration file not found: {path}",
            details={"path": path},
        )
        self.path = path


class SSHConnectionError(GrovectlError):
    """Raised when an SSH connection fails.

    Args:
        host: The hostname or IP address.
        message: Description of the connection failure.
    """

    def __init__(self, host: str, message: str) -> None:
        super().__init__(
            f"SSH connection to '{host}' failed: {message}",
            details={"host": host},
        )
        self.host = host


class SSHAuthenticationError(SSHConnectionError):
    """Raised when SSH authentication fails.

    Args:
        host: The hostname or IP address.
        username: The username used for authentication.
    """

    def __init__(self, host: str, username: str | None = None) -> None:
        msg = "authentication failed"
        if username:
            msg = f"authentication failed for user '{username}'"
        super().__init__(host, msg)
        self.username = username


class SSHTimeoutError(SSHConnectionError):
    """Raised when an SSH connection times out.

    Args:
        host: The hostname or IP address.
        timeout: The timeout value in seconds.
    """

    def __init__(self, host: str, timeout: int) -> None:
        super().__init__(host, f"connection timed out after {timeout}s")
        self.timeout = timeout
        self.details["timeout"] = timeout


class HostNotFoundError(GrovectlError):
    """Raised when a specified host is not found in configuration.

    Args:
        name: The name of the host that was not found.
    """

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Host '{name}' not found in configuration",
            details={"host_name": name},
        )
        self.name = name


class VMOperationError(GrovectlError):
    """Raised when a VM operation fails.

    Args:
        vm_name: The name of the VM.
        operation: The operation that failed (e.g., 'start', 'stop').
        message: Description of the failure.
        host: Optional host where the VM resides.
    """

    def __init__(
        self,
        vm_name: str,
        operation: str,
        message: str,
        host: str | None = None,
    ) -> None:
        host_str = f" on '{host}'" if host else ""
        super().__init__(
            f"Failed to {operation} VM '{vm_name}'{host_str}: {message}",
            details={"vm_name": vm_name, "operation": operation, "host": host},
        )
        self.vm_name = vm_name
        self.operation = operation
        self.host = host


class VMNotFoundError(VMOperationError):
    """Raised when a VM cannot be found.

    Args:
        vm_name: The name of the VM.
        host: Optional host where the VM was expected.
    """

    def __init__(self, vm_name: str, host: str | None = None) -> None:
        super().__init__(vm_name, "find", "VM does not exist", host=host)


class VMStartError(VMOperationError):
    """Raised when a VM fails to start.

    Args:
        vm_name: The name of the VM.
        message: Description of the failure.
        host: Optional host where the VM resides.
    """

    def __init__(self, vm_name: str, message: str, host: str | None = None) -> None:
        super().__init__(vm_name, "start", message, host=host)


class VMStopError(VMOperationError):
    """Raised when a VM fails to stop.

    Args:
        vm_name: The name of the VM.
        message: Description of the failure.
        host: Optional host where the VM resides.
    """

    def __init__(self, vm_name: str, message: str, host: str | None = None) -> None:
        super().__init__(vm_name, "stop", message, host=host)
