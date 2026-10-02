from __future__ import annotations

import shutil
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlsplit

import httpx

from shared.definitions.constants import SCAN_USER_AGENT
from shared.definitions.intensity import Transport
from shared.definitions.vulnerabilities import CoverageStatus
from shared.logging import get_logger
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.scope_filter import host_excluded, matches_any
from shared.utils.datetime import utc_now
from shared.utils.host_pacing import HostPacer
from tools.runner import tool_path

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from shared.services.scan_resolve import ResolvedScanConfig
    from stages.base import NetOptions
    from tools.runner.models import CommandRecorder

logger = get_logger(__name__)

_CLIENT_ERROR = 400


@dataclass
class Host:
    """One live web asset the scan already proved answers HTTP."""

    url: str
    host: str
    port: int
    scheme: str


@dataclass
class ProviderContext:
    session: Session
    scan_id: object
    hosts: list[Host]
    apex_domains: list[str]
    cfg: object
    transport: Transport
    resolved: ResolvedScanConfig
    net: NetOptions
    recorder: CommandRecorder | None = None
    on_progress: Callable[[str], None] | None = None
    on_batch: Callable[[tuple[str, list[EndpointObservation]]], None] | None = None
    is_aborted: Callable[[], bool] | None = None


@dataclass
class ProviderResult:
    """One provider's account of its own run."""

    source: str
    tool: str | None = None
    status: str = CoverageStatus.COMPLETED.value
    observations: list[EndpointObservation] = field(default_factory=list)
    hosts_total: int = 0
    hosts_scanned: int | None = None
    urls_found: int | None = None  # every url produced, before dedupe and scope
    pages_fetched: int | None = None
    depth_reached: int | None = None
    errors: int | None = None
    capped: bool = False
    cap_reason: str | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    ended_at: datetime | None = None
    duration_seconds: float | None = None


class UrlProvider(ABC):
    """One way of learning that a URL exists."""

    source: ClassVar[str]
    tool: ClassVar[str | None] = None
    binary: ClassVar[str | None] = None
    touches_target: ClassVar[bool] = True
    uses_session: ClassVar[bool] = False
    reads_endpoints: ClassVar[bool] = False

    def __init__(self, ctx: ProviderContext) -> None:
        self.ctx = ctx
        self._gate = threading.Lock()
        self._next_slot = 0.0
        self._pacer = HostPacer()

    @property
    def extra_args(self) -> list[str]:
        return self.ctx.resolved.tool_args(self.tool or "")

    def availability(self) -> tuple[bool, str | None]:
        if self.binary and shutil.which(self.binary, path=tool_path()) is None:
            return False, f"{self.binary} is not installed on this instance."
        return True, None

    def in_scope(self, url: str) -> bool:
        """A URL belongs to this scan if it is on a known host or under one of its apexes."""
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            return False
        resolved = self.ctx.resolved
        if not host or host_excluded(
            host, resolved.excluded_subdomains or [], resolved.excluded_ips or []
        ):
            return False
        hosts, apexes = self._scope
        return host in hosts or any(
            host == apex or host.endswith(f".{apex}") for apex in apexes
        )

    @cached_property
    def _scope(self) -> tuple[frozenset[str], tuple[str, ...]]:
        return (
            frozenset(h.host for h in self.ctx.hosts),
            tuple(a.lower().lstrip(".") for a in self.ctx.apex_domains),
        )

    def progress(self, message: str) -> None:
        if self.ctx.on_progress is not None:
            self.ctx.on_progress(message)

    def hand_over(self, observations: list[EndpointObservation]) -> None:
        """Give the stage what has been found so far."""
        if not observations or self.ctx.on_batch is None:
            return
        self.ctx.on_batch((self.source, list(observations)))
        observations.clear()

    def aborted(self) -> bool:
        return self.ctx.is_aborted is not None and self.ctx.is_aborted()

    def follow_redirects(self, default: bool) -> bool:
        override = self.ctx.resolved.follow_redirects
        return default if override is None else override

    def path_excluded(self, url: str) -> bool:
        excluded = self.ctx.resolved.excluded_paths or []
        if not excluded:
            return False
        try:
            path = urlsplit(url).path or "/"
        except ValueError:
            return True
        return matches_any(path, excluded)

    def workers(self, cap: int) -> int:
        return max(1, min(cap, self.ctx.transport.threads))

    def http_client(self) -> httpx.Client:
        headers = dict(self.ctx.net.headers or {})
        headers.setdefault("User-Agent", SCAN_USER_AGENT)
        return httpx.Client(
            timeout=self.ctx.transport.timeout,
            follow_redirects=self.follow_redirects(True),
            verify=False,  # noqa: S501
            proxy=self.ctx.net.proxy_url or None,
            headers=headers,
        )

    def fetch_text(
        self, client: httpx.Client, url: str, max_bytes: int, counters
    ) -> str | None:
        """GET a URL under the rate and host pace, its body read up to max_bytes."""
        if self.path_excluded(url):
            return None
        self.throttle()
        counters.fetched += 1
        host = urlsplit(url).hostname or ""
        body = bytearray()
        try:
            with self.host_slot(host), client.stream("GET", url) as response:
                self.host_observed(host, status=response.status_code)
                if response.status_code >= _CLIENT_ERROR:
                    return None
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) >= max_bytes:
                        break
        except (httpx.HTTPError, ValueError):
            self.host_observed(host, transport_error=True)
            counters.errors += 1
            return None
        return bytes(body[:max_bytes]).decode("utf-8", errors="replace")

    def host_slot(self, host: str):
        """Hold one of a host's in-flight slots after paying its adaptive backoff."""
        return self._pacer.slot(host)

    def host_observed(
        self, host: str, *, status: int | None = None, transport_error: bool = False
    ) -> None:
        """Record one response for the host's adaptive pace."""
        self._pacer.observe(host, status=status, transport_error=transport_error)

    def throttle(self) -> None:
        """One request per 1/rate seconds across the provider's workers."""
        rate = self.ctx.transport.rate
        if not rate:
            return
        with self._gate:
            now = time.monotonic()
            wait = self._next_slot - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_slot = max(now, self._next_slot) + 1.0 / rate

    @abstractmethod
    def discover(self, result: ProviderResult) -> None:
        """Fill result.observations, and every count the provider actually knows."""

    def run(self) -> ProviderResult:
        result = ProviderResult(
            source=self.source, tool=self.tool, hosts_total=len(self.ctx.hosts)
        )
        ok, reason = self.availability()
        if not ok:
            result.status = CoverageStatus.SKIPPED.value
            result.error = reason
            result.ended_at = utc_now()
            return result
        start = time.monotonic()
        try:
            self.discover(result)
        except Exception as e:
            logger.warning("url provider %s failed: %s", self.source, e)
            result.status = CoverageStatus.FAILED.value
            result.error = str(e)[:2000]
        result.ended_at = utc_now()
        result.duration_seconds = round(time.monotonic() - start, 2)
        return result
