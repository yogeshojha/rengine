"""httpx CLI client - HTTP probing + asset enrichment via CLIToolRunner."""

from __future__ import annotations

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

HTTPX_BINARY = "httpx"
DEFAULT_TIMEOUT = 900

# one probe → the whole enriched asset (status/title/tech/tls/cdn/asn/jarm/favicon/hash)
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
    "-no-color",
]


class HttpxError(Exception):
    """Raised when httpx execution fails."""


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

    def probe(self, targets: list[str]) -> list[dict]:
        """Probe host/host:port/URL targets; return raw httpx JSON records."""
        if not targets:
            return []
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

        result = self._runner.run(
            args=args,
            input_data=targets,
            input_flag="-l",
            use_output_file=False,
            output_format=OutputFormat.JSONL,
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=HTTPX_BINARY,
            extra_args=self.extra_args,
        )
        return result.json_records

    def capture(self, targets: list[str]) -> list[dict]:
        """Screenshot targets via headless chromium; records carry screenshot_path."""
        if not targets:
            return []
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

        result = self._runner.run(
            args=args,
            input_data=targets,
            input_flag="-l",
            use_output_file=False,
            output_format=OutputFormat.JSONL,
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=HTTPX_BINARY,
            extra_args=self.extra_args,
        )
        return result.json_records
