"""CLI context for grovectl.

This module defines the shared context object passed to all CLI commands,
extracted to avoid circular imports.
"""

from __future__ import annotations

import click

from grovectl.core.config import ConfigManager
from grovectl.core.ssh import SSHManager
from grovectl.core.vm_manager import VMManager


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
