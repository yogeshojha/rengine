"""dalfox v3 CLI client — fuzzes a list of URLs for XSS and parses its JSONL findings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from shared.logging import get_logger
from tools.dalfox.parser import parse_finding
from tools.nuclei.parser import Finding
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

DALFOX_BINARY = "dalfox"
DEFAULT_TIMEOUT = 3600
HEADER_FLAG = "--headers"
# dalfox exits 1 when it reports findings, 2 on a real error
_FINDINGS_EXIT = 1


class DalfoxError(Exception):
    """Raised when dalfox cannot be started."""


@dataclass
class DalfoxOptions:
    workers: int = 25
    rate: int = 0
    delay_ms: int = 0
    timeout: int = 10
    retries: int = 1
    proxy_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    blind_url: str | None = None
    follow_redirects: bool = False
    only_poc: str = "v,r,a"
    skip_mining: bool = True
    skip_discovery: bool = True


@dataclass
class DalfoxRun:
    findings: list[Finding] = field(default_factory=list)
    requests: int | None = None
    error: str | None = None
    command: str = ""
    duration_seconds: float = 0.0


class DalfoxClient:
    def __init__(
        self,
        *,
        options: DalfoxOptions | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.options = options or DalfoxOptions()
        self.recorder = recorder
        self.extra_args = list(extra_args or [])
        try:
            self._runner = CLIToolRunner(
                DALFOX_BINARY, default_timeout=DEFAULT_TIMEOUT, recorder=recorder
            )
        except ToolNotFoundError as exc:
            raise DalfoxError(str(exc)) from exc

    def args(self) -> list[str]:
        opt = self.options
        args: list[str] = [
            "scan",
            "--input-type",
            "pipe",
            "--format",
            "jsonl",
            "--no-color",
            "--silence",
            "--dedup-urls",
            "off",
            "--workers",
            str(opt.workers),
            "--timeout",
            str(opt.timeout),
            "--retries",
            str(opt.retries),
        ]
        if opt.rate > 0:
            args += ["--rate-limit", str(opt.rate)]
        if opt.delay_ms > 0:
            args += ["--delay", str(opt.delay_ms)]
        if opt.only_poc:
            args += ["--only-poc", opt.only_poc]
        if opt.skip_mining:
            args.append("--skip-mining")
        if opt.skip_discovery:
            args.append("--skip-discovery")
        if opt.follow_redirects:
            args.append("--follow-redirects")
        if opt.proxy_url:
            args += ["--proxy", opt.proxy_url]
        if opt.blind_url:
            args += ["--blind", opt.blind_url]
        for name, value in (opt.headers or {}).items():
            args += [HEADER_FLAG, f"{name}: {value}"]
        return args

    def scan(
        self,
        targets: list[str],
        *,
        on_finding: Callable[[Finding], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
        timeout: int | None = None,
    ) -> DalfoxRun:
        run = DalfoxRun()
        if not targets:
            return run
        result = self._runner.run(
            args=self.args(),
            input_data=targets,
            use_stdin=True,
            use_output_file=False,
            output_format=OutputFormat.JSONL,
            json_flag="--format",
            silent=False,
            timeout=timeout,
            recorder=self.recorder,
            extra_args=self.extra_args,
            should_stop=should_stop,
        )
        run.command = result.command
        run.duration_seconds = result.duration_seconds
        if result.exit_code not in (0, _FINDINGS_EXIT):
            run.error = result.error
        for record in result.json_records:
            if not isinstance(record, dict):
                continue
            if "findings_count" in record:
                run.requests = _int(record.get("total_requests"))
                continue
            finding = parse_finding(record)
            if finding is None:
                continue
            run.findings.append(finding)
            if on_finding is not None:
                on_finding(finding)
        return run


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


__all__ = ["DalfoxClient", "DalfoxError", "DalfoxOptions", "DalfoxRun"]
