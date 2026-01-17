"""grovectl - CLI tool for managing macOS VMs via SSH on remote hosts.

This package provides a command-line interface for managing virtual machines
running on remote macOS hosts using the tart virtualization tool.

Example:
    $ grovectl hosts list
    $ grovectl vm list --host mac-builder-1
    $ grovectl vm start my-vm --host mac-builder-1
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "you@example.com"

from grovectl.core.exceptions import (
    ConfigurationError,
    GrovectlError,
    HostNotFoundError,
    SSHConnectionError,
    VMNotFoundError,
    VMOperationError,
)

__all__ = [
    "ConfigurationError",
    "GrovectlError",
    "HostNotFoundError",
    "SSHConnectionError",
    "VMNotFoundError",
    "VMOperationError",
    "__version__",
]
