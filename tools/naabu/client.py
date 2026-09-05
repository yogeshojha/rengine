"""naabu CLI client — active TCP port discovery and passive internetdb lookups."""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.definitions.ports import (
    MAX_PORT,
    PortProfile,
    profile_ports,
)
from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError, ToolResult
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

NAABU_BINARY = "naabu"
DEFAULT_TIMEOUT = 3600
SCAN_TYPES = {"connect": "c", "syn": "s"}


class NaabuError(Exception):
    """Raised when naabu execution fails."""


def port_args(profile: str, custom: str = "") -> list[str]:
    """Translate a port profile (or a literal spec) into naabu port flags."""
    explicit = profile_ports(profile)
    if explicit:
        return ["-p", ",".join(str(p) for p in explicit)]
    if profile == PortProfile.TOP_100.value:
        return ["-top-ports", "100"]
    if profile == PortProfile.TOP_1000.value:
        return ["-top-ports", "1000"]
    if profile == PortProfile.FULL.value:
        return ["-p", f"1-{MAX_PORT}"]
    spec = (custom or "").strip()
    return ["-p", spec] if spec else ["-top-ports", "100"]


@dataclass
class NaabuOptions:
    rate: int = 1000
    concurrency: int = 25
    timeout: int = 5
    retries: int = 2
    scan_type: str = "connect"
    port_threshold: int = 0
    exclude_ports: str = ""
    proxy_url: str | None = None
    extra_args: list[str] = field(default_factory=list)


class NaabuClient:
    def __init__(
        self,
        *,
        options: NaabuOptions | None = None,
        recorder: CommandRecorder | None = None,
    ) -> None:
        self.options = options or NaabuOptions()
        self.recorder = recorder
        try:
            self._runner = CLIToolRunner(NAABU_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise NaabuError(str(e)) from e

    def scan(self, ips: list[str], port_flags: list[str]) -> list[dict]:
        """Active connect/SYN scan. Returns [{ip, port, protocol, tls}] per open port."""
        if not ips:
            return []
        opt = self.options
        args = [*port_flags, "-Pn"]
        args += [
            "-s",
            SCAN_TYPES.get(opt.scan_type, "c"),
            "-rate",
            str(opt.rate),
            "-c",
            str(opt.concurrency),
            # naabu parses -timeout as a go duration: a bare number is not
            # milliseconds, and costs a fixed ~135s per run for the same results
            "-timeout",
            f"{opt.timeout}s",
            "-retries",
            str(opt.retries),
        ]
        if opt.port_threshold > 0:
            args += ["-port-threshold", str(opt.port_threshold)]
        if opt.exclude_ports.strip():
            args += ["-exclude-ports", opt.exclude_ports.strip()]
        if opt.proxy_url:
            args += ["-proxy", opt.proxy_url]
        return self._records(self._run(ips, args))

    def passive(self, ips: list[str]) -> list[dict]:
        """Ports already known to Shodan's internetdb. Sends nothing to the target."""
        if not ips:
            return []
        return self._records(self._run(ips, ["-passive"]))

    @staticmethod
    def _records(result: ToolResult) -> list[dict]:
        # a timed-out or crashed run returns nothing; reporting that as zero open ports is a lie
        if not result.success and not result.json_records:
            raise NaabuError(result.error or "naabu produced no output")
        out: list[dict] = []
        for rec in result.json_records:
            ip = rec.get("ip") or rec.get("host")
            port = rec.get("port")
            if not ip or not isinstance(port, int) or not 0 < port <= MAX_PORT:
                continue
            out.append(
                {
                    "ip": str(ip),
                    "port": port,
                    "protocol": rec.get("protocol") or "tcp",
                    "tls": bool(rec.get("tls")),
                }
            )
        return out

    def _run(self, ips: list[str], args: list[str]) -> ToolResult:
        return self._runner.run(
            args=[*args, "-duc"],
            input_data=ips,
            input_flag="-l",
            use_output_file=False,
            output_format=OutputFormat.JSONL,
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=NAABU_BINARY,
            extra_args=self.options.extra_args,
        )
