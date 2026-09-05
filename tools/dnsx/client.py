"""dnsx CLI client - wraps CLIToolRunner with dnsx-specific arguments."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator

from shared.logging import get_logger
from tools.runner import (
    CLIToolRunner,
    OutputFormat,
    StreamOutcome,
    ToolNotFoundError,
    ToolResult,
)
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

DNSX_BINARY = "dnsx"
DEFAULT_TIMEOUT = 120
DEFAULT_RETRY = 3
DEFAULT_THREADS = 10


class DnsxError(Exception):
    """Raised when dnsx execution fails."""


class DnsxClient:
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        retry: int = DEFAULT_RETRY,
        threads: int = DEFAULT_THREADS,
        resolvers: list[str] | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.retry = retry
        self.threads = threads
        self.resolvers = resolvers
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(DNSX_BINARY, default_timeout=timeout)
        except ToolNotFoundError as e:
            raise DnsxError(str(e)) from e

    def _build_base_args(self) -> list[str]:
        args = [
            "-retry",
            str(self.retry),
            "-t",
            str(self.threads),
        ]
        if self.resolvers:
            args.extend(["-r", ",".join(self.resolvers)])
        return args

    def recon(
        self,
        targets: str | list[str],
        cdn: bool = True,
    ) -> ToolResult:
        """Run full DNS recon (-recon) querying all record types on one or more targets."""
        args = self._build_base_args()
        args.extend(["-recon", "-resp"])
        if cdn:
            args.append("-cdn")

        return self._run(targets, args)

    def query(
        self,
        targets: str | list[str],
        record_types: list[str] | None = None,
        resp_only: bool = False,
        cdn: bool = False,
    ) -> ToolResult:
        """Run targeted DNS queries for specific record types (defaults to A)."""
        args = self._build_base_args()

        if record_types:
            for rt in record_types:
                flag = f"-{rt.lower()}"
                args.append(flag)

        if resp_only:
            args.append("-resp-only")
        else:
            args.append("-resp")

        if cdn:
            args.append("-cdn")

        return self._run(targets, args)

    @contextlib.contextmanager
    def stream_query(
        self,
        targets: list[str],
        record_types: list[str] | None = None,
        *,
        idle_timeout: int | None = None,
    ) -> Iterator[StreamOutcome]:
        """Resolve in bulk, streaming records as they land so a stall never zeroes the run."""
        args = self._build_base_args()
        for rt in record_types or ["a"]:
            args.append(f"-{rt.lower()}")
        args.append("-resp")
        with self._runner.stream_json(
            args=args,
            input_data=targets,
            input_flag="-l",
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            timeout=0,
            idle_timeout=idle_timeout,
            recorder=self.recorder,
            tool=DNSX_BINARY,
            extra_args=self.extra_args,
        ) as stream:
            yield stream

    def resolve(
        self,
        targets: str | list[str],
    ) -> ToolResult:
        """Simple DNS resolution check (filters alive hosts)."""
        args = self._build_base_args()

        return self._run(
            targets,
            args,
            output_format=OutputFormat.PLAIN,
        )

    def ptr(
        self,
        ips: str | list[str],
    ) -> ToolResult:
        """Reverse-DNS (PTR) lookup for one or more IPs (-ptr)."""
        args = self._build_base_args()
        args.extend(["-ptr", "-resp"])

        return self._run(ips, args)

    def _run(
        self,
        targets: str | list[str],
        args: list[str],
        output_format: OutputFormat = OutputFormat.JSONL,
    ) -> ToolResult:
        """Execute dnsx with the given arguments."""
        if isinstance(targets, str):
            targets = [targets]

        return self._runner.run(
            args=args,
            input_data=targets,
            input_flag="-l",
            output_format=output_format,
            json_flag="-json",
            timeout=self.timeout,
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=DNSX_BINARY,
            extra_args=self.extra_args,
        )
