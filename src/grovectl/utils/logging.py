"""Logging configuration for grovectl.

This module provides multi-level logging support with both console
and file handlers. Verbosity can be controlled via CLI flags:
- No flag: WARNING only
- -v: INFO level
- -vv: DEBUG level
- -vvv: DEBUG level + SSH debug output
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Custom log format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module-level logger cache
_loggers: dict[str, logging.Logger] = {}


def get_log_level(verbosity: int) -> int:
    """Convert verbosity count to log level.

    Args:
        verbosity: Number of -v flags (0-3).

    Returns:
        Logging level constant.
    """
    levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: logging.DEBUG,  # Same as 2, but enables paramiko debug
    }
    return levels.get(min(verbosity, 3), logging.WARNING)


def configure_logging(
    verbosity: int = 0,
    log_file: str | Path | None = None,
    log_level: str | None = None,
) -> None:
    """Configure logging for grovectl.

    Sets up both console (stderr) and optional file logging handlers.
    The console handler respects the verbosity level, while the file
    handler always logs at DEBUG level.

    Args:
        verbosity: Number of -v flags from CLI (0-3).
        log_file: Optional path to log file.
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR).

    Example:
        >>> configure_logging(verbosity=2)  # DEBUG level
        >>> configure_logging(log_file="~/.grovectl/logs/app.log")
    """
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), logging.WARNING)
    else:
        level = get_log_level(verbosity)

    # Configure root logger
    root_logger = logging.getLogger("grovectl")
    root_logger.setLevel(logging.DEBUG)  # Capture all, handlers filter

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    )
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # Always debug in file
        file_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        )
        root_logger.addHandler(file_handler)

    # Configure paramiko logging for -vvv
    paramiko_logger = logging.getLogger("paramiko")
    if verbosity >= 3:
        paramiko_logger.setLevel(logging.DEBUG)
        paramiko_logger.addHandler(console_handler)
    else:
        paramiko_logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.

    Creates child loggers under the 'grovectl' namespace.

    Args:
        name: Name of the module (e.g., 'ssh', 'vm_manager').

    Returns:
        Configured logger instance.

    Example:
        >>> logger = get_logger("ssh")
        >>> logger.info("Connected to host")
    """
    full_name = f"grovectl.{name}" if not name.startswith("grovectl.") else name

    if full_name not in _loggers:
        _loggers[full_name] = logging.getLogger(full_name)

    return _loggers[full_name]


class LogContext:
    """Context manager for temporary log level changes.

    Useful for suppressing or increasing log output for
    specific operations.

    Args:
        logger_name: Name of the logger to modify.
        level: Temporary log level.

    Example:
        >>> with LogContext("grovectl.ssh", logging.ERROR):
        ...     # SSH operations with reduced logging
        ...     pass
    """

    def __init__(self, logger_name: str, level: int) -> None:
        self.logger = logging.getLogger(logger_name)
        self.level = level
        self.original_level: int | None = None

    def __enter__(self) -> LogContext:
        self.original_level = self.logger.level
        self.logger.setLevel(self.level)
        return self

    def __exit__(self, *args: object) -> None:
        if self.original_level is not None:
            self.logger.setLevel(self.original_level)
