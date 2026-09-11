"""tlsx CLI client - the certificate a host presents, one handshake each."""

from __future__ import annotations

from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError, ToolResult
from tools.runner.models import CommandRecorder

TLSX_BINARY = "tlsx"
DEFAULT_TIMEOUT = 10
DEFAULT_CONCURRENCY = 50


class TlsxError(Exception):
    """Raised when tlsx cannot be run."""


class TlsxClient:
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        concurrency: int = DEFAULT_CONCURRENCY,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.concurrency = concurrency
        self.recorder = recorder
        self.extra_args = extra_args or []
        try:
            self._runner = CLIToolRunner(TLSX_BINARY, default_timeout=timeout)
        except ToolNotFoundError as e:
            raise TlsxError(str(e)) from e

    def certificates(self, hosts: list[str], *, timeout: int) -> ToolResult:
        args = [
            "-timeout",
            str(self.timeout),
            "-c",
            str(self.concurrency),
            "-expired",
            "-self-signed",
        ]
        return self._runner.run(
            args=args,
            input_data=hosts,
            input_flag="-l",
            output_format=OutputFormat.JSONL,
            json_flag="-json",
            timeout=timeout,
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=TLSX_BINARY,
            extra_args=self.extra_args,
        )
