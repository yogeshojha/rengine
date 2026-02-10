"""Models for CLI tool execution results.

These models are tool-agnostic and used by all CLI-based tools
"""

from enum import Enum

from pydantic import BaseModel, Field


class OutputFormat(Enum):
    """Output format expected from the CLI tool."""

    JSONL = "jsonl"
    PLAIN = "plain"


class ToolResult(BaseModel):
    """Result of a CLI tool execution.

    Attributes:
        success: Whether the tool ran without errors.
        stdout: Raw stdout captured (may be empty if output file was used).
        stderr: Raw stderr captured.
        exit_code: Process exit code.
        output_lines: Parsed non-empty lines from tool output (plain mode).
        json_records: Parsed JSON objects from tool output (JSONL mode).
        duration_seconds: Wall-clock time the tool ran.
        command: Full command string (for debugging/logging).
        error: Human-readable error message if success is False.
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    output_lines: list[str] = Field(default_factory=list)
    json_records: list[dict] = Field(default_factory=list)
    duration_seconds: float = 0.0
    command: str = ""
    error: str | None = None

    @property
    def record_count(self) -> int:
        """Number of parsed records (JSON or plain lines)."""
        return len(self.json_records) if self.json_records else len(self.output_lines)

    @property
    def has_output(self) -> bool:
        return bool(self.json_records or self.output_lines)
