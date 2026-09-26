"""Generic CLI tool executor wrapped by tool-specific clients (dnsx, nuclei, etc.)."""

import contextlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from shared.definitions.constants import MAX_COMMAND_OUTPUT
from shared.logging import get_logger
from shared.services.scan_resolve import redact_command
from tools.runner.abort import StageAbortedError, active_abort
from tools.runner.models import (
    CommandRecorder,
    OutputFormat,
    StreamOutcome,
    ToolFlags,
    ToolResult,
)

logger = get_logger(__name__)

_TOOL_BIN = os.environ.get("RENGINE_TOOL_BIN", "/root/go/bin")


def tool_path() -> str:
    """PATH the worker's tool binaries are looked up on."""
    return f"{_TOOL_BIN}{os.pathsep}{os.environ.get('PATH', '')}"


_STOP_POLL_SECONDS = 2.0
_KILL_GRACE_SECONDS = 5


def _terminate(proc: subprocess.Popen) -> None:
    """Kill the tool and anything it started, so no grandchild keeps running."""
    with contextlib.suppress(Exception):
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    with contextlib.suppress(Exception):
        proc.kill()
    with contextlib.suppress(Exception):
        proc.wait(timeout=_KILL_GRACE_SECONDS)


def _flag_name(token: str) -> str:
    return token.split("=", 1)[0]


def merge_extra_args(
    args: list[str],
    extra: list[str],
    reserved: tuple[str, ...] = (),
    aliases: dict[str, str] | None = None,
) -> list[str]:
    """Tool args, minus any flag the stage already set, under either spelling."""
    names = aliases or {}

    def canonical(token: str) -> str:
        name = _flag_name(token)
        return names.get(name, name)

    taken = {canonical(a) for a in args if a.startswith("-")} | {
        names.get(r, r) for r in reserved if r
    }
    out: list[str] = []
    skip = False
    for index, token in enumerate(extra):
        if skip:
            skip = False
            continue
        if token.startswith("-") and canonical(token) in taken:
            following = extra[index + 1] if index + 1 < len(extra) else None
            skip = (
                "=" not in token
                and following is not None
                and not following.startswith("-")
            )
            continue
        out.append(token)
    return out


def _drain(stream, into: list[str]) -> None:
    with contextlib.suppress(Exception):
        into.append(stream.read())


def _feed(stream, data: str) -> None:
    with contextlib.suppress(Exception):
        stream.write(data)
        stream.close()


def _wait(
    proc: subprocess.Popen,
    *,
    timeout: int | None,
    should_stop: Callable[[], bool] | None,
) -> bool:
    """Wait for the tool, answering the stage's abort check while it runs."""
    deadline = time.monotonic() + timeout if timeout else None
    while True:
        left = None if deadline is None else deadline - time.monotonic()
        if left is not None and left <= 0:
            return False
        slice_seconds = (
            _STOP_POLL_SECONDS if left is None else min(_STOP_POLL_SECONDS, left)
        )
        try:
            proc.wait(timeout=slice_seconds)
        except subprocess.TimeoutExpired:
            if should_stop is not None and should_stop():
                return True
        else:
            return False


def _run_process(
    cmd: list[str],
    *,
    stdin_data: str | None,
    env: dict[str, str],
    cwd: str,
    timeout: int | None,
    should_stop: Callable[[], bool] | None,
) -> subprocess.CompletedProcess[str]:
    """subprocess.run, plus a kill when the scan is halted."""
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        env=env,
        cwd=cwd,
        start_new_session=True,
    )
    out: list[str] = []
    err: list[str] = []
    readers = [
        threading.Thread(target=_drain, args=(proc.stdout, out), daemon=True),
        threading.Thread(target=_drain, args=(proc.stderr, err), daemon=True),
    ]
    if stdin_data is not None and proc.stdin is not None:
        readers.append(
            threading.Thread(target=_feed, args=(proc.stdin, stdin_data), daemon=True)
        )
    for reader in readers:
        reader.start()

    stopped = _wait(proc, timeout=timeout, should_stop=should_stop)
    timed_out = proc.poll() is None and not stopped
    if proc.poll() is None:
        _terminate(proc)
    for reader in readers:
        reader.join(timeout=_KILL_GRACE_SECONDS)
    if stopped:
        raise StageAbortedError
    if timed_out:
        raise subprocess.TimeoutExpired(
            cmd, timeout or 0, output="".join(out), stderr="".join(err)
        )
    return subprocess.CompletedProcess(
        cmd,
        proc.returncode if proc.returncode is not None else -1,
        "".join(out),
        "".join(err),
    )


class ToolNotFoundError(Exception):
    """Raised when a CLI tool binary is not found in PATH."""


class ToolExecutionError(Exception):
    """Raised when tool execution fails unexpectedly."""


_MAX_STDOUT_AS_ERROR = 2000


