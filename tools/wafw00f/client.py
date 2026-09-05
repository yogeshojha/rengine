"""wafw00f CLI client - WAF fingerprinting via CLIToolRunner."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

WAFW00F_BINARY = "wafw00f"
DEFAULT_TIMEOUT = 600
# wafw00f has no threading of its own, so concurrency is one process per shard
DEFAULT_CONCURRENCY = 6
# small shards on purpose: a shard killed at the timeout has written no json at all,
# so the chunk size is what a stalled host can cost the run
SHARD_SIZE = 25


class Wafw00fError(Exception):
    """Raised when wafw00f execution fails."""


@dataclass
class WafScan:
    """What the run actually covered. A shard that never finished names no WAF at all."""

    found: dict[str, str] = field(default_factory=dict)
    scanned: int = 0
    unfinished: int = 0


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _extract_json_array(raw: str) -> list:
    match = re.search(r"\[\s*\{.*\}\s*\]", _ANSI_RE.sub("", raw), re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


class Wafw00fClient:
    def __init__(
        self,
        *,
        proxy_url: str | None = None,
        concurrency: int = DEFAULT_CONCURRENCY,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.proxy_url = proxy_url
        self.concurrency = max(1, concurrency)
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(
                WAFW00F_BINARY, default_timeout=DEFAULT_TIMEOUT
            )
        except ToolNotFoundError as e:
            raise Wafw00fError(str(e)) from e

    def detect(self, urls: list[str]) -> WafScan:
        """Fingerprint every URL, sharded across processes since wafw00f has no threads."""
        scan = WafScan()
        if not urls:
            return scan
        shards = _shard(urls)
        runs = (
            [self._detect_one(shards[0])]
            if len(shards) == 1
            else _run_all(self._detect_one, shards, self.concurrency)
        )
        for shard, (found, complete) in zip(shards, runs, strict=True):
            if complete:
                scan.found.update(found)
                scan.scanned += len(shard)
            else:
                scan.unfinished += len(shard)
        return scan

    def _detect_one(self, urls: list[str]) -> tuple[dict[str, str], bool]:
        args = ["-f", "json", "-a", "-o", "/dev/stdout"]
        if self.proxy_url:
            args += ["-p", self.proxy_url]

        result = self._runner.run(
            args=args,
            input_data=urls,
            input_flag="-i",
            use_output_file=False,
            output_format=OutputFormat.PLAIN,
            silent=False,
            recorder=self.recorder,
            tool=WAFW00F_BINARY,
            extra_args=self.extra_args,
        )

        out: dict[str, str] = {}
        for rec in _extract_json_array(result.stdout):
            url = rec.get("url")
            if url and rec.get("detected") and rec.get("firewall"):
                name = rec["firewall"]
                if name and name.lower() not in ("none", "generic"):
                    out[url] = name[:100]
        # wafw00f writes its json array only at the end, so a killed run says nothing
        return out, not result.timed_out


def _run_all(fn, shards: list[list[str]], concurrency: int) -> list[tuple[dict, bool]]:
    with ThreadPoolExecutor(max_workers=min(concurrency, len(shards))) as pool:
        return list(pool.map(fn, shards))


def _shard(urls: list[str]) -> list[list[str]]:
    return [urls[i : i + SHARD_SIZE] for i in range(0, len(urls), SHARD_SIZE)]
