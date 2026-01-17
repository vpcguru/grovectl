"""VM Manager for controlling VMs via SSH.

This module provides the VMManager class that orchestrates VM operations
on remote hosts using the tart CLI via SSH.
"""

from __future__ import annotations

import fnmatch
import json
from typing import TYPE_CHECKING

from grovectl.core.exceptions import (
    HostNotFoundError,
    VMNotFoundError,
    VMOperationError,
    VMStartError,
    VMStopError,
)
from grovectl.core.ssh import SSHManager, SSHResult
from grovectl.models.host import Host
from grovectl.models.vm import VM, VMState
from grovectl.utils.logging import get_logger
from grovectl.utils.output import create_spinner_progress

if TYPE_CHECKING:
    from grovectl.core.config import ConfigManager

logger = get_logger("vm_manager")


class VMManager:
    """Manages VM operations across multiple hosts.

    This class provides high-level operations for managing VMs on
    remote macOS hosts via SSH, using the tart virtualization tool.

    Args:
        config_manager: Configuration manager with host settings.
        ssh_manager: SSH manager for remote command execution.
        dry_run: If True, don't execute actual commands.

    Example:
        >>> from grovectl.core.config import ConfigManager
        >>> from grovectl.core.ssh import SSHManager
        >>>
        >>> config = ConfigManager()
        >>> ssh = SSHManager()
        >>> vm_mgr = VMManager(config, ssh)
        >>>
        >>> # List VMs on a specific host
        >>> vms = vm_mgr.list_vms(host_name="mac-builder-1")
        >>>
        >>> # Start a VM
        >>> vm_mgr.start_vm("my-vm", host_name="mac-builder-1")
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        ssh_manager: SSHManager | None = None,
        dry_run: bool = False,
    ) -> None:
        self.config = config_manager
        self.ssh = ssh_manager or SSHManager()
        self.dry_run = dry_run

    def _get_host(self, host_name: str) -> Host:
        """Get a host by name, raising if not found.

        Args:
            host_name: Name of the host.

        Returns:
            The Host object.

        Raises:
            HostNotFoundError: If host is not in configuration.
        """
        host = self.config.get_host(host_name)
        if host is None:
            raise HostNotFoundError(host_name)
        return host

    def _run_tart(
        self,
        host: Host,
        subcommand: str,
        args: list[str] | None = None,
        json_output: bool = False,
    ) -> SSHResult:
        """Run a tart command on a host.

        Args:
            host: Host to run command on.
            subcommand: Tart subcommand (list, run, stop, etc.).
            args: Additional arguments.
            json_output: Add --format json flag.

        Returns:
            SSHResult from the command.
        """
        cmd_parts = ["tart", subcommand]

        if json_output:
            cmd_parts.extend(["--format", "json"])

        if args:
            cmd_parts.extend(args)

        cmd = " ".join(cmd_parts)
        return self.ssh.run(host, cmd, dry_run=self.dry_run)

    def _parse_tart_list(self, output: str, host_name: str) -> list[VM]:
        """Parse tart list JSON output into VM objects.

        Args:
            output: JSON output from tart list.
            host_name: Name of the host.

        Returns:
            List of VM objects.
        """
        if not output or output.startswith("[dry-run"):
            return []

        try:
            data = json.loads(output)
            vms = []

            for item in data:
                name = item.get("Name", "unknown")
                vm = VM.from_tart_output(name, host_name, item)
                vms.append(vm)

            return vms

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse tart list output: {e}")
            return []

    def list_vms(
        self,
        host_name: str | None = None,
        pattern: str | None = None,
        show_progress: bool = False,
    ) -> list[VM]:
        """List VMs on one or all configured hosts.

        Args:
            host_name: Specific host to query (None for all hosts).
            pattern: Optional glob pattern to filter VM names.
            show_progress: Show spinner during operation.

        Returns:
            List of VM objects.

        Raises:
            HostNotFoundError: If specified host is not found.
        """
        if host_name:
            hosts = [self._get_host(host_name)]
        else:
            hosts = self.config.hosts

        if not hosts:
            logger.warning("No hosts configured")
            return []

        all_vms: list[VM] = []

        if show_progress:
            progress = create_spinner_progress()
            with progress:
                task = progress.add_task("Fetching VMs...", total=None)
                for host in hosts:
                    vms = self._list_vms_on_host(host)
                    all_vms.extend(vms)
                progress.update(task, completed=True)
        else:
            for host in hosts:
                vms = self._list_vms_on_host(host)
                all_vms.extend(vms)

        # Apply pattern filter
        if pattern:
            all_vms = [vm for vm in all_vms if fnmatch.fnmatch(vm.name, pattern)]

        return all_vms

    def _list_vms_on_host(self, host: Host) -> list[VM]:
        """List VMs on a specific host.

        Args:
            host: Host to query.

        Returns:
            List of VM objects.
        """
        try:
            result = self._run_tart(host, "list", json_output=True)

            if not result.success:
                logger.warning(f"Failed to list VMs on {host.name}: {result.stderr}")
                return []

            return self._parse_tart_list(result.stdout, host.name)

        except Exception as e:
            logger.error(f"Error listing VMs on {host.name}: {e}")
            return []

    def get_vm(self, name: str, host_name: str) -> VM | None:
        """Get a specific VM by name.

        Args:
            name: Name of the VM.
            host_name: Host where VM resides.

        Returns:
            VM object if found, None otherwise.
        """
        vms = self.list_vms(host_name=host_name)
        for vm in vms:
            if vm.name == name:
                return vm
        return None

    def start_vm(
        self,
        name: str,
        host_name: str,
        show_progress: bool = True,
    ) -> VM:
        """Start a VM.

        Args:
            name: Name of the VM to start.
            host_name: Host where VM resides.
            show_progress: Show spinner during operation.

        Returns:
            Updated VM object.

        Raises:
            VMNotFoundError: If VM is not found.
            VMStartError: If start fails.
        """
        host = self._get_host(host_name)

        if show_progress:
            progress = create_spinner_progress()
            with progress:
                task = progress.add_task(f"Starting {name}...", total=None)
                result = self._run_tart(host, "run", [name, "--no-graphics"])
                progress.update(task, completed=True)
        else:
            result = self._run_tart(host, "run", [name, "--no-graphics"])

        if not result.success:
            if "not found" in result.stderr.lower():
                raise VMNotFoundError(name, host_name)
            raise VMStartError(name, result.stderr, host_name)

        logger.info(f"Started VM {name} on {host_name}")

        # Return updated VM status
        vm = self.get_vm(name, host_name)
        if vm:
            return vm

        # Return a synthetic VM object if we can't get status
        return VM(name=name, host=host_name, state=VMState.STARTING)

    def stop_vm(
        self,
        name: str,
        host_name: str,
        force: bool = False,
        show_progress: bool = True,
    ) -> VM:
        """Stop a VM.

        Args:
            name: Name of the VM to stop.
            host_name: Host where VM resides.
            force: Force stop (kill) the VM.
            show_progress: Show spinner during operation.

        Returns:
            Updated VM object.

        Raises:
            VMNotFoundError: If VM is not found.
            VMStopError: If stop fails.
        """
        host = self._get_host(host_name)

        args = [name]
        if force:
            args.append("--force")

        if show_progress:
            action = "Force stopping" if force else "Stopping"
            progress = create_spinner_progress()
            with progress:
                task = progress.add_task(f"{action} {name}...", total=None)
                result = self._run_tart(host, "stop", args)
                progress.update(task, completed=True)
        else:
            result = self._run_tart(host, "stop", args)

        if not result.success:
            if "not found" in result.stderr.lower():
                raise VMNotFoundError(name, host_name)
            raise VMStopError(name, result.stderr, host_name)

        logger.info(f"Stopped VM {name} on {host_name}")

        return VM(name=name, host=host_name, state=VMState.STOPPED)

    def delete_vm(
        self,
        name: str,
        host_name: str,
        show_progress: bool = True,
    ) -> bool:
        """Delete a VM.

        Args:
            name: Name of the VM to delete.
            host_name: Host where VM resides.
            show_progress: Show spinner during operation.

        Returns:
            True if deleted successfully.

        Raises:
            VMNotFoundError: If VM is not found.
            VMOperationError: If deletion fails.
        """
        host = self._get_host(host_name)

        if show_progress:
            progress = create_spinner_progress()
            with progress:
                task = progress.add_task(f"Deleting {name}...", total=None)
                result = self._run_tart(host, "delete", [name])
                progress.update(task, completed=True)
        else:
            result = self._run_tart(host, "delete", [name])

        if not result.success:
            if "not found" in result.stderr.lower():
                raise VMNotFoundError(name, host_name)
            raise VMOperationError(name, "delete", result.stderr, host_name)

        logger.info(f"Deleted VM {name} on {host_name}")
        return True

    def clone_vm(
        self,
        source: str,
        destination: str,
        host_name: str,
        show_progress: bool = True,
    ) -> VM:
        """Clone a VM.

        Args:
            source: Source VM or image name.
            destination: Name for the new VM.
            host_name: Host where to perform the clone.
            show_progress: Show spinner during operation.

        Returns:
            The newly created VM.

        Raises:
            VMOperationError: If clone fails.
        """
        host = self._get_host(host_name)

        if show_progress:
            progress = create_spinner_progress()
            with progress:
                task = progress.add_task(
                    f"Cloning {source} to {destination}...", total=None
                )
                result = self._run_tart(host, "clone", [source, destination])
                progress.update(task, completed=True)
        else:
            result = self._run_tart(host, "clone", [source, destination])

        if not result.success:
            raise VMOperationError(destination, "clone", result.stderr, host_name)

        logger.info(f"Cloned {source} to {destination} on {host_name}")

        return VM(name=destination, host=host_name, state=VMState.STOPPED)

    def get_vm_ip(
        self,
        name: str,
        host_name: str,
        show_progress: bool = True,
    ) -> str | None:
        """Get the IP address of a running VM.

        Args:
            name: Name of the VM.
            host_name: Host where VM resides.
            show_progress: Show spinner during operation.

        Returns:
            IP address string or None if not available.

        Raises:
            VMNotFoundError: If VM is not found.
        """
        host = self._get_host(host_name)

        if show_progress:
            progress = create_spinner_progress()
            with progress:
                task = progress.add_task(f"Getting IP for {name}...", total=None)
                result = self._run_tart(host, "ip", [name])
                progress.update(task, completed=True)
        else:
            result = self._run_tart(host, "ip", [name])

        if not result.success:
            if "not found" in result.stderr.lower():
                raise VMNotFoundError(name, host_name)
            logger.warning(f"Could not get IP for {name}: {result.stderr}")
            return None

        ip = result.stdout.strip()
        if ip and not ip.startswith("[dry-run"):
            return ip

        return None

    def create_vm(
        self,
        name: str,
        host_name: str,
        source_image: str,
        cpu: int | None = None,
        memory: int | None = None,
        disk: int | None = None,
        show_progress: bool = True,
    ) -> VM:
        """Create a new VM from an image.

        Args:
            name: Name for the new VM.
            host_name: Host where to create the VM.
            source_image: Source tart image to clone.
            cpu: Number of CPU cores (uses default if None).
            memory: Memory in MB (uses default if None).
            disk: Disk size in GB (uses default if None).
            show_progress: Show spinner during operation.

        Returns:
            The newly created VM.

        Raises:
            VMOperationError: If creation fails.
        """
        # Clone the image first
        vm = self.clone_vm(source_image, name, host_name, show_progress=show_progress)

        # Set resources if specified
        host = self._get_host(host_name)
        defaults = self.config.config.defaults

        cpu = cpu or defaults.vm_cpu
        memory = memory or defaults.vm_memory
        disk = disk or defaults.vm_disk

        # Configure VM resources using tart set
        set_args = [name, "--cpu", str(cpu), "--memory", str(memory)]

        if show_progress:
            progress = create_spinner_progress()
            with progress:
                task = progress.add_task(f"Configuring {name}...", total=None)
                result = self._run_tart(host, "set", set_args)
                progress.update(task, completed=True)
        else:
            result = self._run_tart(host, "set", set_args)

        if not result.success:
            logger.warning(f"Failed to configure VM resources: {result.stderr}")

        vm.cpu = cpu
        vm.memory = memory
        vm.disk = disk
        vm.source_image = source_image

        logger.info(f"Created VM {name} on {host_name}")
        return vm

    def batch_start(
        self,
        pattern: str,
        host_name: str | None = None,
    ) -> list[tuple[str, bool, str]]:
        """Start multiple VMs matching a pattern.

        Args:
            pattern: Glob pattern to match VM names.
            host_name: Specific host (None for all hosts).

        Returns:
            List of (vm_name, success, message) tuples.
        """
        vms = self.list_vms(host_name=host_name, pattern=pattern)
        results: list[tuple[str, bool, str]] = []

        for vm in vms:
            if vm.state == VMState.RUNNING:
                results.append((vm.name, True, "Already running"))
                continue

            try:
                self.start_vm(vm.name, vm.host, show_progress=False)
                results.append((vm.name, True, "Started"))
            except Exception as e:
                results.append((vm.name, False, str(e)))

        return results

    def batch_stop(
        self,
        pattern: str,
        host_name: str | None = None,
        force: bool = False,
    ) -> list[tuple[str, bool, str]]:
        """Stop multiple VMs matching a pattern.

        Args:
            pattern: Glob pattern to match VM names.
            host_name: Specific host (None for all hosts).
            force: Force stop VMs.

        Returns:
            List of (vm_name, success, message) tuples.
        """
        vms = self.list_vms(host_name=host_name, pattern=pattern)
        results: list[tuple[str, bool, str]] = []

        for vm in vms:
            if vm.state == VMState.STOPPED:
                results.append((vm.name, True, "Already stopped"))
                continue

            try:
                self.stop_vm(vm.name, vm.host, force=force, show_progress=False)
                results.append((vm.name, True, "Stopped"))
            except Exception as e:
                results.append((vm.name, False, str(e)))

        return results

    def close(self) -> None:
        """Clean up resources."""
        self.ssh.close_all()
