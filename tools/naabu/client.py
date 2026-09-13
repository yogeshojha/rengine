"""naabu CLI client — active TCP port discovery and passive internetdb lookups."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from shared.definitions.ports import (
    MAX_PORT,
    PortProfile,
    profile_ports,
)
from shared.logging import get_logger
from shared.services.proxy_resolve import is_socks5, proxy_env
from shared.utils.net import bracketed, host_port
from tools.runner import (
    CLIToolRunner,
    OutputFormat,
    StreamOutcome,
    ToolNotFoundError,
    ToolResult,
)
from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

NAABU_BINARY = "naabu"
DEFAULT_TIMEOUT = 3600
SCAN_TYPES = {"connect": "c", "syn": "s"}


class NaabuError(Exception):
    """Raised when naabu execution fails."""


def proxy_args(proxy_url: str | None) -> tuple[list[str], str | None]:
    """naabu's proxy flags, or the reason this proxy cannot be expressed."""
    if not proxy_url:
        return [], None
    parts = urlsplit(proxy_url if "://" in proxy_url else f"socks5://{proxy_url}")
    scheme = (parts.scheme or "").lower()
    if not is_socks5(proxy_url):
        return [], (
            f"naabu takes a socks5 proxy. The scan's {scheme} proxy did not carry "
            "the port scan."
        )
    if not parts.hostname:
        return [], "The scan's proxy names no host. The port scan did not use it."
    address = (
        host_port(parts.hostname, parts.port)
        if parts.port
        else bracketed(parts.hostname)
    )
    args = ["-proxy", address]
    if parts.username:
        user = unquote(parts.username)
        password = unquote(parts.password or "")
        args += ["-proxy-auth", f"{user}:{password}"]
    return args, None


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
        self._proxy_args, self.proxy_warning = proxy_args(self.options.proxy_url)
        try:
            self._runner = CLIToolRunner(NAABU_BINARY, default_timeout=DEFAULT_TIMEOUT)
        except ToolNotFoundError as e:
            raise NaabuError(str(e)) from e

    def scan(self, ips: list[str], port_flags: list[str]) -> list[dict]:
        """Active connect/SYN scan."""
        if not ips:
            return []
        return self._records(self._run(ips, self._scan_args(port_flags)))

    @contextlib.contextmanager
    def stream_scan(
        self,
        ips: list[str],
        port_flags: list[str],
        *,
        should_stop=None,
    ) -> Iterator[StreamOutcome]:
        """The same scan, yielding each open port as naabu prints it."""
        if not ips:
            yield StreamOutcome(records=iter(()), return_code=0)
            return
        with self._runner.stream_json(
            args=[*self._scan_args(port_flags), "-duc"],
            input_data=ips,
            input_flag="-l",
            json_flag="-json",
            silent=True,
            silent_flag="-silent",
            timeout=DEFAULT_TIMEOUT,
            recorder=self.recorder,
            tool=NAABU_BINARY,
            extra_args=self.options.extra_args,
            should_stop=should_stop,
        ) as stream:
            raw = stream.records
            stream.records = (rec for rec in map(_port_record, raw) if rec is not None)
            yield stream

    def _scan_args(self, port_flags: list[str]) -> list[str]:
        opt = self.options
        args = [*port_flags, "-Pn"]
        args += [
            "-s",
            SCAN_TYPES.get(opt.scan_type, "c"),
            "-rate",
            str(opt.rate),
            "-c",
            str(opt.concurrency),
            "-timeout",
            f"{opt.timeout}s",
            "-retries",
            str(opt.retries),
        ]
        if opt.port_threshold > 0:
            args += ["-port-threshold", str(opt.port_threshold)]
        if opt.exclude_ports.strip():
            args += ["-exclude-ports", opt.exclude_ports.strip()]
        return [*args, *self._proxy_args]

    def passive(self, ips: list[str]) -> list[dict]:
        """Ports already known to Shodan's internetdb, fetched through the scan's proxy."""
        if not ips:
            return []
        return self._records(
            self._run(ips, ["-passive"], env=proxy_env(self.options.proxy_url))
        )

    @staticmethod
    def _records(result: ToolResult) -> list[dict]:
        if not result.success and not result.json_records:
            raise NaabuError(result.error or "naabu produced no output")
        return [
            rec for rec in map(_port_record, result.json_records) if rec is not None
        ]

    def _run(
        self, ips: list[str], args: list[str], env: dict[str, str] | None = None
    ) -> ToolResult:
        return self._runner.run(
            args=[*args, "-duc"],
            env=env,
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


def _port_record(rec: dict) -> dict | None:
    ip = rec.get("ip") or rec.get("host")
    port = rec.get("port")
    if not ip or not isinstance(port, int) or not 0 < port <= MAX_PORT:
        return None
    return {
        "ip": str(ip),
        "port": port,
        "protocol": rec.get("protocol") or "tcp",
        "tls": bool(rec.get("tls")),
    }
