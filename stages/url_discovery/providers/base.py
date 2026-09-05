from __future__ import annotations

import shutil
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlsplit

from shared.definitions.tools import parse_tool_args
from shared.definitions.vulnerabilities import CoverageStatus
from shared.logging import get_logger
from shared.services.endpoint_inventory import EndpointObservation
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from shared.enums.api_key import APIProvider
    from shared.services.scan_resolve import ResolvedScanConfig
    from stages.base import NetOptions
    from tools.runner.models import CommandRecorder

logger = get_logger(__name__)


@dataclass
class Host:
    """One live web asset the scan already proved answers HTTP."""

    url: str
    host: str
    port: int
    scheme: str
    status_code: int | None = None


@dataclass
class ProviderContext:
    session: Session
    scan_id: object
    target_id: object
    project_id: object
    target_value: str
    target_type: str
    hosts: list[Host]
    apex_domains: list[str]
    cfg: object
    resolved: ResolvedScanConfig
    net: NetOptions
    recorder: CommandRecorder | None = None
    api_keys: dict[str, str | None] = field(default_factory=dict)
    on_progress: Callable[[str], None] | None = None
    is_aborted: Callable[[], bool] | None = None


@dataclass
class ProviderResult:
    """One provider's account of its own run. A null count means unknown, never zero."""

    source: str
    tool: str | None = None
    status: str = CoverageStatus.COMPLETED.value
    observations: list[EndpointObservation] = field(default_factory=list)
    hosts_total: int = 0
    hosts_scanned: int | None = None
    hosts_dropped: list[str] = field(default_factory=list)
    urls_found: int | None = None
    pages_fetched: int | None = None
    depth_reached: int | None = None
    errors: int | None = None
    capped: bool = False
    cap_reason: str | None = None
    command: str | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    ended_at: datetime | None = None
    duration_seconds: float | None = None


class UrlProvider(ABC):
    """One way of learning that a URL exists."""

    source: ClassVar[str]
    tool: ClassVar[str | None] = None
    binary: ClassVar[str | None] = None
    requires_key: ClassVar[APIProvider | None] = None
    # a provider that sends no request to the target survives a passive-intensity scan
    touches_target: ClassVar[bool] = True
    # reads the scan's own rows, so it runs on the stage thread rather than in the pool
    uses_session: ClassVar[bool] = False

    def __init__(self, ctx: ProviderContext) -> None:
        self.ctx = ctx

    @property
    def extra_args(self) -> list[str]:
        options = getattr(self.ctx.resolved, "tool_options", None) or {}
        return parse_tool_args(options.get(self.tool or "", ""))

    def availability(self) -> tuple[bool, str | None]:
        if self.binary and shutil.which(self.binary) is None:
            return False, f"{self.binary} is not installed on this instance."
        if self.requires_key is not None and not self.ctx.api_keys.get(
            self.requires_key.value
        ):
            return False, f"No {self.requires_key.value} API key is configured."
        return True, None

    def in_scope(self, url: str) -> bool:
        """A URL belongs to this scan if it is on a known host or under one of its apexes.

        Hosts alone are not enough: the host list is capped, and a sitemap legitimately
        names hosts the cap left out.
        """
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            return False
        if not host:
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

    def aborted(self) -> bool:
        return self.ctx.is_aborted is not None and self.ctx.is_aborted()

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
