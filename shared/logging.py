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


_RESERVED = frozenset({"exc_info", "stack_info", "stacklevel", "extra"})


class _FieldLogger(logging.LoggerAdapter):
    """Accepts structured fields as keywords and appends them to the message.

    Call sites throughout the codebase pass `logger.info("thing failed", error=...)`.
    A bare stdlib logger raises TypeError on that — and only when the level is
    enabled, so it hides in one environment and crashes in another.
    """

    def log(self, level, msg, *args, **kwargs):
        fields = {k: v for k, v in kwargs.items() if k not in _RESERVED}
        for key in fields:
            kwargs.pop(key)
        if fields:
            rendered = " ".join(f"{k}={v}" for k, v in fields.items())
            msg = f"{msg} | {rendered}"
        super().log(level, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        kwargs.setdefault("exc_info", True)
        self.log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log(logging.CRITICAL, msg, *args, **kwargs)


def get_logger(name: str) -> logging.Logger:
    return _FieldLogger(logging.getLogger(name), {})
