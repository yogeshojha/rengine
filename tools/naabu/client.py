"""naabu CLI client - fast TCP port discovery via CLIToolRunner."""

from __future__ import annotations

from shared.logging import get_logger
from tools.runner import CLIToolRunner, OutputFormat, ToolNotFoundError, ToolResult
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

NAABU_BINARY = "naabu"
DEFAULT_TIMEOUT = 600


class NaabuError(Exception):
    """Raised when naabu execution fails."""


def _port_args(ports: str) -> list[str]:
    """Translate a ports spec into naabu flags."""
    spec = (ports or "top-100").strip().lower()
    if spec in ("top-100", "top100"):
        return ["-top-ports", "100"]
    if spec in ("top-1000", "top1000"):
        return ["-top-ports", "1000"]
    if spec in ("full", "all", "-"):
        return ["-p", "-"]
    return ["-p", ports]


class NaabuClient:
    def __init__(
        self,
        *,
        ports: str = "top-100",
        rate: int = 1000,
        concurrency: int = 25,
        timeout: int = 5,
        scan_type: str = "c",
        proxy_url: str | None = None,
        exclude_cdn: bool = True,
        recorder: CommandRecorder | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self.ports = ports
        self.rate = rate
        self.concurrency = concurrency
        self.timeout = timeout
        self.scan_type = scan_type
        self.proxy_url = proxy_url
        self.exclude_cdn = exclude_cdn
        self.recorder = recorder
        self.extra_args = extra_args or []

        try:
            self._runner = CLIToolRunner(NAABU_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise NaabuError(str(e)) from e

    def scan(self, ips: list[str]) -> list[dict]:
        """Scan IPs, returning [{ip, port, protocol}] for each open port."""
        if not ips:
            return []
        args = _port_args(self.ports)
        args += [
            "-s",
            self.scan_type,
            "-rate",
            str(self.rate),
            "-c",
            str(self.concurrency),
            "-timeout",
            str(self.timeout * 1000),
        ]
        if self.exclude_cdn:
            args.append("-exclude-cdn")
        if self.proxy_url:
            args += ["-proxy", self.proxy_url]

        result = self._run(ips, args)
        out: list[dict] = []
        for rec in result.json_records:
            ip = rec.get("ip") or rec.get("host")
            port = rec.get("port")
            if ip and isinstance(port, int):
                out.append(
                    {
                        "ip": str(ip),
                        "port": port,
                        "protocol": rec.get("protocol", "tcp"),
                    }
                )
        return out

    def _run(self, ips: list[str], args: list[str]) -> ToolResult:
        return self._runner.run(
            args=args,
            input_data=ips,
            input_flag="-l",
            use_output_file=False,
            output_format=OutputFormat.JSONL,
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            recorder=self.recorder,
            tool=NAABU_BINARY,
            extra_args=self.extra_args,
        )
