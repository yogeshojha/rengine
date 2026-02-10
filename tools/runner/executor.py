"""Generic CLI tool executor for various recon tools.

Handles subprocess lifecycle, temp file management, input/output piping,
JSONL parsing, timeouts, and cleanup. Designed to be wrapped by
tool-specific clients (dnsx, nuclei, etc.).

TODO: keep improving this as more tools are integrated, but it should cover most common patterns.
Usage:
    runner = CLIToolRunner("dnsx")
    result = runner.run(
        args=["-a", "-aaaa", "-resp"],
        input_data=["example.com", "google.com"],
        output_format=OutputFormat.JSONL,
        json_flag="-json",
    )
"""

import contextlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from shared.logging import get_logger
from tools.runner.models import OutputFormat, ToolResult

logger = get_logger("tools.runner")


class ToolNotFoundError(Exception):
    """Raised when a CLI tool binary is not found in PATH."""


class ToolExecutionError(Exception):
    """Raised when tool execution fails unexpectedly."""


class CLIToolRunner:
    """Generic CLI tool executor.

    Manages the full lifecycle of running a CLI tool:
    1. Validates binary exists in PATH
    2. Writes input data to temp file if provided
    3. Builds command with args, input/output flags
    4. Runs subprocess with timeout
    5. Reads output from file or stdout
    6. Parses output (JSONL or plain text)
    7. Cleans up all temp files

    Args:
        binary: Name of the CLI tool binary (e.g. "dnsx", "subfinder", "katana, etc").
        default_timeout: Default timeout in seconds for tool execution.
    """

    def __init__(self, binary: str, default_timeout: int = 300) -> None:
        self.binary = binary
        self.default_timeout = default_timeout
        self._binary_path: str | None = None
        self._verify_binary()

    def _verify_binary(self) -> None:
        """Check that the binary exists in PATH."""
        path = shutil.which(self.binary)
        if not path:
            msg = (
                f"Binary '{self.binary}' not found in PATH. "
                f"Ensure it is installed in the worker container."
            )
            raise ToolNotFoundError(msg)
        self._binary_path = path
        logger.debug(f"Found {self.binary} at {path}")

    def run(  # noqa: PLR0915
        self,
        args: list[str] | None = None,
        input_data: str | list[str] | None = None,
        input_flag: str = "-l",
        use_stdin: bool = False,
        use_output_file: bool = True,
        output_flag: str = "-o",
        output_format: OutputFormat = OutputFormat.PLAIN,
        json_flag: str = "-json",
        timeout: int | None = None,
        env: dict[str, str] | None = None,
        silent: bool = True,
        silent_flag: str = "-silent",
    ) -> ToolResult:
        """Execute the CLI tool and return parsed results.

        Args:
            args: CLI arguments to pass to the tool.
            input_data: Input to feed the tool. Can be:
                - A string (single value, written to temp file or piped to stdin)
                - A list of strings (one per line, written to temp file or piped)
                - None (no input)
            input_flag: CLI flag for input file (e.g. "-l", "-list", "-target").
            use_stdin: If True, pipe input via stdin instead of temp file.
                When False (default), writes to temp file and passes via input_flag.
            use_output_file: If True, captures output via temp file using output_flag.
                When False, captures stdout directly.
            output_flag: CLI flag for output file (e.g. "-o", "-output").
            output_format: Expected output format (JSONL or PLAIN).
            json_flag: CLI flag to enable JSON output (e.g. "-json", "-j").
            timeout: Max seconds to wait. Defaults to self.default_timeout.
            env: Additional environment variables for the subprocess.
            silent: If True, adds silent_flag to suppress banner/noise.
            silent_flag: CLI flag for silent mode (e.g. "-silent", "-s").

        Returns:
            ToolResult with parsed output and execution metadata.

        Raises:
            ToolExecutionError: On unexpected failures (not tool errors).
        """
        timeout = timeout or self.default_timeout
        args = list(args) if args else []

        input_file: Path | None = None
        output_file: Path | None = None
        stdin_data: str | None = None
        start_time = time.monotonic()

        try:
            if input_data is not None:
                raw_input = self._normalize_input(input_data)
                if use_stdin:
                    stdin_data = raw_input
                else:
                    input_file = self._write_temp_file(raw_input, prefix="input_")
                    args.extend([input_flag, str(input_file)])

            if use_output_file:
                output_file = self._create_temp_path(prefix="output_")
                args.extend([output_flag, str(output_file)])

            if output_format == OutputFormat.JSONL and json_flag not in args:
                args.append(json_flag)

            if silent and silent_flag not in args:
                args.append(silent_flag)

            cmd = [self._binary_path, *args]
            cmd_str = " ".join(cmd)
            logger.info(f"Executing: {cmd_str}")

            process_result = subprocess.run(  # noqa: S603
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=self._build_env(env),
                cwd=tempfile.gettempdir(),
            )

            duration = time.monotonic() - start_time

            raw_output = self._read_output(
                output_file=output_file,
                stdout=process_result.stdout,
                use_output_file=use_output_file,
            )

            output_lines: list[str] = []
            json_records: list[dict] = []

            if output_format == OutputFormat.JSONL:
                json_records = self._parse_jsonl(raw_output)
            else:
                output_lines = self._parse_lines(raw_output)

            success = process_result.returncode == 0
            error = None
            if not success:
                stderr_excerpt = (process_result.stderr or "").strip()[:500]
                error = (
                    f"{self.binary} exited with code {process_result.returncode}"
                    + (f": {stderr_excerpt}" if stderr_excerpt else "")
                )
                logger.warning(error)

            return ToolResult(
                success=success,
                stdout=process_result.stdout or "",
                stderr=process_result.stderr or "",
                exit_code=process_result.returncode,
                output_lines=output_lines,
                json_records=json_records,
                duration_seconds=round(duration, 3),
                command=cmd_str,
                error=error,
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            logger.error(f"{self.binary} timed out after {timeout}s")
            return ToolResult(
                success=False,
                exit_code=-1,
                duration_seconds=round(duration, 3),
                command=" ".join([self.binary, *(args or [])]),
                error=f"{self.binary} timed out after {timeout} seconds",
            )

        except Exception as e:
            msg = f"Unexpected error running {self.binary}: {e}"
            logger.error(msg)
            raise ToolExecutionError(msg) from e

        finally:
            self._cleanup(input_file, output_file)

    @staticmethod
    def _normalize_input(data: str | list[str]) -> str:
        """Convert input data to newline-separated string."""
        if isinstance(data, list):
            return "\n".join(data) + "\n"
        return data.strip() + "\n"

    @staticmethod
    def _write_temp_file(content: str, prefix: str = "tool_") -> Path:
        """Write content to a named temp file, return its path."""
        fd, path_str = tempfile.mkstemp(prefix=prefix, suffix=".txt")
        filepath = Path(path_str)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
        except Exception:
            os.close(fd)
            filepath.unlink(missing_ok=True)
            raise
        return filepath

    @staticmethod
    def _create_temp_path(prefix: str = "tool_") -> Path:
        """Create a temp file path (file created empty, tool will write to it)."""
        fd, path_str = tempfile.mkstemp(prefix=prefix, suffix=".txt")
        os.close(fd)
        return Path(path_str)

    @staticmethod
    def _read_output(
        output_file: Path | None,
        stdout: str,
        use_output_file: bool,
    ) -> str:
        """Read tool output from file or stdout."""
        if use_output_file and output_file and output_file.exists():
            try:
                content = output_file.read_text(encoding="utf-8", errors="replace")
                if content.strip():
                    return content
            except OSError as e:
                logger.warning(f"Failed to read output file {output_file}: {e}")
        return stdout or ""

    @staticmethod
    def _parse_jsonl(raw: str) -> list[dict]:
        """Parse JSONL (one JSON object per line) output."""
        records = []
        for raw_line in raw.strip().splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    logger.debug(f"Skipping non-dict JSON line: {type(obj)}")
            except json.JSONDecodeError as e:
                logger.debug(f"Skipping invalid JSON line: {e} | {stripped[:100]}")
        return records

    @staticmethod
    def _parse_lines(raw: str) -> list[str]:
        """Parse plain text output into non-empty lines."""
        return [line.strip() for line in raw.strip().splitlines() if line.strip()]

    @staticmethod
    def _build_env(extra: dict[str, str] | None) -> dict[str, str]:
        """Build subprocess environment, merging extra vars with current env."""
        env = os.environ.copy()
        if extra:
            env.update(extra)
        return env

    @staticmethod
    def _cleanup(*files: Path | None) -> None:
        """Remove temp files, silently ignoring errors."""
        for f in files:
            if f is not None:
                with contextlib.suppress(OSError):
                    f.unlink(missing_ok=True)
