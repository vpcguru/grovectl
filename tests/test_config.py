"""Tests for configuration management."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from grovectl.core.config import Config, ConfigManager, DefaultsConfig, LoggingConfig
from grovectl.core.exceptions import ConfigNotFoundError, ConfigurationError
from grovectl.models.host import Host


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_default_values(self) -> None:
        """Test default logging configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file is None

    def test_valid_log_levels(self) -> None:
        """Test that valid log levels are accepted."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_log_level_case_insensitive(self) -> None:
        """Test that log levels are case-insensitive."""
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"

    def test_invalid_log_level(self) -> None:
        """Test that invalid log levels raise an error."""
        with pytest.raises(ValueError, match="Invalid log level"):
            LoggingConfig(level="INVALID")


class TestDefaultsConfig:
    """Tests for DefaultsConfig model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = DefaultsConfig()
        assert config.vm_cpu == 4
        assert config.vm_memory == 8192
        assert config.vm_disk == 50
        assert config.timeout == 300

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = DefaultsConfig(
            vm_cpu=8,
            vm_memory=16384,
            vm_disk=100,
            timeout=600,
        )
        assert config.vm_cpu == 8
        assert config.vm_memory == 16384
        assert config.vm_disk == 100
        assert config.timeout == 600

    def test_validation_constraints(self) -> None:
        """Test that validation constraints are enforced."""
        with pytest.raises(ValueError):
            DefaultsConfig(vm_cpu=0)  # Must be >= 1

        with pytest.raises(ValueError):
            DefaultsConfig(vm_memory=256)  # Must be >= 512


class TestConfig:
    """Tests for Config model."""

    def test_empty_config(self) -> None:
        """Test creating an empty configuration."""
        config = Config()
        assert config.hosts == []
        assert config.defaults.vm_cpu == 4
        assert config.logging.level == "INFO"

    def test_config_with_hosts(self, sample_hosts: list[Host]) -> None:
        """Test configuration with hosts."""
        config = Config(hosts=sample_hosts)
        assert len(config.hosts) == 2
        assert config.host_names == ["mac-builder-1", "mac-builder-2"]

    def test_get_host(self, sample_hosts: list[Host]) -> None:
        """Test retrieving a host by name."""
        config = Config(hosts=sample_hosts)

        host = config.get_host("mac-builder-1")
        assert host is not None
        assert host.hostname == "192.168.1.100"

        # Non-existent host
        assert config.get_host("nonexistent") is None


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_load_config(self, temp_config_file: Path) -> None:
        """Test loading configuration from file."""
        manager = ConfigManager(temp_config_file)
        assert len(manager.hosts) == 2
        assert manager.config.defaults.vm_cpu == 4

    def test_create_default_config(self, temp_config_dir: Path) -> None:
        """Test creating a default configuration when file doesn't exist."""
        config_path = temp_config_dir / "new_config.yaml"
        manager = ConfigManager(config_path)

        # Default config should be created in memory
        assert manager.config is not None
        assert manager.hosts == []

    def test_save_config(self, temp_config_dir: Path) -> None:
        """Test saving configuration to file."""
        config_path = temp_config_dir / "save_test.yaml"
        manager = ConfigManager(config_path)

        # Add a host
        host = Host(name="new-host", hostname="192.168.1.200")
        manager.add_host(host)

        # Reload and verify
        manager.reload()
        assert len(manager.hosts) == 1
        assert manager.hosts[0].name == "new-host"

    def test_add_duplicate_host(self, config_manager: ConfigManager) -> None:
        """Test that adding a duplicate host raises an error."""
        with pytest.raises(ConfigurationError, match="already exists"):
            config_manager.add_host(
                Host(name="mac-builder-1", hostname="192.168.1.200")
            )

    def test_remove_host(self, config_manager: ConfigManager) -> None:
        """Test removing a host."""
        assert config_manager.remove_host("mac-builder-1") is True
        assert len(config_manager.hosts) == 1

        # Removing non-existent host returns False
        assert config_manager.remove_host("nonexistent") is False

    def test_get_host(self, config_manager: ConfigManager) -> None:
        """Test getting a host by name."""
        host = config_manager.get_host("mac-builder-1")
        assert host is not None
        assert host.hostname == "192.168.1.100"

    def test_invalid_yaml(self, temp_config_dir: Path) -> None:
        """Test loading invalid YAML raises error."""
        config_path = temp_config_dir / "invalid.yaml"
        config_path.write_text("{ invalid yaml content")

        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            ConfigManager(config_path)

    def test_create_example_config(self, temp_config_dir: Path) -> None:
        """Test creating an example configuration file."""
        config_path = temp_config_dir / "example.yaml"
        result = ConfigManager.create_example_config(config_path)

        assert result == config_path
        assert config_path.exists()

        # Verify it's valid
        manager = ConfigManager(config_path)
        assert len(manager.hosts) == 2

    def test_to_dict(self, config_manager: ConfigManager) -> None:
        """Test converting configuration to dictionary."""
        data = config_manager.to_dict()

        assert "hosts" in data
        assert "defaults" in data
        assert "logging" in data
        assert len(data["hosts"]) == 2
