"""wafw00f CLI client - WAF fingerprinting via CLIToolRunner."""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolFlags, ToolNotFoundError
from tools.runner.models import CommandRecorder
from tools.wafw00f.parser import parse_detections

logger = get_logger(__name__)

WAFW00F_BINARY = "wafw00f"
DEFAULT_TIMEOUT = 600

# wafw00f reads custom headers from a file, one `Name: Value` per line
HEADER_FLAG = "-H"


def unreadable_headers(headers: dict[str, str] | None) -> list[str]:
    """Names wafw00f drops: it splits a line on ':' and keeps only a two-part result."""
    return sorted(name for name, value in (headers or {}).items() if ":" in value)


DEFAULT_CONCURRENCY = 6
SHARD_SIZE = 25


class Wafw00fError(Exception):
    """Raised when wafw00f execution fails."""


@dataclass
class WafScan:
    """What the run actually covered."""

    found: dict[str, str] = field(default_factory=dict)
    scanned: int = 0
    unfinished: int = 0


class Wafw00fClient:
    def __init__(
        self,
        *,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
        concurrency: int = DEFAULT_CONCURRENCY,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.proxy_url = proxy_url
        self.headers = headers or {}
        self.unreadable_headers = unreadable_headers(self.headers)
        self.concurrency = max(1, concurrency)
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(
                WAFW00F_BINARY,
                default_timeout=DEFAULT_TIMEOUT,
                recorder=recorder,
                extra_args=self.extra_args,
                flags=ToolFlags(input="-i"),
            )
        except ToolNotFoundError as e:
            raise Wafw00fError(str(e)) from e

    def detect(self, urls: list[str]) -> WafScan:
        """Fingerprint every URL, sharded across processes since wafw00f has no threads."""
        scan = WafScan()
        if not urls:
            return scan
        shards = _shard(urls)
        with self._header_file() as header_path:
            runs = (
                [self._detect_one(shards[0], header_path)]
                if len(shards) == 1
                else _run_all(
                    lambda shard: self._detect_one(shard, header_path),
                    shards,
                    self.concurrency,
                )
            )
        for shard, (found, complete) in zip(shards, runs, strict=True):
            if complete:
                scan.found.update(found)
                scan.scanned += len(shard)
            else:
                scan.unfinished += len(shard)
        return scan

    @contextlib.contextmanager
    def _header_file(self) -> Iterator[str | None]:
        """The scan's headers on disk, since wafw00f takes a path and not a value."""
        if not self.headers:
            yield None
            return
        descriptor, name = tempfile.mkstemp(prefix="wafw00f_headers_", suffix=".txt")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.writelines(
                    f"{header}: {value}\n" for header, value in self.headers.items()
                )
            yield name
        finally:
            with contextlib.suppress(OSError):
                Path(name).unlink(missing_ok=True)

    def _detect_one(
        self, urls: list[str], header_path: str | None = None
    ) -> tuple[dict[str, str], bool]:
        args = ["-f", "json", "-a", "-o", "/dev/stdout"]
        if header_path:
            args += [HEADER_FLAG, header_path]
        if self.proxy_url:
            args += ["-p", self.proxy_url]

        result = self._runner.run(
            args=args,
            input_data=urls,
            use_output_file=False,
            output_format=OutputFormat.PLAIN,
            silent=False,
        )
        return parse_detections(result.stdout), not result.timed_out


def _run_all(fn, shards: list[list[str]], concurrency: int) -> list[tuple[dict, bool]]:
    with ThreadPoolExecutor(max_workers=min(concurrency, len(shards))) as pool:
        return list(pool.map(fn, shards))


def _shard(urls: list[str]) -> list[list[str]]:
    return [urls[i : i + SHARD_SIZE] for i in range(0, len(urls), SHARD_SIZE)]
