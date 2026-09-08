from __future__ import annotations

import contextlib
from collections.abc import Iterator

from shared.logging import get_logger
from tools.runner import CLIToolRunner, StreamOutcome, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

HTTPX_BINARY = "httpx"
DEFAULT_TIMEOUT = 900
# a probe that keeps answering keeps running; only a stalled one is killed
_IDLE_FLOOR = 120
_IDLE_TIMEOUT_FACTOR = 6
_CAPTURE_IDLE_FLOOR = 300
# rendering budget: generous per target, hard-capped, never unbounded
CAPTURE_SECONDS_PER_TARGET = 6
MAX_CAPTURE_SECONDS = 7200

# cap response-body read to bound DB growth + worker memory (per-record, times N hosts)
_RESPONSE_SIZE_CAP = 131072  # 128 KiB

_ENRICH_FLAGS = [
    "-status-code",
    "-title",
    "-tech-detect",
    "-web-server",
    "-content-length",
    "-content-type",
    "-location",
    "-ip",
    "-cname",
    "-cdn",
    "-tls-grab",
    "-jarm",
    "-favicon",
    "-hash",
    "sha256",
    "-http2",
    "-pipeline",
    "-include-response",
    "-body-preview",
    "-response-size-to-read",
    str(_RESPONSE_SIZE_CAP),
    "-no-color",
]


class HttpxError(Exception):
    pass


class HttpxClient:
    def __init__(
        self,
        *,
        rate_limit: int | None = None,
        threads: int = 50,
        timeout: int = 10,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = True,
        store_dir: str | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.rate_limit = rate_limit
        self.threads = threads
        self.timeout = timeout
        self.proxy_url = proxy_url
        self.headers = headers or {}
        self.follow_redirects = follow_redirects
        self.store_dir = store_dir
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(HTTPX_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise HttpxError(str(e)) from e

    @contextlib.contextmanager
    def stream_probe(self, targets: list[str]) -> Iterator[StreamOutcome]:
        """Probe targets, streaming parsed httpx records one at a time (memory-bounded)."""
        if not targets:
            yield StreamOutcome(records=iter(()), return_code=0)
            return
        args = list(_ENRICH_FLAGS)
        if self.follow_redirects:
            args.append("-follow-redirects")
        if self.rate_limit:
            args += ["-rate-limit", str(self.rate_limit)]
        args += ["-threads", str(self.threads), "-timeout", str(self.timeout)]
        if self.proxy_url:
            args += ["-proxy", self.proxy_url]
        for key, value in self.headers.items():
            args += ["-header", f"{key}: {value}"]

        with self._runner.stream_json(
            args=args,
            input_data=targets,
            input_flag="-l",
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            timeout=0,
            idle_timeout=max(_IDLE_FLOOR, self.timeout * _IDLE_TIMEOUT_FACTOR),
            recorder=self.recorder,
            tool=HTTPX_BINARY,
            extra_args=self.extra_args,
        ) as stream:
            yield stream

    def _capture_args(self) -> list[str]:
        args = [
            "-status-code",
            "-screenshot",
            "-system-chrome",
            "-exclude-screenshot-bytes",
            "-no-color",
        ]
        if self.store_dir:
            args += ["-store-response-dir", self.store_dir]
        if self.follow_redirects:
            args.append("-follow-redirects")
        args += ["-threads", str(self.threads), "-timeout", str(max(self.timeout, 20))]
        if self.proxy_url:
            args += ["-proxy", self.proxy_url]
        for key, value in self.headers.items():
            args += ["-header", f"{key}: {value}"]
        return args

    @contextlib.contextmanager
    def stream_capture(self, targets: list[str]) -> Iterator[StreamOutcome]:
        """The same render, streaming each image as the browser finishes it."""
        if not targets:
            yield StreamOutcome(records=iter(()), return_code=0)
            return
        # a total ceiling as well as the idle watchdog: a renderer that keeps emitting one
        # image every few minutes is not stalled, but it must not run to the celery limit
        ceiling = min(
            MAX_CAPTURE_SECONDS,
            max(DEFAULT_TIMEOUT, len(targets) * CAPTURE_SECONDS_PER_TARGET),
        )
        with self._runner.stream_json(
            args=self._capture_args(),
            input_data=targets,
            input_flag="-l",
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            timeout=ceiling,
            # a headless browser is slow to start and slow per page, so the watchdog
            # has to be generous — it is only there for a renderer that has died
            idle_timeout=max(_CAPTURE_IDLE_FLOOR, self.timeout * _IDLE_TIMEOUT_FACTOR),
            recorder=self.recorder,
            tool=HTTPX_BINARY,
            extra_args=self.extra_args,
        ) as stream:
            yield stream
