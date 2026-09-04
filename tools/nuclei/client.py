"""nuclei CLI client — runs an explicit template set and keeps nuclei's own account of the run."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from shared.logging import get_logger
from tools.nuclei.parser import Finding, parse_finding
from tools.runner import CLIToolRunner, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

NUCLEI_BINARY = "nuclei"
DEFAULT_TIMEOUT = 7200

# nuclei reports a host it gave up on only when -silent is absent
_DROPPED = re.compile(
    r"Skipped\s+(?P<host>\S+)\s+from target list as found unresponsive.*?:\s*(?P<reason>.*)$"
)
MAX_DROPPED = 500
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class NucleiError(Exception):
    """Raised when nuclei cannot be started."""


class _CallbackError(Exception):
    """Carries an exception the caller's on_finding raised, past this module's own handler."""

    def __init__(self, cause: BaseException) -> None:
        super().__init__(str(cause))
        self.cause = cause


@dataclass
class NucleiOptions:
    templates_file: str | None = None
    template_paths: tuple[str, ...] = ()
    rate: int = 150
    concurrency: int = 25
    bulk_size: int = 25
    timeout: int = 10
    retries: int = 1
    max_host_error: int = 30
    max_minutes: int = 0
    headless: bool = False
    interactsh: bool = False
    interactsh_server: str | None = None
    honeypot_threshold: int = 0
    proxy_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    exclude_hosts: tuple[str, ...] = ()
    follow_redirects: bool | None = None
    extra_args: list[str] = field(default_factory=list)


@dataclass
class NucleiStats:
    """nuclei's own numbers. A field is None when nuclei did not report it — never zero."""

    templates: int | None = None
    hosts: int | None = None
    requests: int | None = None
    total: int | None = None
    matched: int | None = None
    errors: int | None = None
    duration: str | None = None
    rps: int | None = None


@dataclass
class NucleiRun:
    findings: list[Finding] = field(default_factory=list)
    stats: NucleiStats = field(default_factory=NucleiStats)
    dropped: list[dict] = field(default_factory=list)
    exit_code: int = 0
    error: str | None = None
    command: str = ""
    duration_seconds: float = 0.0
    started: bool = False


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


