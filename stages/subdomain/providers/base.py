from __future__ import annotations

import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from shared.definitions.tools import parse_tool_args
from shared.logging import get_logger

if TYPE_CHECKING:
    from shared.enums.api_key import APIProvider
    from shared.enums.subdomain import SubdomainSource
    from tools.runner.models import CommandRecorder

logger = get_logger(__name__)


def proxy_env(proxy_url: str | None) -> dict[str, str] | None:
    """Proxy env vars honored by Go HTTP tools that lack a proxy flag."""
    if not proxy_url:
        return None
    return {
        "HTTP_PROXY": proxy_url,
        "HTTPS_PROXY": proxy_url,
        "ALL_PROXY": proxy_url,
    }


@dataclass
class ProviderContext:
    domain: str
    timeout: int
    threads: int
    proxy_url: str | None
    api_keys: dict[str, str | None]
    recorder: CommandRecorder | None = None
    tool_options: dict[str, str] = field(default_factory=dict)


@dataclass
class ProviderResult:
    source: SubdomainSource
    subdomains: set[str] = field(default_factory=set)
    raw_count: int = 0
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None
    duration_seconds: float = 0.0


class SubdomainProvider(ABC):
    tool: ClassVar[str]
    source: ClassVar[SubdomainSource]
    binary: ClassVar[str | None] = None
    requires_key: ClassVar[APIProvider | None] = None

    def __init__(self, ctx: ProviderContext) -> None:
        self.ctx = ctx

    @property
    def extra_args(self) -> list[str]:
        return parse_tool_args((self.ctx.tool_options or {}).get(self.tool, ""))

    def availability(self) -> tuple[bool, str | None]:
        if self.binary and shutil.which(self.binary) is None:
            return False, f"{self.binary} not installed"
        if self.requires_key is not None and not self.ctx.api_keys.get(
            self.requires_key.value
        ):
            return False, f"{self.requires_key.value} API key not configured"
        return True, None

    @abstractmethod
    def discover(self) -> set[str]: ...

    def run(self) -> ProviderResult:
        ok, reason = self.availability()
        if not ok:
            return ProviderResult(source=self.source, skipped=True, skip_reason=reason)
        start = time.monotonic()
        try:
            subs = self.discover()
        except Exception as e:
            logger.warning("provider %s failed: %s", self.tool, e)
            return ProviderResult(
                source=self.source,
                error=str(e)[:300],
                duration_seconds=round(time.monotonic() - start, 2),
            )
        return ProviderResult(
            source=self.source,
            subdomains=set(subs),
            raw_count=len(subs),
            duration_seconds=round(time.monotonic() - start, 2),
        )
