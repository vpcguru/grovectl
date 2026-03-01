"""Tests for SSH connection management."""

from __future__ import annotations

from subprocess import CompletedProcess
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
        with patch.object(SSHManager, "close_all") as mock_close_all:
            with SSHManager() as manager:
                assert manager is not None
            mock_close_all.assert_called_once()


class TestHostIsLocal:
    """Tests for the Host.is_local property."""

    def test_localhost_is_local(self) -> None:
        host = Host(name="local", hostname="localhost")
        assert host.is_local is True

    def test_loopback_ipv4_is_local(self) -> None:
        host = Host(name="local", hostname="127.0.0.1")
        assert host.is_local is True

    def test_loopback_ipv6_is_local(self) -> None:
        host = Host(name="local", hostname="::1")
        assert host.is_local is True

    def test_remote_ip_is_not_local(self) -> None:
        host = Host(name="remote", hostname="192.168.1.100")
        assert host.is_local is False

    def test_remote_hostname_is_not_local(self) -> None:
        host = Host(name="remote", hostname="mac-builder.internal")
        assert host.is_local is False


class TestSSHManagerLocalExecution:
    """Tests for local (subprocess) execution path in SSHManager."""

    @pytest.fixture
    def ssh_manager(self) -> SSHManager:
        return SSHManager()

    @pytest.fixture
    def local_host(self) -> Host:
        return Host(name="local-tart", hostname="localhost", username="admin")

    @pytest.fixture
    def remote_host(self) -> Host:
        return Host(name="remote", hostname="192.168.1.100", username="admin")

    # --- _run_local ---

    @patch("subprocess.run")
    def test_run_local_success(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """Local command success populates SSHResult correctly."""
        mock_subprocess.return_value = CompletedProcess(
            args=[], returncode=0, stdout="output\n", stderr=""
        )

        result = ssh_manager._run_local("tart list --format json", local_host.name)

        assert result.success is True
        assert result.stdout == "output"
        assert result.exit_code == 0
        assert result.host == local_host.name
        mock_subprocess.assert_called_once_with(
            ["tart", "list", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_run_local_failure(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """Local command failure sets exit code and stderr."""
        mock_subprocess.return_value = CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error message\n"
        )

        result = ssh_manager._run_local("tart list --format json", local_host.name)

        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "error message"

    @patch("subprocess.run")
    def test_run_local_dry_run(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """Dry-run mode skips subprocess and returns success."""
        result = ssh_manager._run_local("tart list", local_host.name, dry_run=True)

        mock_subprocess.assert_not_called()
        assert result.success is True
        assert "dry-run" in result.stdout.lower()

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_run_local_command_not_found(
        self, _mock: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """FileNotFoundError returns exit_code 127 with helpful message."""
        result = ssh_manager._run_local("tart list", local_host.name)

        assert result.exit_code == 127
        assert result.success is False
        assert "tart not found" in result.stderr

    # --- run() dispatching ---

    @patch("subprocess.run")
    def test_run_dispatches_to_local_for_localhost(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """run() uses subprocess (not SSH) when host.is_local is True."""
        mock_subprocess.return_value = CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr=""
        )

        with patch.object(ssh_manager, "get_client") as mock_get_client:
            result = ssh_manager.run(local_host, "tart list --format json")

        mock_get_client.assert_not_called()
        mock_subprocess.assert_called_once()
        assert result.success is True

    @patch("subprocess.run")
    def test_run_does_not_use_local_for_remote_host(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, remote_host: Host
    ) -> None:
        """run() does not call subprocess for a remote host."""
        with patch.object(ssh_manager, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_stdout = MagicMock()
            mock_stdout.read.return_value = b"output"
            mock_stdout.channel.recv_exit_status.return_value = 0
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""
            mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

            ssh_manager.run(remote_host, "tart list")

        mock_subprocess.assert_not_called()
        mock_get_client.assert_called_once()

    # --- test_connection() dispatching ---

    @patch("subprocess.run")
    def test_test_connection_local_tart_found(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """test_connection returns success when tart --version works locally."""
        mock_subprocess.return_value = CompletedProcess(
            args=[], returncode=0, stdout="tart 2.5.0\n", stderr=""
        )

        success, message = ssh_manager.test_connection(local_host)

        assert success is True
        assert "Local tart available" in message
        assert "tart 2.5.0" in message

    @patch("subprocess.run")
    def test_test_connection_local_tart_missing(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """test_connection returns failure when tart is not installed."""
        mock_subprocess.return_value = CompletedProcess(
            args=[], returncode=127, stdout="", stderr="command not found"
        )

        success, message = ssh_manager.test_connection(local_host)

        assert success is False
        assert "tart not found locally" in message

    @patch("subprocess.run")
    def test_test_connection_does_not_use_ssh_for_localhost(
        self, mock_subprocess: MagicMock, ssh_manager: SSHManager, local_host: Host
    ) -> None:
        """test_connection skips paramiko entirely for local hosts."""
        mock_subprocess.return_value = CompletedProcess(
            args=[], returncode=0, stdout="tart 2.5.0", stderr=""
        )

        with patch.object(ssh_manager, "_create_client") as mock_create:
            ssh_manager.test_connection(local_host)

        mock_create.assert_not_called()
