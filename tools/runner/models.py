"""Tool-agnostic models for CLI tool execution results."""

from enum import Enum

from pydantic import BaseModel, Field


class OutputFormat(Enum):
    """Output format expected from the CLI tool."""

    JSONL = "jsonl"
    PLAIN = "plain"


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

    @property
    def record_count(self) -> int:
        return len(self.json_records) if self.json_records else len(self.output_lines)

    @property
    def has_output(self) -> bool:
        return bool(self.json_records or self.output_lines)
