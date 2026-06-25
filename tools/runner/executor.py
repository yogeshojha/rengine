"""Generic CLI tool executor wrapped by tool-specific clients (dnsx, nuclei, etc.)."""

import contextlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from shared.definitions.constants import MAX_COMMAND_OUTPUT
from shared.logging import get_logger
from shared.services.scan_resolve import redact_command
from tools.runner.models import CommandRecorder, OutputFormat, ToolResult

logger = get_logger(__name__)

# orchestrated CLI tools (go binaries) live here; prefer them over venv console
# scripts of the same name (e.g. the httpx PyPI CLI) when resolving under `uv run`.
_TOOL_BIN = os.environ.get("RENGINE_TOOL_BIN", "/root/go/bin")


class ToolNotFoundError(Exception):
    """Raised when a CLI tool binary is not found in PATH."""


class ToolExecutionError(Exception):
    """Raised when tool execution fails unexpectedly."""


class CLIToolRunner:
    """Generic CLI tool executor managing the full run lifecycle (validate, run, parse, cleanup)."""

    def __init__(
        self,
        binary: str,
        default_timeout: int = 300,
        recorder: CommandRecorder | None = None,
        tool: str | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.binary = binary
        self.default_timeout = default_timeout
        self._recorder = recorder
        self._tool = tool
        self._extra_args = extra_args or []
        self._binary_path: str | None = None
        self._verify_binary()

    def _verify_binary(self) -> None:
        """Check that the binary exists in PATH."""
        lookup = f"{_TOOL_BIN}{os.pathsep}{os.environ.get('PATH', '')}"
        path = shutil.which(self.binary, path=lookup)
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
        recorder: CommandRecorder | None = None,
        tool: str | None = None,
        extra_args: list[str] | None = None,
    ) -> ToolResult:
        """Execute the CLI tool and return parsed results."""
        timeout = timeout or self.default_timeout
        args = list(args) if args else []
        recorder = recorder if recorder is not None else self._recorder
        tool = tool if tool is not None else self._tool
        args.extend(extra_args if extra_args is not None else self._extra_args)

        input_file: Path | None = None
        output_file: Path | None = None
        stdin_data: str | None = None
        start_time = time.monotonic()
        cmd_str = self.binary
        handle = None
        finished = False

        def _finish(return_code: int, output: str, error: str | None) -> None:
            nonlocal finished
            if recorder is None or handle is None or finished:
                return
            finished = True
            try:
                recorder.finish(
                    handle,
                    return_code=return_code,
                    output=output,
                    error=error,
                    duration_seconds=round(time.monotonic() - start_time, 3),
                )
            except Exception:
                logger.warning("command recorder.finish failed", exc_info=True)

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
            logger.info("Executing: %s", redact_command(cmd_str))

            if recorder is not None:
                handle = recorder.start(tool or self.binary, cmd_str)

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

            _finish(
                process_result.returncode,
                (process_result.stdout or "")[:MAX_COMMAND_OUTPUT]
                + (process_result.stderr or "")[:MAX_COMMAND_OUTPUT],
                error,
            )

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
            timeout_error = f"{self.binary} timed out after {timeout} seconds"
            _finish(-1, "", timeout_error)
            return ToolResult(
                success=False,
                exit_code=-1,
                duration_seconds=round(duration, 3),
                command=cmd_str,
                error=timeout_error,
            )

        except Exception as e:
            msg = f"Unexpected error running {self.binary}: {e}"
            logger.error(msg)
            _finish(-1, "", msg)
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
