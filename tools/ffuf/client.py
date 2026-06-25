"""ffuf CLI client - virtual-host (Host-header) bruteforce via CLIToolRunner."""

from __future__ import annotations

import json

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError

logger = get_logger(__name__)

FFUF_BINARY = "ffuf"
DEFAULT_TIMEOUT = 1800
DEFAULT_MATCH_CODES = "200,204,301,302,307,401,403,405,500"


class FfufError(Exception):
    """Raised when ffuf execution fails."""


class FfufClient:
    def __init__(
        self,
        *,
        wordlist: str,
        threads: int = 40,
        rate: int = 0,
        match_codes: str = DEFAULT_MATCH_CODES,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
        recorder=None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.wordlist = wordlist
        self.threads = threads
        self.rate = rate
        self.match_codes = match_codes
        self.proxy_url = proxy_url
        self.headers = headers or {}
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(FFUF_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise FfufError(str(e)) from e

    def vhost(self, ip: str, base_host: str, scheme: str = "http") -> list[str]:
        """Bruteforce `Host: FUZZ.<base_host>` against an IP; return found labels."""
        args = [
            "-w",
            f"{self.wordlist}:FUZZ",
            "-u",
            f"{scheme}://{ip}/",
            "-H",
            f"Host: FUZZ.{base_host}",
            "-ac",
            "-mc",
            self.match_codes,
            "-t",
            str(self.threads),
            "-of",
            "json",
            "-o",
            "/dev/stdout",
            "-s",
        ]
        if self.rate:
            args += ["-rate", str(self.rate)]
        if self.proxy_url:
            args += ["-x", self.proxy_url]
        for key, value in self.headers.items():
            args += ["-H", f"{key}: {value}"]

        result = self._runner.run(
            args=args,
            use_output_file=False,
            output_format=OutputFormat.PLAIN,
            silent=False,
            recorder=self.recorder,
            tool=FFUF_BINARY,
            extra_args=self.extra_args,
        )
        return self._parse(result.stdout)

    @staticmethod
    def _parse(raw: str) -> list[str]:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            return []
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return []
        labels = []
        for item in data.get("results") or []:
            label = (item.get("input") or {}).get("FUZZ")
            if label:
                labels.append(str(label).strip().lower())
        return list(dict.fromkeys(labels))
