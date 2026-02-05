"""Logging configuration module for reNgine.
This module is expected to be used by various components of reNgine, including:
- Backend (FastAPI)
- Worker (Celery)
- Engines (Scan engines)
"""

import logging
import sys
from typing import ClassVar


class ColoredFormatter(logging.Formatter):
    # ANSI color codes
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def setup_logging(
    name: str = "rengine",
    level: str = "INFO",
    colored: bool = True,
) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        name: Logger name (e.g., "rengine.backend", "rengine.worker")
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        colored: Whether to use colored output for console

    Returns:
        Configured logger instance

    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if colored:
        console_format = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        console_format = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
