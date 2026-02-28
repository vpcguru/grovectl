"""SSH connection manager with connection pooling.

This module provides a thread-safe SSH connection manager that handles:
- Connection pooling for efficient multi-host operations
- Automatic reconnection on connection loss
- Retry logic with exponential backoff
- SSH key and password authentication
"""

from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass, field
from pathlib import Path

import paramiko

from grovectl.core.exceptions import (
    SSHAuthenticationError,
    SSHConnectionError,
    SSHTimeoutError,
)
from grovectl.models.host import Host
from grovectl.utils.logging import get_logger
from grovectl.utils.retry import retry_with_backoff

logger = get_logger("ssh")


@dataclass
class SSHResult:
    """Result from an SSH command execution.

    Args:
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        exit_code: Exit code of the command.
        host: Name of the host where command ran.
        command: The command that was executed.

    Attributes:
        success: True if exit code is 0.
    """

    stdout: str
    stderr: str
    exit_code: int
    host: str
    command: str

    @property
    def success(self) -> bool:
        """Check if command succeeded (exit code 0)."""
        return self.exit_code == 0

    @property
    def output(self) -> str:
        """Combined stdout and stderr output."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)


@dataclass
class PooledConnection:
    """A pooled SSH connection with metadata.

    Args:
        client: The Paramiko SSH client.
        host: The Host this connection is for.
        created_at: Timestamp when connection was created.
    """

    client: paramiko.SSHClient
    host: Host
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def is_active(self) -> bool:
        """Check if the connection is still active."""
        transport = self.client.get_transport()
        return transport is not None and transport.is_active()


class SSHManager:
    """Manages SSH connections with pooling and retry logic.

    This class provides a thread-safe connection pool for SSH clients,
    with automatic reconnection and retry capabilities.

    Args:
        default_timeout: Default timeout for SSH operations in seconds.
        pool_max_age: Maximum age of pooled connections in seconds.

    Example:
        >>> manager = SSHManager()
        >>> host = Host(name="server", hostname="192.168.1.1", username="admin")
        >>> result = manager.run(host, "ls -la")
        >>> print(result.stdout)

        >>> # Test connection
        >>> if manager.test_connection(host):
        ...     print("Connected successfully")

        >>> # Clean up
        >>> manager.close_all()
    """

    def __init__(
        self,
        default_timeout: int = 30,
        pool_max_age: int = 300,
    ) -> None:
        self._lock = threading.RLock()
        self._pool: dict[str, PooledConnection] = {}
        self.default_timeout = default_timeout
        self.pool_max_age = pool_max_age

    def _create_client(
        self,
        host: Host,
        password: str | None = None,
        timeout: int | None = None,
    ) -> paramiko.SSHClient:
        """Create a new SSH client connection.

        Args:
            host: Host to connect to.
            password: Optional password for authentication.
            timeout: Connection timeout in seconds.

        Returns:
            Connected SSH client.

        Raises:
            SSHAuthenticationError: If authentication fails.
            SSHTimeoutError: If connection times out.
            SSHConnectionError: For other connection failures.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_timeout = timeout or self.default_timeout

        # Prepare key file
        key_filename = None
        if host.ssh_key:
            key_path = Path(host.ssh_key).expanduser()
            if key_path.exists():
                key_filename = str(key_path)
            else:
                logger.warning(f"SSH key not found: {host.ssh_key}")

        try:
            logger.debug(f"Connecting to {host.hostname}:{host.port} as {host.username}")
            client.connect(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                password=password,
                key_filename=key_filename,
                look_for_keys=True,
                allow_agent=True,
                timeout=connect_timeout,
            )
            logger.debug(f"Connected to {host.name}")
            return client

        except paramiko.AuthenticationException as e:
            client.close()
            raise SSHAuthenticationError(host.hostname, host.username) from e

        except TimeoutError as e:
            client.close()
            raise SSHTimeoutError(host.hostname, connect_timeout) from e

        except (paramiko.SSHException, OSError) as e:
            client.close()
            raise SSHConnectionError(host.hostname, str(e)) from e

    def get_client(
        self,
        host: Host,
        password: str | None = None,
        force_new: bool = False,
    ) -> paramiko.SSHClient:
        """Get a pooled or new SSH client for a host.

        Args:
            host: Host to connect to.
            password: Optional password for authentication.
            force_new: Force creating a new connection.

        Returns:
            SSH client (may be from pool or newly created).
        """
        with self._lock:
            # Check for existing pooled connection
            if not force_new and host.name in self._pool:
                pooled = self._pool[host.name]

                # Check if connection is still valid
                if pooled.is_active():
                    # Check age
                    import time

                    age = time.time() - pooled.created_at
                    if age < self.pool_max_age:
                        logger.debug(f"Reusing pooled connection for {host.name}")
                        return pooled.client

                # Remove stale connection
                logger.debug(f"Removing stale connection for {host.name}")
                with contextlib.suppress(Exception):
                    pooled.client.close()
                del self._pool[host.name]

            # Create new connection
            client = self._create_client(host, password=password)
            self._pool[host.name] = PooledConnection(client=client, host=host)
            return client

    @retry_with_backoff(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(SSHConnectionError,),
    )
    def run(
        self,
        host: Host,
        command: str,
        password: str | None = None,
        timeout: int | None = None,
        dry_run: bool = False,
    ) -> SSHResult:
        """Execute a command on a remote host.

        Args:
            host: Host to run command on.
            command: Command to execute.
            password: Optional password for authentication.
            timeout: Command execution timeout.
            dry_run: If True, don't actually run the command.

        Returns:
            SSHResult with command output and exit code.

        Example:
            >>> result = manager.run(host, "tart list --format json")
            >>> if result.success:
            ...     data = json.loads(result.stdout)
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would execute on {host.name}: {command}")
            return SSHResult(
                stdout="[dry-run mode - command not executed]",
                stderr="",
                exit_code=0,
                host=host.name,
                command=command,
            )

        logger.debug(f"Executing on {host.name}: {command}")

        try:
            client = self.get_client(host, password=password)
            exec_timeout = timeout or self.default_timeout

            _stdin, stdout, stderr = client.exec_command(command, timeout=exec_timeout)

            # Read output
            stdout_data = stdout.read().decode("utf-8", errors="replace")
            stderr_data = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()

            result = SSHResult(
                stdout=stdout_data.strip(),
                stderr=stderr_data.strip(),
                exit_code=exit_code,
                host=host.name,
                command=command,
            )

            if result.success:
                logger.debug(f"Command succeeded on {host.name}")
            else:
                logger.warning(f"Command failed on {host.name} with exit code {exit_code}")

            return result

        except TimeoutError as e:
            raise SSHConnectionError(
                host.hostname, f"Command timed out after {timeout}s"
            ) from e

        except paramiko.SSHException as e:
            # Connection may be stale, try to reconnect
            with self._lock:
                if host.name in self._pool:
                    del self._pool[host.name]
            raise SSHConnectionError(host.hostname, str(e)) from e

    def test_connection(
        self,
        host: Host,
        password: str | None = None,
    ) -> tuple[bool, str]:
        """Test SSH connectivity to a host.

        Args:
            host: Host to test connection to.
            password: Optional password for authentication.

        Returns:
            Tuple of (success, message).
        """
        try:
            client = self._create_client(host, password=password, timeout=10)
            # Run a simple command to verify
            _stdin, stdout, _stderr = client.exec_command("echo ok")
            result = stdout.read().decode().strip()
            client.close()

            if result == "ok":
                return True, f"Connected to {host.name} ({host.hostname})"
            return False, f"Unexpected response from {host.name}"

        except SSHAuthenticationError as e:
            return False, f"Authentication failed: {e.message}"

        except SSHTimeoutError as e:
            return False, f"Connection timed out: {e.message}"

        except SSHConnectionError as e:
            return False, f"Connection failed: {e.message}"

        except Exception as e:
            return False, f"Unexpected error: {e}"

    def close(self, host_name: str) -> None:
        """Close a specific pooled connection.

        Args:
            host_name: Name of the host connection to close.
        """
        with self._lock:
            if host_name in self._pool:
                with contextlib.suppress(Exception):
                    self._pool[host_name].client.close()
                del self._pool[host_name]
                logger.debug(f"Closed connection for {host_name}")

    def close_all(self) -> None:
        """Close all pooled connections."""
        with self._lock:
            for _name, pooled in list(self._pool.items()):
                with contextlib.suppress(Exception):
                    pooled.client.close()
            self._pool.clear()
            logger.debug("Closed all SSH connections")

    @property
    def active_connections(self) -> list[str]:
        """List of currently pooled host names."""
        with self._lock:
            return [name for name, pooled in self._pool.items() if pooled.is_active()]

    def __enter__(self) -> SSHManager:
        return self

    def __exit__(self, *args: object) -> None:
        self.close_all()