class NucleiClient:
    def __init__(
        self,
        *,
        options: NucleiOptions | None = None,
        recorder: CommandRecorder | None = None,
    ) -> None:
        self.options = options or NucleiOptions()
        self.recorder = recorder
        try:
            self._runner = CLIToolRunner(
                NUCLEI_BINARY,
                default_timeout=DEFAULT_TIMEOUT,
                recorder=recorder,
                extra_args=list(self.options.extra_args),
            )
        except ToolNotFoundError as exc:
            raise NucleiError(str(exc)) from exc

    def args(self) -> list[str]:
        opt = self.options
        # the resolved template list IS the contract: no severity or tag filter rides on top
        args: list[str] = []
        if opt.templates_file:
            args += ["-t", opt.templates_file]
        for path in opt.template_paths:
            args += ["-t", path]
        args += [
            "-jsonl",
            "-omit-template",
            "-no-color",
            "-disable-update-check",
            "-stats",
            "-stats-json",
            "-stats-interval",
            "20",
            "-rate-limit",
            str(opt.rate),
            "-concurrency",
            str(opt.concurrency),
            "-bulk-size",
            str(opt.bulk_size),
            "-timeout",
            str(opt.timeout),
            "-retries",
            str(opt.retries),
            "-max-host-error",
            str(opt.max_host_error),
        ]
        if opt.max_minutes > 0:
            args += ["-max-time", f"{opt.max_minutes}m"]
        if opt.headless:
            args += ["-headless", "-system-chrome"]
        if not opt.interactsh:
            args.append("-no-interactsh")
        elif opt.interactsh_server:
            args += ["-interactsh-server", opt.interactsh_server]
        if opt.honeypot_threshold > 0:
            args += [
                "-honeypot-detect",
                "-honeypot-threshold",
                str(opt.honeypot_threshold),
                "-suppress-honeypot",
            ]
        if opt.proxy_url:
            args += ["-proxy", opt.proxy_url]
        for name, value in (opt.headers or {}).items():
            args += ["-header", f"{name}: {value}"]
        if opt.exclude_hosts:
            args += ["-exclude-hosts", ",".join(opt.exclude_hosts)]
        if opt.follow_redirects is True:
            args.append("-follow-redirects")
        elif opt.follow_redirects is False:
            args.append("-disable-redirects")
        return args

    def scan(
        self,
        targets: list[str],
        *,
        on_finding: Callable[[Finding], None] | None = None,
        on_progress: Callable[[NucleiStats], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
        timeout: int | None = None,
    ) -> NucleiRun:
        """Run one group and return everything nuclei said about it."""
        run = NucleiRun()
        if not targets:
            return run

        stats = NucleiStats()
        dropped: list[dict] = []
        # nuclei repeats the drop notice per attempt; one host is one dropped host
        seen_drops: set[str] = set()

        def _stderr(line: str) -> None:
            clean = _ANSI.sub("", line).strip()
            if not clean:
                return
            if clean.startswith("{") and '"templates"' in clean:
                self._absorb(stats, clean)
                if on_progress is not None:
                    on_progress(stats)
                return
            match = _DROPPED.search(clean)
            if match is None or len(dropped) >= MAX_DROPPED:
                return
            host = match.group("host")
            if host in seen_drops:
                return
            seen_drops.add(host)
            dropped.append(
                {"host": host, "reason": match.group("reason").strip()[:200]}
            )

        started = time.monotonic()
        run.started = True
        try:
            with self._stream(targets, _stderr, timeout, should_stop) as records:
                for record in records:
                    finding = parse_finding(record)
                    if finding is None:
                        continue
                    run.findings.append(finding)
                    if on_finding is None:
                        continue
                    try:
                        on_finding(finding)
                    except Exception as exc:
                        raise _CallbackError(exc) from exc
        except _CallbackError as wrapper:
            # the caller asked us to stop (cancelled scan, budget); that is not a nuclei failure
            run.duration_seconds = round(time.monotonic() - started, 2)
            run.stats = stats
            run.dropped = dropped
            raise wrapper.cause from None
        except Exception as exc:
            run.error = str(exc)[:500]
            logger.warning("nuclei run failed", error=run.error)
        run.duration_seconds = round(time.monotonic() - started, 2)
        run.stats = stats
        run.dropped = dropped
        run.command = self._command(targets)
        return run

    def _stream(self, targets: list[str], sink, timeout: int | None, should_stop=None):
        return self._runner.stream_json(
            args=self.args(),
            input_data=targets,
            input_flag="-list",
            json_flag="-jsonl",
            silent=False,
            timeout=timeout,
            stderr_sink=sink,
            should_stop=should_stop,
        )

    def _command(self, targets: list[str]) -> str:
        return " ".join(
            [NUCLEI_BINARY, "-list", f"<{len(targets)} targets>", *self.args()]
        )

    @staticmethod
    def _absorb(stats: NucleiStats, line: str) -> None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        for key, attr in (
            ("templates", "templates"),
            ("hosts", "hosts"),
            ("requests", "requests"),
            ("total", "total"),
            ("matched", "matched"),
            ("errors", "errors"),
            ("rps", "rps"),
        ):
            value = _int(payload.get(key))
            if value is not None:
                setattr(stats, attr, value)
        duration = payload.get("duration")
        if isinstance(duration, str) and duration:
            stats.duration = duration


def write_template_list(paths: list[str]) -> Path:
    """Persist the resolved template set so nuclei runs exactly what was counted."""
    descriptor, name = tempfile.mkstemp(prefix="nuclei_templates_", suffix=".txt")
    with os.fdopen(descriptor, "w") as handle:
        handle.write("\n".join(paths) + "\n")
    return Path(name)


def iter_findings(run: NucleiRun) -> Iterator[Finding]:
    yield from run.findings
