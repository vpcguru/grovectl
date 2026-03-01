"""Tests for hosts CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from grovectl.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def isolated_config(runner: CliRunner, _temp_config_file: Path) -> object:
    """Run CLI commands with isolated config."""
    return runner.isolated_filesystem()


class TestHostsAdd:
    """Tests for 'grovectl hosts add' command."""

    def test_add_host_basic(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test adding a host with basic options."""
        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "hosts",
                "add",
                "new-host",
                "192.168.1.200",
            ],
        )

        assert result.exit_code == 0
        assert "Added host" in result.output

    def test_add_host_with_options(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test adding a host with all options."""
        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "hosts",
                "add",
                "new-host",
                "192.168.1.200",
                "--username",
                "admin",
                "--ssh-key",
                "~/.ssh/id_rsa",
                "--port",
                "2222",
            ],
        )

        assert result.exit_code == 0
        assert "Added host" in result.output

    def test_add_duplicate_host(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test adding a duplicate host fails."""
        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "hosts",
                "add",
                "mac-builder-1",  # Already exists
                "192.168.1.200",
            ],
        )

        assert result.exit_code == 1
        assert "already exists" in result.output


class TestHostsList:
    """Tests for 'grovectl hosts list' command."""

    def test_list_hosts_table(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test listing hosts in table format."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "hosts", "list"],
        )

        assert result.exit_code == 0
        assert "mac-builder-1" in result.output
        assert "mac-builder-2" in result.output

    def test_list_hosts_json(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test listing hosts in JSON format."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "hosts", "list", "--format", "json"],
        )

        assert result.exit_code == 0
        assert "mac-builder-1" in result.output
        # Should be valid JSON structure
        assert "[" in result.output

    def test_list_hosts_yaml(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test listing hosts in YAML format."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "hosts", "list", "--format", "yaml"],
        )

        assert result.exit_code == 0
        assert "mac-builder-1" in result.output
        assert "name:" in result.output

    def test_list_hosts_empty(
        self,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test listing hosts when none configured."""
        config_path = temp_config_dir / "empty.yaml"
        config_path.write_text("hosts: []")

        result = runner.invoke(
            cli,
            ["--config", str(config_path), "hosts", "list"],
        )

        assert result.exit_code == 0
        assert "No hosts configured" in result.output


class TestHostsRemove:
    """Tests for 'grovectl hosts remove' command."""

    def test_remove_host(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test removing a host."""
        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "hosts",
                "remove",
                "mac-builder-1",
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_remove_nonexistent_host(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test removing a non-existent host fails."""
        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config_file),
                "hosts",
                "remove",
                "nonexistent",
                "--yes",
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_remove_host_with_confirmation(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test remove with confirmation prompt."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "hosts", "remove", "mac-builder-1"],
            input="y\n",
        )

        assert result.exit_code == 0


class TestHostsTest:
    """Tests for 'grovectl hosts test' command."""

    def test_test_host_not_found(
        self,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test testing a non-existent host."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "hosts", "test", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("grovectl.core.ssh.SSHManager.test_connection")
    def test_test_host_success(
        self,
        mock_test: MagicMock,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test successful connection test."""
        mock_test.return_value = (True, "Connected successfully")

        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "hosts", "test", "mac-builder-1"],
        )

        assert result.exit_code == 0
        assert "Connected" in result.output

    @patch("grovectl.core.ssh.SSHManager.test_connection")
    def test_test_host_failure(
        self,
        mock_test: MagicMock,
        runner: CliRunner,
        temp_config_file: Path,
    ) -> None:
        """Test failed connection test."""
        mock_test.return_value = (False, "Connection refused")

        result = runner.invoke(
            cli,
            ["--config", str(temp_config_file), "hosts", "test", "mac-builder-1"],
        )

        assert result.exit_code == 1
        assert "Connection refused" in result.output
