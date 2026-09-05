"""Tool-agnostic models for CLI tool execution results."""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class OutputFormat(Enum):
    """Output format expected from the CLI tool."""

    JSONL = "jsonl"
    PLAIN = "plain"


@runtime_checkable
class CommandRecorder(Protocol):
    """Optional hook the executor calls to register a command and capture its log."""

    def start(self, tool: str, command: str) -> Any: ...

    def finish(
        self,
        handle: Any,
        *,
        return_code: int,
        output: str,
        error: str | None,
        duration_seconds: float,
    ) -> None: ...


class ToolResult(BaseModel):
    """Result of a CLI tool execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    output_lines: list[str] = Field(default_factory=list)
    json_records: list[dict] = Field(default_factory=list)
    duration_seconds: float = 0.0
    command: str = ""
    error: str | None = None
    timed_out: bool = False

    @property
    def has_output(self) -> bool:
        return bool(self.json_records or self.output_lines)


@dataclass
class StreamOutcome:
    """How a stream_json run ended; populated once the caller's block exits."""

    records: Iterator[dict]
    return_code: int = -1
    timed_out: bool = False
    record_count: int = 0
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.return_code == 0 and not self.timed_out
