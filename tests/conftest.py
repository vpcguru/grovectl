"""Pytest configuration and fixtures for grovectl tests.

This module provides shared fixtures for testing grovectl components
including mocked SSH connections, sample configurations, and test data.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import yaml

from grovectl.core.config import ConfigManager
from grovectl.core.ssh import SSHManager, SSHResult
from grovectl.models.host import Host
from grovectl.models.vm import VM, VMState

if TYPE_CHECKING:
    from collections.abc import Generator

    from click.testing import CliRunner


@pytest.fixture
def sample_host() -> Host:
    """Create a sample Host for testing."""
    return Host(
        name="test-host",
        hostname="192.168.1.100",
        username="admin",
        port=22,
        ssh_key="~/.ssh/id_rsa",
    )


@pytest.fixture
def sample_hosts() -> list[Host]:
    """Create a list of sample hosts for testing."""
    return [
        Host(
            name="mac-builder-1",
            hostname="192.168.1.100",
            username="admin",
            ssh_key="~/.ssh/id_rsa",
        ),
        Host(
            name="mac-builder-2",
            hostname="192.168.1.101",
            username="admin",
            ssh_key="~/.ssh/id_rsa",
        ),
    ]


@pytest.fixture
def sample_vm() -> VM:
    """Create a sample VM for testing."""
    return VM(
        name="test-vm",
        host="mac-builder-1",
        state=VMState.RUNNING,
        cpu=4,
        memory=8192,
        disk=50,
        ip_address="192.168.64.10",
    )


@pytest.fixture
def sample_vms() -> list[VM]:
    """Create a list of sample VMs for testing."""
    return [
        VM(
            name="vm-1",
            host="mac-builder-1",
            state=VMState.RUNNING,
            cpu=4,
            memory=8192,
        ),
        VM(
            name="vm-2",
            host="mac-builder-1",
            state=VMState.STOPPED,
            cpu=2,
            memory=4096,
        ),
        VM(
            name="test-vm",
            host="mac-builder-2",
            state=VMState.RUNNING,
            cpu=8,
            memory=16384,
        ),
    ]


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_data(sample_hosts: list[Host]) -> dict:
    """Create sample configuration data."""
    return {
        "hosts": [h.to_dict() for h in sample_hosts],
        "defaults": {
            "vm_cpu": 4,
            "vm_memory": 8192,
            "vm_disk": 50,
            "timeout": 300,
        },
        "logging": {
            "level": "INFO",
            "file": None,
        },
    }


@pytest.fixture
def temp_config_file(
    temp_config_dir: Path, sample_config_data: dict
) -> Generator[Path, None, None]:
    """Create a temporary config file with sample data."""
    config_path = temp_config_dir / "config.yaml"
    with config_path.open("w") as f:
        yaml.safe_dump(sample_config_data, f)
    yield config_path


@pytest.fixture
def config_manager(temp_config_file: Path) -> ConfigManager:
    """Create a ConfigManager with a temporary config file."""
    return ConfigManager(temp_config_file)


@pytest.fixture
def mock_ssh_result_success() -> SSHResult:
    """Create a successful SSH result."""
    return SSHResult(
        stdout="output",
        stderr="",
        exit_code=0,
        host="test-host",
        command="echo test",
    )


@pytest.fixture
def mock_ssh_result_failure() -> SSHResult:
    """Create a failed SSH result."""
    return SSHResult(
        stdout="",
        stderr="error message",
        exit_code=1,
        host="test-host",
        command="false",
    )


@pytest.fixture
def mock_ssh_manager() -> Generator[SSHManager, None, None]:
    """Create a mocked SSH manager."""
    with patch.object(SSHManager, "__init__", lambda self, **kwargs: None):
        manager = SSHManager()
        manager._pool = {}
        manager._lock = MagicMock()
        manager.default_timeout = 30
        manager.pool_max_age = 300
        yield manager


@pytest.fixture
def mock_ssh_client() -> MagicMock:
    """Create a mocked Paramiko SSH client."""
    client = MagicMock()
    transport = MagicMock()
    transport.is_active.return_value = True
    client.get_transport.return_value = transport

    # Mock exec_command
    stdout = MagicMock()
    stdout.read.return_value = b"output"
    stdout.channel.recv_exit_status.return_value = 0

    stderr = MagicMock()
    stderr.read.return_value = b""

    client.exec_command.return_value = (MagicMock(), stdout, stderr)

    return client


@pytest.fixture
def tart_list_json_output() -> str:
    """Sample JSON output from 'tart list --format json'."""
    return """[
        {
            "Name": "vm-1",
            "State": "running",
            "CPU": 4,
            "Memory": 8192,
            "Disk": 50,
            "Source": "ghcr.io/cirruslabs/macos-sonoma-base:latest"
        },
        {
            "Name": "vm-2",
            "State": "stopped",
            "CPU": 2,
            "Memory": 4096,
            "Disk": 25,
            "Source": "template-vm"
        }
    ]"""


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click test runner."""
    from click.testing import CliRunner

    return CliRunner()
