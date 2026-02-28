"""Configuration management for grovectl.

This module provides a Pydantic-based configuration system that supports:
- YAML configuration files
- Environment variable overrides
- Default values with validation
- Automatic directory creation

The default config location is ~/.grovectl/config.yaml, which can be
overridden with the GROVECTL_CONFIG environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, Field, field_validator

from grovectl.core.exceptions import ConfigNotFoundError, ConfigurationError
from grovectl.models.host import Host


def get_default_config_path() -> Path:
    """Get the default configuration file path.

    The path can be overridden by setting the GROVECTL_CONFIG
    environment variable.

    Returns:
        Path to the configuration file.
    """
    env_path = os.environ.get("GROVECTL_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".grovectl" / "config.yaml"


def get_default_log_path() -> Path:
    """Get the default log file path.

    Returns:
        Path to the log file directory.
    """
    return Path.home() / ".grovectl" / "logs" / "grovectl.log"


class LoggingConfig(BaseModel):
    """Logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        file: Path to log file (optional).
    """

    level: str = Field(default="INFO", description="Log level")
    file: str | None = Field(default=None, description="Log file path")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


class DefaultsConfig(BaseModel):
    """Default values for VM creation and operations.

    Args:
        vm_cpu: Default CPU cores for new VMs.
        vm_memory: Default memory in MB for new VMs.
        vm_disk: Default disk size in GB for new VMs.
        timeout: Default timeout in seconds for operations.
    """

    vm_cpu: Annotated[int, Field(ge=1, le=64)] = Field(
        default=4, description="Default VM CPU cores"
    )
    vm_memory: Annotated[int, Field(ge=512, le=131072)] = Field(
        default=8192, description="Default VM memory in MB"
    )
    vm_disk: Annotated[int, Field(ge=10, le=2048)] = Field(
        default=50, description="Default VM disk size in GB"
    )
    timeout: Annotated[int, Field(ge=10, le=3600)] = Field(
        default=300, description="Default operation timeout in seconds"
    )


class Config(BaseModel):
    """Main configuration model for grovectl.

    This model represents the entire configuration file structure
    and provides validation for all configuration values.

    Args:
        hosts: List of configured remote hosts.
        defaults: Default values for VM operations.
        logging: Logging configuration.

    Example config.yaml:
        ```yaml
        hosts:
          - name: mac-builder-1
            hostname: 192.168.1.100
            username: admin
            ssh_key: ~/.ssh/id_rsa
            port: 22

        defaults:
          vm_cpu: 4
          vm_memory: 8192
          vm_disk: 50
          timeout: 300

        logging:
          level: INFO
          file: ~/.grovectl/logs/grovectl.log
        ```
    """

    hosts: list[Host] = Field(default_factory=list, description="Configured hosts")
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig, description="Default values")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging config")

    def get_host(self, name: str) -> Host | None:
        """Get a host by name.

        Args:
            name: The name of the host.

        Returns:
            The Host if found, None otherwise.
        """
        for host in self.hosts:
            if host.name == name:
                return host
        return None

    @property
    def host_names(self) -> list[str]:
        """List of all configured host names."""
        return [h.name for h in self.hosts]


class ConfigManager:
    """Manages reading and writing grovectl configuration.

    This class handles:
    - Loading configuration from YAML files
    - Saving configuration changes
    - Validating configuration with Pydantic
    - Creating default configuration directories

    Args:
        path: Optional path to config file. Uses default if not specified.

    Attributes:
        path: Path to the configuration file.
        config: The loaded and validated Config object.

    Example:
        >>> cm = ConfigManager()
        >>> print(cm.config.hosts)
        []
        >>> cm.add_host(Host(name="test", hostname="192.168.1.1"))
        >>> cm.save()
    """

    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            self.path = get_default_config_path()
        else:
            self.path = Path(path).expanduser()

        self._ensure_config_dir()
        self.config = self._load_or_create()

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_or_create(self) -> Config:
        """Load config from file or create default.

        Returns:
            Loaded or default Config object.
        """
        if self.path.exists():
            return self._load()
        return Config()

    def _load(self) -> Config:
        """Load and validate configuration from file.

        Returns:
            Validated Config object.

        Raises:
            ConfigurationError: If the config file is invalid.
            ConfigNotFoundError: If the config file doesn't exist.
        """
        if not self.path.exists():
            raise ConfigNotFoundError(str(self.path))

        try:
            with self.path.open("r") as f:
                data = yaml.safe_load(f) or {}
            return Config.model_validate(data)
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in config file: {e}",
                details={"path": str(self.path)},
            ) from e
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load config: {e}",
                details={"path": str(self.path)},
            ) from e

    def save(self) -> None:
        """Save current configuration to file.

        Raises:
            ConfigurationError: If saving fails.
        """
        try:
            data = self.config.model_dump(exclude_none=True)
            # Convert Host objects to dicts
            if "hosts" in data:
                data["hosts"] = [h if isinstance(h, dict) else h for h in data["hosts"]]

            with self.path.open("w") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to save config: {e}",
                details={"path": str(self.path)},
            ) from e

    def reload(self) -> None:
        """Reload configuration from disk."""
        self.config = self._load_or_create()

    def add_host(self, host: Host) -> None:
        """Add a new host to the configuration.

        Args:
            host: The Host to add.

        Raises:
            ConfigurationError: If a host with the same name exists.
        """
        if self.config.get_host(host.name) is not None:
            raise ConfigurationError(
                f"Host '{host.name}' already exists",
                details={"host_name": host.name},
            )
        self.config.hosts.append(host)
        self.save()

    def remove_host(self, name: str) -> bool:
        """Remove a host by name.

        Args:
            name: The name of the host to remove.

        Returns:
            True if removed, False if not found.
        """
        for i, host in enumerate(self.config.hosts):
            if host.name == name:
                del self.config.hosts[i]
                self.save()
                return True
        return False

    def get_host(self, name: str) -> Host | None:
        """Get a host by name.

        Args:
            name: The name of the host.

        Returns:
            The Host if found, None otherwise.
        """
        return self.config.get_host(name)

    @property
    def hosts(self) -> list[Host]:
        """List of all configured hosts."""
        return self.config.hosts

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of the config.
        """
        return self.config.model_dump(exclude_none=True)

    @classmethod
    def create_example_config(cls, path: Path | None = None) -> Path:
        """Create an example configuration file.

        Args:
            path: Optional path for the config. Uses default if not specified.

        Returns:
            Path to the created config file.
        """
        path = get_default_config_path() if path is None else Path(path).expanduser()

        path.parent.mkdir(parents=True, exist_ok=True)

        example_config = {
            "hosts": [
                {
                    "name": "mac-builder-1",
                    "hostname": "192.168.1.100",
                    "username": "admin",
                    "ssh_key": "~/.ssh/id_rsa",
                    "port": 22,
                },
                {
                    "name": "mac-builder-2",
                    "hostname": "192.168.1.101",
                    "username": "admin",
                    "ssh_key": "~/.ssh/id_rsa",
                    "port": 22,
                },
            ],
            "defaults": {
                "vm_cpu": 4,
                "vm_memory": 8192,
                "vm_disk": 50,
                "timeout": 300,
            },
            "logging": {
                "level": "INFO",
                "file": str(get_default_log_path()),
            },
        }

        with path.open("w") as f:
            yaml.safe_dump(example_config, f, default_flow_style=False, sort_keys=False)

        return path
