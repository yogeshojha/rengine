from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator

from shared.logging import get_logger
from tools.runner import CLIToolRunner, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

KATANA_BINARY = "katana"
DEFAULT_TIMEOUT = 1800

_BASE_FLAGS = [
    "-jsonl",
    "-omit-raw",
    "-omit-body",
    "-no-color",
    "-known-files",
    "all",
]


class KatanaError(Exception):
    pass


class KatanaClient:
    def __init__(
        self,
        *,
        depth: int = 3,
        threads: int = 10,
        timeout: int = 10,
        max_duration_minutes: int = 0,
        rate_limit: int | None = None,
        crawl_scope: str = "subs",
        include_js: bool = True,
        headless: bool = False,
        form_extraction: bool = True,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.depth = depth
        self.threads = threads
        self.timeout = timeout
        self.max_duration_minutes = max_duration_minutes
        self.rate_limit = rate_limit
        self.crawl_scope = crawl_scope
        self.include_js = include_js
        self.headless = headless
        self.form_extraction = form_extraction
        self.proxy_url = proxy_url
        self.headers = headers or {}
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(KATANA_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise KatanaError(str(e)) from e

    def _args(self) -> list[str]:
        args = list(_BASE_FLAGS)
        args += ["-depth", str(self.depth)]
        args += ["-concurrency", str(self.threads)]
        args += ["-timeout", str(self.timeout)]
        args += ["-field-scope", self.crawl_scope]
        if self.max_duration_minutes:
            args += ["-crawl-duration", f"{self.max_duration_minutes}m"]
        if self.rate_limit:
            args += ["-rate-limit", str(self.rate_limit)]
        if self.include_js:
            args += ["-jsluice", "-js-crawl"]
        if self.form_extraction:
            args.append("-automatic-form-fill")
        if self.headless:
            args += ["-headless", "-no-sandbox"]
        if self.proxy_url:
            args += ["-proxy", self.proxy_url]
        for key, value in self.headers.items():
            args += ["-header", f"{key}: {value}"]
        return args

    @contextlib.contextmanager
    def stream_crawl(
        self,
        targets: list[str],
        *,
        should_stop: Callable[[], bool] | None = None,
        stderr_sink: Callable[[str], None] | None = None,
    ) -> Iterator[Iterator[dict]]:
        """Crawl targets, streaming one parsed katana record at a time."""
        if not targets:
            yield iter(())
            return
        with self._runner.stream_json(
            args=self._args(),
            input_data=targets,
            input_flag="-list",
            json_flag="-jsonl",
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=KATANA_BINARY,
            extra_args=self.extra_args,
            should_stop=should_stop,
            stderr_sink=stderr_sink,
        ) as records:
            yield records
