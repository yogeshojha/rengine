"""julius CLI client: names the AI service behind a web asset."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from shared.logging import get_logger
from shared.services.proxy_resolve import proxy_env
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

JULIUS_BINARY = "julius"
HEADER_FLAG = "-H"
# julius reads -f only beside a positional target; "-" reads stdin
STDIN_TARGETS = "-"
JULIUS_ALIASES: dict[str, str] = {
    "--header": HEADER_FLAG,
    "--concurrency": "-c",
    "--timeout": "-t",
    "--output": "-o",
    "--file": "-f",
    "--probes-dir": "-p",
}
MCP_PROBES_DIR = os.environ.get("JULIUS_MCP_PROBES_DIR", "/opt/julius/probes-mcp")


class JuliusError(Exception):
    """Raised when julius cannot be started."""


@dataclass
class AiMatch:
    target: str
    service: str
    category: str
    specificity: int
    matched_request: str
    models: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class JuliusRun:
    matches: dict[str, list[AiMatch]] = field(default_factory=dict)
    error: str | None = None
    timed_out: bool = False
    command: str = ""


@dataclass
class JuliusOptions:
    concurrency: int = 10
    timeout: int = 5
    proxy_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    probes_dir: str | None = None


def normalise_target(url: str) -> str:
    """The spelling julius reports a target under: no trailing slash on a bare root."""
    value = url.strip()
    scheme, sep, rest = value.partition("://")
    if not sep:
        return value
    host, slash, path = rest.partition("/")
    if not slash or not path.strip("/"):
        return f"{scheme}://{host}"
    return value


class JuliusClient:
    def __init__(
        self,
        *,
        options: JuliusOptions | None = None,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.options = options or JuliusOptions()
        self.recorder = recorder
        self.extra_args = list(extra_args or [])
        try:
            self._runner = CLIToolRunner(
                JULIUS_BINARY,
                recorder=recorder,
                aliases=JULIUS_ALIASES,
            )
        except ToolNotFoundError as exc:
            raise JuliusError(str(exc)) from exc

    def args(self) -> list[str]:
        opt = self.options
        args = [
            "probe",
            "-o",
            "jsonl",
            "-q",
            "--no-color",
            "--banner=false",
            "--insecure",
            "-c",
            str(max(1, opt.concurrency)),
            "-t",
            str(max(1, opt.timeout)),
        ]
        if opt.probes_dir:
            args += ["-p", opt.probes_dir]
        for name, value in (opt.headers or {}).items():
            args += [HEADER_FLAG, f"{name}: {value}"]
        return args

    def probe(self, targets: list[str], *, timeout: int) -> JuliusRun:
        """One process over the batch, matches keyed by the target as given."""
        run = JuliusRun()
        if not targets:
            return run
        wanted = {normalise_target(t): t for t in targets}
        result = self._runner.run(
            args=[*self.args(), STDIN_TARGETS],
            input_data=list(wanted),
            use_stdin=True,
            use_output_file=False,
            output_format=OutputFormat.JSONL,
            json_flag="-o",
            silent=False,
            timeout=timeout,
            env=proxy_env(self.options.proxy_url),
            recorder=self.recorder,
            tool=JULIUS_BINARY,
            extra_args=self.extra_args,
        )
        run.command = result.command
        run.timed_out = result.timed_out
        if not result.success:
            run.error = result.error
        for record in result.json_records:
            match = parse_record(record)
            if match is None:
                continue
            source = wanted.get(match.target)
            if source is None:
                continue
            match.target = source
            run.matches.setdefault(source, []).append(match)
        return run


def parse_record(record: object) -> AiMatch | None:
    """A julius result, its target folded back to the input it was probed as."""
    if not isinstance(record, dict):
        return None
    service = str(record.get("service") or "").strip().lower()
    reported = str(record.get("target") or "").strip()
    if not service or not reported:
        return None
    path = str(record.get("matched_request") or "")
    base = reported[: -len(path)] if path and reported.endswith(path) else reported
    models = record.get("models")
    try:
        specificity = int(record.get("specificity") or 0)
    except (TypeError, ValueError):
        specificity = 0
    return AiMatch(
        target=normalise_target(base),
        service=service,
        category=str(record.get("category") or ""),
        specificity=specificity,
        matched_request=path,
        models=[str(m) for m in models if m] if isinstance(models, list) else [],
        error=str(record["error"]) if record.get("error") else None,
    )
