"""Logging configuration for Smart Cleaner.

Provides centralized logging setup with optional file output and different
verbosity levels for CLI and library use.
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console_output: bool = True,
    format_string: Optional[str] = None
) -> None:
    """Configure logging for Smart Cleaner.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to write logs to file.
        console_output: Whether to output logs to console.
        format_string: Custom format string (uses default if None).
    """
    # Default format: timestamp, level, module, message
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(format_string))
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_string))
        root_logger.addHandler(file_handler)


def setup_cli_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Convenience function for CLI logging setup.

    Args:
        verbose: Enable verbose (DEBUG) logging.
        quiet: Suppress most logging (WARNING and above only).
    """
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    # Use simpler format for CLI
    format_string = '%(levelname)s: %(message)s'

    setup_logging(
        level=level,
        console_output=True,
        format_string=format_string
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__ from calling module).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
