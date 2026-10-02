from __future__ import annotations

import contextlib
import re
from collections.abc import Callable, Iterator

from tools.runner import CLIToolRunner, ToolNotFoundError
from tools.runner.models import CommandRecorder

KATANA_BINARY = "katana"
DEFAULT_TIMEOUT = 1800
_KILL_SLACK_SECONDS = 120

# katana spells it -H/-headers; httpx and nuclei spell it -header
HEADER_FLAG = "-headers"

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


def url_pattern(host_regex: str, scheme: str | None = None) -> str:
    """A -crawl-scope or -crawl-out-scope regex for URLs whose host matches host_regex."""
    lead = re.escape(scheme) if scheme else "[a-z][a-z0-9+.-]*"
    return f"(?i)^{lead}://([^/?#@]*@)?{host_regex}(:[0-9]+)?([/?#]|$)"


def _scope_values(patterns: list[str] | None) -> list[str]:
    # goflags splits a value on commas
    return [p for p in patterns or [] if p and "," not in p]


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
        crawl_in_scope: list[str] | None = None,
        crawl_out_scope: list[str] | None = None,
        include_js: bool = True,
        headless: bool = False,
        form_extraction: bool = True,
        ignore_query_params: bool = True,
        exclude_extensions: list[str] | None = None,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
        scheme: str | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.scheme = scheme
        self.depth = depth
        self.threads = threads
        self.timeout = timeout
        self.max_duration_minutes = max_duration_minutes
        self.rate_limit = rate_limit
        self.crawl_scope = crawl_scope
        self.crawl_in_scope = _scope_values(crawl_in_scope)
        self.crawl_out_scope = _scope_values(crawl_out_scope)
        self.include_js = include_js
        self.headless = headless
        self.form_extraction = form_extraction
        self.ignore_query_params = ignore_query_params
        self.exclude_extensions = list(exclude_extensions or [])
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
        in_scope = getattr(self, "crawl_in_scope", None) or []
        for pattern in in_scope:
            args += ["-crawl-scope", pattern]
        scheme = getattr(self, "scheme", None)
        if scheme and not in_scope:
            args += ["-crawl-scope", f"^{scheme}://"]
        for pattern in getattr(self, "crawl_out_scope", None) or []:
            args += ["-crawl-out-scope", pattern]
        if self.max_duration_minutes:
            args += ["-crawl-duration", f"{self.max_duration_minutes}m"]
        if self.rate_limit:
            args += ["-rate-limit", str(self.rate_limit)]
        if self.include_js:
            args += ["-jsluice", "-js-crawl"]
        if self.form_extraction:
            args.append("-automatic-form-fill")
        if self.ignore_query_params:
            args.append("-ignore-query-params")
        if self.exclude_extensions:
            args += ["-extension-filter", ",".join(self.exclude_extensions)]
        if self.headless:
            args += ["-headless", "-no-sandbox"]
        if self.proxy_url:
            args += ["-proxy", self.proxy_url]
        for key, value in self.headers.items():
            args += [HEADER_FLAG, f"{key}: {value}"]
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
            timeout=self.kill_after(),
            recorder=self.recorder,
            tool=KATANA_BINARY,
            extra_args=self.extra_args,
            should_stop=should_stop,
            stderr_sink=stderr_sink,
        ) as stream:
            yield stream.records

    def kill_after(self) -> int:
        """Seconds before the runner kills the crawl. 0 is no limit."""
        minutes = self.max_duration_minutes or 0
        return minutes * 60 + _KILL_SLACK_SECONDS if minutes > 0 else 0
