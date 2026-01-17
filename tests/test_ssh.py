"""Tests for SSH connection management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from grovectl.core.exceptions import (
    SSHAuthenticationError,
    SSHTimeoutError,
)
from grovectl.core.ssh import SSHManager, SSHResult
from grovectl.models.host import Host


class TestSSHResult:
    """Tests for SSHResult dataclass."""

    def test_success_property(self) -> None:
        """Test the success property."""
        success_result = SSHResult(
            stdout="output",
            stderr="",
            exit_code=0,
            host="test",
            command="echo test",
        )
        assert success_result.success is True

        failure_result = SSHResult(
            stdout="",
            stderr="error",
            exit_code=1,
            host="test",
            command="false",
        )
        assert failure_result.success is False

    def test_output_property(self) -> None:
        """Test the combined output property."""
        result = SSHResult(
            stdout="stdout content",
            stderr="stderr content",
            exit_code=0,
            host="test",
            command="test",
        )
        assert "stdout content" in result.output
        assert "stderr content" in result.output

    def test_output_empty(self) -> None:
        """Test output when stdout/stderr are empty."""
        result = SSHResult(
            stdout="",
            stderr="",
            exit_code=0,
            host="test",
            command="test",
        )
        assert result.output == ""


class TestSSHManager:
    """Tests for SSHManager."""

    @pytest.fixture
    def ssh_manager(self) -> SSHManager:
        """Create an SSH manager for testing."""
        return SSHManager(default_timeout=10, pool_max_age=60)

    @pytest.fixture
    def host(self) -> Host:
        """Create a test host."""
        return Host(
            name="test-host",
            hostname="192.168.1.100",
            username="admin",
            port=22,
        )

    def test_init(self, ssh_manager: SSHManager) -> None:
        """Test SSHManager initialization."""
        assert ssh_manager.default_timeout == 10
        assert ssh_manager.pool_max_age == 60
        assert ssh_manager.active_connections == []

    @patch("paramiko.SSHClient")
    def test_create_client_success(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test successful client creation."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        client = ssh_manager._create_client(host)

        assert client == mock_client
        mock_client.connect.assert_called_once()

    @patch("paramiko.SSHClient")
    def test_create_client_auth_failure(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test authentication failure."""
        import paramiko

        mock_client = MagicMock()
        mock_client.connect.side_effect = paramiko.AuthenticationException()
        mock_client_class.return_value = mock_client

        with pytest.raises(SSHAuthenticationError) as exc_info:
            ssh_manager._create_client(host)

        assert host.hostname in str(exc_info.value)

    @patch("paramiko.SSHClient")
    def test_create_client_timeout(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test connection timeout."""

        mock_client = MagicMock()
        mock_client.connect.side_effect = TimeoutError()
        mock_client_class.return_value = mock_client

        with pytest.raises(SSHTimeoutError) as exc_info:
            ssh_manager._create_client(host, timeout=5)

        assert "5s" in str(exc_info.value)

    def test_dry_run_mode(self, ssh_manager: SSHManager, host: Host) -> None:
        """Test dry-run mode doesn't execute commands."""
        result = ssh_manager.run(host, "dangerous command", dry_run=True)

        assert result.success is True
        assert "dry-run" in result.stdout.lower()
        assert result.exit_code == 0

    @patch("paramiko.SSHClient")
    def test_run_command_success(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test running a command successfully."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock transport
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport

        # Mock exec_command
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"command output"
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""

        mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        result = ssh_manager.run(host, "echo test")

        assert result.success is True
        assert result.stdout == "command output"
        assert result.exit_code == 0

    @patch("paramiko.SSHClient")
    def test_connection_pooling(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test that connections are pooled."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport

        # Get client twice
        client1 = ssh_manager.get_client(host)
        client2 = ssh_manager.get_client(host)

        # Should be the same pooled client
        assert client1 is client2
        # Should only connect once
        assert mock_client.connect.call_count == 1

    @patch("paramiko.SSHClient")
    def test_close_connection(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test closing a specific connection."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport

        ssh_manager.get_client(host)
        assert host.name in ssh_manager.active_connections

        ssh_manager.close(host.name)
        assert host.name not in ssh_manager.active_connections
        mock_client.close.assert_called()

    @patch("paramiko.SSHClient")
    def test_close_all(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test closing all connections."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport

        ssh_manager.get_client(host)
        ssh_manager.close_all()

        assert ssh_manager.active_connections == []

    @patch("paramiko.SSHClient")
    def test_test_connection_success(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test successful connection test."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"ok"
        mock_client.exec_command.return_value = (MagicMock(), mock_stdout, MagicMock())

        success, message = ssh_manager.test_connection(host)

        assert success is True
        assert "Connected" in message

    @patch("paramiko.SSHClient")
    def test_test_connection_failure(
        self,
        mock_client_class: MagicMock,
        ssh_manager: SSHManager,
        host: Host,
    ) -> None:
        """Test failed connection test."""
        import paramiko

        mock_client = MagicMock()
        mock_client.connect.side_effect = paramiko.AuthenticationException()
        mock_client_class.return_value = mock_client

        success, message = ssh_manager.test_connection(host)

        assert success is False
        assert "Authentication failed" in message

    def test_context_manager(self) -> None:
        """Test SSHManager as context manager."""
        with SSHManager() as manager:
            assert manager is not None
        # close_all should have been called
