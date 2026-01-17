"""Tests for VM CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from grovectl.cli.main import cli
from grovectl.models.vm import VM, VMState


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_vm_manager():
    """Create a mock VM manager."""
    with patch("grovectl.cli.main.Context.init_vm_manager") as mock:
        manager = MagicMock()
        mock.return_value = manager
        yield manager


class TestVMList:
    """Tests for 'grovectl vm list' command."""

    def test_list_vms_table(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test listing VMs in table format."""
        mock_vm_manager.list_vms.return_value = [
            VM(name="vm-1", host="mac-builder-1", state=VMState.RUNNING),
            VM(name="vm-2", host="mac-builder-1", state=VMState.STOPPED),
        ]

        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "vm", "list"],
        )

        assert result.exit_code == 0
        assert "vm-1" in result.output
        assert "vm-2" in result.output

    def test_list_vms_with_host_filter(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test listing VMs filtered by host."""
        mock_vm_manager.list_vms.return_value = [
            VM(name="vm-1", host="mac-builder-1", state=VMState.RUNNING),
        ]

        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "vm", "list", "--host", "mac-builder-1"],
        )

        assert result.exit_code == 0
        mock_vm_manager.list_vms.assert_called_with(
            host_name="mac-builder-1",
            pattern=None,
            show_progress=True,
        )

    def test_list_vms_json(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test listing VMs in JSON format."""
        mock_vm_manager.list_vms.return_value = [
            VM(name="vm-1", host="mac-builder-1", state=VMState.RUNNING),
        ]

        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "vm", "list", "--format", "json"],
        )

        assert result.exit_code == 0
        assert "vm-1" in result.output

    def test_list_vms_empty(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test listing VMs when none exist."""
        mock_vm_manager.list_vms.return_value = []

        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "vm", "list"],
        )

        assert result.exit_code == 0
        assert "No VMs found" in result.output


class TestVMStart:
    """Tests for 'grovectl vm start' command."""

    def test_start_vm(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test starting a VM."""
        mock_vm_manager.start_vm.return_value = VM(
            name="vm-1",
            host="mac-builder-1",
            state=VMState.STARTING,
        )

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "start",
                "vm-1",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 0
        assert "Started" in result.output

    def test_start_vm_dry_run(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test starting a VM in dry-run mode."""
        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "--dry-run",
                "vm",
                "start",
                "vm-1",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        mock_vm_manager.start_vm.assert_not_called()


class TestVMStop:
    """Tests for 'grovectl vm stop' command."""

    def test_stop_vm(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test stopping a VM."""
        mock_vm_manager.stop_vm.return_value = VM(
            name="vm-1",
            host="mac-builder-1",
            state=VMState.STOPPED,
        )

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "stop",
                "vm-1",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 0
        assert "Stopped" in result.output

    def test_stop_vm_force(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test force stopping a VM."""
        mock_vm_manager.stop_vm.return_value = VM(
            name="vm-1",
            host="mac-builder-1",
            state=VMState.STOPPED,
        )

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "stop",
                "vm-1",
                "--host",
                "mac-builder-1",
                "--force",
            ],
        )

        assert result.exit_code == 0
        assert "Force stopped" in result.output


class TestVMDelete:
    """Tests for 'grovectl vm delete' command."""

    def test_delete_vm_with_yes(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test deleting a VM with --yes flag."""
        mock_vm_manager.delete_vm.return_value = True

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "delete",
                "vm-1",
                "--host",
                "mac-builder-1",
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_vm_with_confirmation(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test deleting a VM with confirmation."""
        mock_vm_manager.delete_vm.return_value = True

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "delete",
                "vm-1",
                "--host",
                "mac-builder-1",
            ],
            input="y\n",
        )

        assert result.exit_code == 0


class TestVMStatus:
    """Tests for 'grovectl vm status' command."""

    def test_status_vm(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test getting VM status."""
        mock_vm_manager.get_vm.return_value = VM(
            name="vm-1",
            host="mac-builder-1",
            state=VMState.RUNNING,
            cpu=4,
            memory=8192,
        )
        mock_vm_manager.get_vm_ip.return_value = "192.168.64.10"

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "status",
                "vm-1",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 0
        assert "vm-1" in result.output

    def test_status_vm_not_found(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test getting status of non-existent VM."""
        mock_vm_manager.get_vm.return_value = None

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "status",
                "nonexistent",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.output


class TestVMClone:
    """Tests for 'grovectl vm clone' command."""

    def test_clone_vm(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test cloning a VM."""
        mock_vm_manager.clone_vm.return_value = VM(
            name="new-vm",
            host="mac-builder-1",
            state=VMState.STOPPED,
        )

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "clone",
                "source-vm",
                "new-vm",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 0
        assert "Cloned" in result.output


class TestVMIP:
    """Tests for 'grovectl vm ip' command."""

    def test_get_vm_ip(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test getting VM IP."""
        mock_vm_manager.get_vm_ip.return_value = "192.168.64.10"

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "ip",
                "vm-1",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 0
        assert "192.168.64.10" in result.output

    def test_get_vm_ip_not_available(
        self,
        runner: CliRunner,
        temp_config_file: Path,
        mock_vm_manager: MagicMock,
    ) -> None:
        """Test when VM IP is not available."""
        mock_vm_manager.get_vm_ip.return_value = None

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "vm",
                "ip",
                "vm-1",
                "--host",
                "mac-builder-1",
            ],
        )

        assert result.exit_code == 1
        assert "No IP address" in result.output
