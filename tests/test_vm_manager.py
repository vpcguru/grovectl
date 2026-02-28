"""Tests for VM manager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from grovectl.core.config import ConfigManager
from grovectl.core.exceptions import HostNotFoundError, VMNotFoundError
from grovectl.core.ssh import SSHManager, SSHResult
from grovectl.core.vm_manager import VMManager
from grovectl.models.vm import VMState


class TestVMManager:
    """Tests for VMManager."""

    @pytest.fixture
    def mock_ssh_manager(self) -> MagicMock:
        """Create a mocked SSH manager."""
        return MagicMock(spec=SSHManager)

    @pytest.fixture
    def vm_manager(
        self,
        config_manager: ConfigManager,
        mock_ssh_manager: MagicMock,
    ) -> VMManager:
        """Create a VMManager with mocked dependencies."""
        return VMManager(config_manager, mock_ssh_manager)

    def test_init(
        self,
        config_manager: ConfigManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test VMManager initialization."""
        vm_manager = VMManager(config_manager, mock_ssh_manager)

        assert vm_manager.config is config_manager
        assert vm_manager.ssh is mock_ssh_manager
        assert vm_manager.dry_run is False

    def test_init_with_dry_run(
        self,
        config_manager: ConfigManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test VMManager with dry-run mode."""
        vm_manager = VMManager(config_manager, mock_ssh_manager, dry_run=True)
        assert vm_manager.dry_run is True

    def test_get_host_success(
        self,
        vm_manager: VMManager,
    ) -> None:
        """Test getting an existing host."""
        host = vm_manager._get_host("mac-builder-1")
        assert host.name == "mac-builder-1"
        assert host.hostname == "192.168.1.100"

    def test_get_host_not_found(
        self,
        vm_manager: VMManager,
    ) -> None:
        """Test getting a non-existent host raises error."""
        with pytest.raises(HostNotFoundError) as exc_info:
            vm_manager._get_host("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_list_vms(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
        tart_list_json_output: str,
    ) -> None:
        """Test listing VMs."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout=tart_list_json_output,
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart list --format json",
        )

        vms = vm_manager.list_vms(host_name="mac-builder-1")

        assert len(vms) == 2
        assert vms[0].name == "vm-1"
        assert vms[0].state == VMState.RUNNING
        assert vms[1].name == "vm-2"
        assert vms[1].state == VMState.STOPPED

    def test_list_vms_with_pattern(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
        tart_list_json_output: str,
    ) -> None:
        """Test listing VMs with pattern filter."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout=tart_list_json_output,
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart list --format json",
        )

        vms = vm_manager.list_vms(host_name="mac-builder-1", pattern="vm-1")
        assert len(vms) == 1
        assert vms[0].name == "vm-1"

    def test_list_vms_empty(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test listing VMs when none exist."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="[]",
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart list --format json",
        )

        vms = vm_manager.list_vms(host_name="mac-builder-1")
        assert vms == []

    def test_start_vm(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test starting a VM."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="",
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart run vm-1 --no-graphics",
        )

        vm = vm_manager.start_vm("vm-1", "mac-builder-1", show_progress=False)

        assert vm.name == "vm-1"
        mock_ssh_manager.run.assert_called()

    def test_start_vm_not_found(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test starting a non-existent VM."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="",
            stderr="VM not found",
            exit_code=1,
            host="mac-builder-1",
            command="tart run nonexistent --no-graphics",
        )

        with pytest.raises(VMNotFoundError):
            vm_manager.start_vm("nonexistent", "mac-builder-1", show_progress=False)

    def test_stop_vm(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test stopping a VM."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="",
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart stop vm-1",
        )

        vm = vm_manager.stop_vm("vm-1", "mac-builder-1", show_progress=False)

        assert vm.name == "vm-1"
        assert vm.state == VMState.STOPPED

    def test_stop_vm_force(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test force stopping a VM."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="",
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart stop vm-1 --force",
        )

        vm_manager.stop_vm("vm-1", "mac-builder-1", force=True, show_progress=False)

        # Verify --force was included
        call_args = mock_ssh_manager.run.call_args
        assert "--force" in call_args[1].get("command", "") or any(
            "--force" in str(arg) for arg in call_args[0]
        )

    def test_delete_vm(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test deleting a VM."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="",
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart delete vm-1",
        )

        result = vm_manager.delete_vm("vm-1", "mac-builder-1", show_progress=False)

        assert result is True

    def test_clone_vm(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test cloning a VM."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="",
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart clone source-vm new-vm",
        )

        vm = vm_manager.clone_vm("source-vm", "new-vm", "mac-builder-1", show_progress=False)

        assert vm.name == "new-vm"
        assert vm.state == VMState.STOPPED

    def test_get_vm_ip(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test getting VM IP address."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="192.168.64.10",
            stderr="",
            exit_code=0,
            host="mac-builder-1",
            command="tart ip vm-1",
        )

        ip = vm_manager.get_vm_ip("vm-1", "mac-builder-1", show_progress=False)

        assert ip == "192.168.64.10"

    def test_get_vm_ip_not_available(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test getting IP when VM has no IP."""
        mock_ssh_manager.run.return_value = SSHResult(
            stdout="",
            stderr="No IP address available",
            exit_code=1,
            host="mac-builder-1",
            command="tart ip vm-1",
        )

        ip = vm_manager.get_vm_ip("vm-1", "mac-builder-1", show_progress=False)

        assert ip is None

    def test_batch_start(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test batch starting VMs."""
        # Mock list_vms - note: start_vm calls get_vm() internally to get updated status
        mock_ssh_manager.run.side_effect = [
            # First call for list (batch_start initial list)
            SSHResult(
                stdout='[{"Name": "test-1", "State": "stopped"}, {"Name": "test-2", "State": "stopped"}]',
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart list --format json",
            ),
            # Start test-1
            SSHResult(
                stdout="",
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart run test-1",
            ),
            # get_vm for test-1 (called by start_vm to return updated status)
            SSHResult(
                stdout='[{"Name": "test-1", "State": "running"}]',
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart list --format json",
            ),
            # Start test-2
            SSHResult(
                stdout="",
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart run test-2",
            ),
            # get_vm for test-2 (called by start_vm to return updated status)
            SSHResult(
                stdout='[{"Name": "test-2", "State": "running"}]',
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart list --format json",
            ),
        ]

        results = vm_manager.batch_start("test-*", host_name="mac-builder-1")

        assert len(results) == 2
        assert all(success for _, success, _ in results)

    def test_batch_stop(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test batch stopping VMs."""
        mock_ssh_manager.run.side_effect = [
            # First call for list
            SSHResult(
                stdout='[{"Name": "test-1", "State": "running"}, {"Name": "test-2", "State": "running"}]',
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart list --format json",
            ),
            # Stop calls
            SSHResult(
                stdout="",
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart stop test-1",
            ),
            SSHResult(
                stdout="",
                stderr="",
                exit_code=0,
                host="mac-builder-1",
                command="tart stop test-2",
            ),
        ]

        results = vm_manager.batch_stop("test-*", host_name="mac-builder-1")

        assert len(results) == 2
        assert all(success for _, success, _ in results)

    def test_close(
        self,
        vm_manager: VMManager,
        mock_ssh_manager: MagicMock,
    ) -> None:
        """Test cleanup."""
        vm_manager.close()
        mock_ssh_manager.close_all.assert_called_once()
