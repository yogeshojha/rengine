from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from shared.services.scan_resolve import redact_command
from tools.dalfox.parser import parse_finding
from tools.nuclei.parser import Finding
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

DALFOX_BINARY = "dalfox"
DEFAULT_TIMEOUT = 3600
HEADER_FLAG = "--headers"
DALFOX_ALIASES: dict[str, str] = {
    "-i": "--input-type",
    "-f": "--format",
    "-o": "--output",
    "-S": "--silence",
    "-r": "--rate-limit",
    "-F": "--follow-redirects",
    "-H": HEADER_FLAG,
    "-b": "--blind",
}
# dalfox exits 1 when it reports findings, 2 on a real error
_FINDINGS_EXIT = 1


class DalfoxError(Exception):
    """Raised when dalfox cannot be started."""


@dataclass
class DalfoxOptions:
    workers: int = 25
    rate: int = 0
    timeout: int = 10
    retries: int = 1
    proxy_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    follow_redirects: bool = False


@dataclass
class DalfoxRun:
    requests: int | None = None
    error: str | None = None
    command: str = ""


class DalfoxClient:
    def __init__(
        self,
        *,
        options: DalfoxOptions | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.options = options or DalfoxOptions()
        self.extra_args = list(extra_args or [])
        try:
            self._runner = CLIToolRunner(
                DALFOX_BINARY,
                default_timeout=DEFAULT_TIMEOUT,
                recorder=recorder,
                aliases=DALFOX_ALIASES,
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
            "--only-poc",
            "v,r,a",
            "--skip-mining",
            "--skip-discovery",
        ]
        if opt.rate > 0:
            args += ["--rate-limit", str(opt.rate)]
        if opt.follow_redirects:
            args.append("--follow-redirects")
        if opt.proxy_url:
            args += ["--proxy", opt.proxy_url]
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
            extra_args=self.extra_args,
            should_stop=should_stop,
        )
        run.command = redact_command(result.command)
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
            if on_finding is not None:
                on_finding(finding)
        return run


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


__all__ = ["DALFOX_ALIASES", "DalfoxClient", "DalfoxError", "DalfoxOptions"]