def failure_excerpt(stderr: str | None, stdout: str | None) -> str:
    text = (stderr or "").strip()
    if text:
        return text[:500]
    out = (stdout or "").strip()
    return out[:500] if 0 < len(out) <= _MAX_STDOUT_AS_ERROR else ""


class CLIToolRunner:
    """Generic CLI tool executor managing the full run lifecycle (validate, run, parse, cleanup).

    Everything that describes the binary and the scan it runs for (its flag
    spellings, the command recorder, the user's custom args) is bound here once;
    `run` and `stream_json` take only what differs between two invocations.
    """

    def __init__(
        self,
        binary: str,
        default_timeout: int = 300,
        recorder: CommandRecorder | None = None,
        tool: str | None = None,
        extra_args: list[str] | None = None,
        aliases: dict[str, str] | None = None,
        flags: ToolFlags | None = None,
    ) -> None:
        self.binary = binary
        self.default_timeout = default_timeout
        self.flags = flags or ToolFlags()
        self._recorder = recorder
        self._tool = tool or binary
        self._extra_args = list(extra_args or [])
        self._aliases = dict(aliases or {})
        self._binary_path: str | None = None
        self._verify_binary()

    def _with_extra_args(self, args: list[str] | None, *reserved: str) -> list[str]:
        """The stage's args, then the user's custom args minus any flag already set."""
        out = list(args) if args else []
        out.extend(merge_extra_args(out, self._extra_args, reserved, self._aliases))
        return out

    def _verify_binary(self) -> None:
        """Check that the binary exists in PATH."""
        path = shutil.which(self.binary, path=tool_path())
        if not path:
            msg = (
                f"Binary '{self.binary}' not found in PATH. "
                "Install it in the worker image."
            )
            raise ToolNotFoundError(msg)
        self._binary_path = path
        logger.debug(f"Found {self.binary} at {path}")

    def run(  # noqa: PLR0915
        self,
        args: list[str] | None = None,
        input_data: str | list[str] | None = None,
        *,
        use_stdin: bool = False,
        use_output_file: bool = True,
        output_format: OutputFormat = OutputFormat.PLAIN,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
        silent: bool = True,
        should_stop: Callable[[], bool] | None = None,
    ) -> ToolResult:
        """Execute the CLI tool and return parsed results."""
        timeout = timeout or self.default_timeout
        flags = self.flags
        recorder = self._recorder
        args = self._with_extra_args(
            args, flags.input, flags.output, flags.json, flags.silent
        )

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
                    args.extend([flags.input, str(input_file)])

            if use_output_file:
                output_file = self._create_temp_path(prefix="output_")
                args.extend([flags.output, str(output_file)])

            if output_format == OutputFormat.JSONL and flags.json not in args:
                args.append(flags.json)

            if silent and flags.silent not in args:
                args.append(flags.silent)

            cmd = [self._binary_path, *args]
            cmd_str = " ".join(cmd)
            logger.info("Executing: %s", redact_command(cmd_str))

            if recorder is not None:
                handle = recorder.start(self._tool, cmd_str)

            process_result = _run_process(
                cmd,
                stdin_data=stdin_data,
                env=self._build_env(env),
                cwd=tempfile.gettempdir(),
                timeout=timeout,
                should_stop=should_stop or active_abort(),
            )

            duration = time.monotonic() - start_time

            raw_output = self._read_output(
                output_file=output_file,
                stdout=process_result.stdout,
                use_output_file=use_output_file,
            )

            output_lines, json_records = self._parse(raw_output, output_format)

            success = process_result.returncode == 0
            error = None
            if not success:
                excerpt = failure_excerpt(process_result.stderr, process_result.stdout)
                error = (
                    f"{self.binary} exited with code {process_result.returncode}"
                    + (f": {excerpt}" if excerpt else "")
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

        except StageAbortedError:
            logger.info("%s stopped: the scan was halted", self.binary)
            _finish(-1, "", f"{self.binary} stopped: the scan was halted")
            raise

        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start_time
            logger.error(f"{self.binary} timed out after {timeout}s")
            timeout_error = f"{self.binary} timed out after {timeout} seconds"
            raw_output = self._read_output(
                output_file=output_file,
                stdout=str(exc.output or ""),
                use_output_file=use_output_file,
            )
            partial_lines, partial_records = self._parse(raw_output, output_format)
            _finish(-1, "", timeout_error)
            return ToolResult(
                success=False,
                exit_code=-1,
                output_lines=partial_lines,
                json_records=partial_records,
                duration_seconds=round(duration, 3),
                command=cmd_str,
                error=timeout_error,
                timed_out=True,
            )

        except Exception as e:
            msg = f"Unexpected error running {self.binary}: {e}"
            logger.error(msg)
            _finish(-1, "", msg)
            raise ToolExecutionError(msg) from e

        finally:
            self._cleanup(input_file, output_file)

    @contextlib.contextmanager
    def stream_json(  # noqa: PLR0915
        self,
        *,
        args: list[str] | None = None,
        input_data: str | list[str] | None = None,
        silent: bool = True,
        timeout: int | None = None,
        idle_timeout: int | None = None,
        env: dict[str, str] | None = None,
        stderr_sink: Callable[[str], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> Iterator[StreamOutcome]:
        """Stream-parse the tool's JSONL stdout."""
        timeout = self.default_timeout if timeout is None else timeout
        flags = self.flags
        recorder = self._recorder
        args = self._with_extra_args(args, flags.input, flags.json, flags.silent)

        input_file: Path | None = None
        start_time = time.monotonic()
        handle = None
        proc: subprocess.Popen | None = None
        timer: threading.Timer | None = None
        stderr_thread: threading.Thread | None = None
        stderr_chunks: list[str] = []
        killed_for: list[str] = [""]
        stopped: list[bool] = [False]
        outcome = StreamOutcome(records=iter(()))
        try:
            lead: list[str] = []
            if input_data is not None:
                raw_input = self._normalize_input(input_data)
                input_file = self._write_temp_file(raw_input, prefix="input_")
                lead.extend([flags.input, str(input_file)])
            if flags.json not in args:
                lead.append(flags.json)
            if silent and flags.silent not in args:
                lead.append(flags.silent)

            cmd = [self._binary_path, *lead, *args]
            logger.info("Executing (stream): %s", redact_command(" ".join(cmd)))
            if recorder is not None:
                handle = recorder.start(self._tool, " ".join(cmd))

            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                env=self._build_env(env),
                cwd=tempfile.gettempdir(),
                start_new_session=True,
            )
            stdout = proc.stdout
            last_seen = [time.monotonic()]

            def _kill(reason: str) -> None:
                killed_for[0] = reason
                if proc is not None:
                    _terminate(proc)

            if idle_timeout:

                def _watch_idle() -> None:
                    while proc is not None and proc.poll() is None:
                        if time.monotonic() - last_seen[0] > idle_timeout:
                            _kill(f"no output for {idle_timeout}s")
                            return
                        time.sleep(_STOP_POLL_SECONDS)

                threading.Thread(target=_watch_idle, daemon=True).start()
            if timeout:
                timer = threading.Timer(timeout, lambda: _kill(f"exceeded {timeout}s"))
                timer.start()

            def _drain_stderr() -> None:
                if proc is None or proc.stderr is None:
                    return
                size = 0
                for line in proc.stderr:
                    last_seen[0] = time.monotonic()
                    if size < MAX_COMMAND_OUTPUT:
                        stderr_chunks.append(line)
                        size += len(line)
                    if stderr_sink is not None:
                        with contextlib.suppress(Exception):
                            stderr_sink(line)

            stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
            stderr_thread.start()

            stop_check = should_stop or active_abort()
            if stop_check is not None:

                def _watch_stop() -> None:
                    while proc is not None and proc.poll() is None:
                        if stop_check():
                            stopped[0] = True
                            _kill("the scan was halted")
                            return
                        time.sleep(_STOP_POLL_SECONDS)

                threading.Thread(target=_watch_stop, daemon=True).start()

            def _records() -> Iterator[dict]:
                if stdout is None:
                    return
                for line in stdout:
                    last_seen[0] = time.monotonic()
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        obj = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        outcome.record_count += 1
                        yield obj

            outcome.records = _records()
            yield outcome
        finally:
            if timer is not None:
                timer.cancel()
            return_code = -1
            if proc is not None:
                with contextlib.suppress(Exception):
                    return_code = proc.wait(timeout=10)
                if proc.poll() is None:
                    _terminate(proc)
                    return_code = proc.returncode if proc.returncode is not None else -1
            if stderr_thread is not None:
                stderr_thread.join(timeout=5)
            stderr = "".join(stderr_chunks)
            outcome.return_code = return_code
            outcome.stopped = stopped[0]
            outcome.timed_out = bool(killed_for[0]) and not stopped[0]
            outcome.stderr = stderr
            if killed_for[0]:
                logger.warning("%s killed: %s", self.binary, killed_for[0])
            if recorder is not None and handle is not None:
                err = (
                    None
                    if return_code == 0 and not killed_for[0]
                    else (
                        f"{self.binary} killed: {killed_for[0]}"
                        if killed_for[0]
                        else f"{self.binary} exited with code {return_code}"
                    )
                    + (f": {stderr.strip()[:500]}" if stderr.strip() else "")
                )
                with contextlib.suppress(Exception):
                    recorder.finish(
                        handle,
                        return_code=return_code,
                        output=(stderr or "")[:MAX_COMMAND_OUTPUT],
                        error=err,
                        duration_seconds=round(time.monotonic() - start_time, 3),
                    )
            self._cleanup(input_file)

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
            # the with block closed fd
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

    @classmethod
    def _parse(
        cls, raw: str, output_format: OutputFormat
    ) -> tuple[list[str], list[dict]]:
        """Lines or records, whichever this run asked for."""
        if output_format == OutputFormat.JSONL:
            return [], cls._parse_jsonl(raw)
        return cls._parse_lines(raw), []

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
