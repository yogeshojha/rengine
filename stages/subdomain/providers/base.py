from __future__ import annotations

import shutil
import time
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from shared.config import base_settings
from shared.definitions.api_keys import API_PROVIDER_META
from shared.definitions.tools import denied_flag, parse_tool_args
from shared.logging import get_logger
from tools.runner import tool_path

if TYPE_CHECKING:
    from shared.enums.api_key import APIProvider
    from shared.enums.subdomain import SubdomainSource
    from tools.runner.models import CommandRecorder, ToolResult

logger = get_logger(__name__)


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
    note: str | None = None
    cut_short: bool = False
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None
    duration_seconds: float = 0.0


class SubdomainProvider(ABC):
    tool: ClassVar[str]
    source: ClassVar[SubdomainSource]
    binary: ClassVar[str | None] = None
    requires_key: ClassVar[APIProvider | None] = None
    touches_target: ClassVar[bool] = False

    def __init__(self, ctx: ProviderContext) -> None:
        self.ctx = ctx
        self._note: str | None = None

    @property
    def extra_args(self) -> list[str]:
        args = parse_tool_args((self.ctx.tool_options or {}).get(self.tool, ""))
        return [] if denied_flag(self.tool, args) else args

    def availability(self) -> tuple[bool, str | None]:
        if self.binary and shutil.which(self.binary, path=tool_path()) is None:
            return False, f"{self.binary} not installed"
        if self.requires_key is not None and not self.ctx.api_keys.get(
            self.requires_key.value
        ):
            name = API_PROVIDER_META[self.requires_key]["name"]
            return False, f"{name} API key not configured"
        return True, None

    def _opener(
        self, *handlers: urllib.request.BaseHandler
    ) -> urllib.request.OpenerDirector:
        proxy = self.ctx.proxy_url
        opener = urllib.request.build_opener(
            *handlers,
            urllib.request.ProxyHandler(
                {"http": proxy, "https": proxy} if proxy else {}
            ),
        )
        opener.addheaders = [("User-Agent", base_settings().EGRESS_USER_AGENT)]
        return opener

    def _checked(self, result: ToolResult) -> ToolResult:
        if result.success:
            return result
        if not result.has_output:
            raise RuntimeError(result.error or f"{self.tool} exited {result.exit_code}")
        self._note = (
            f"stopped at the {self.ctx.timeout:,}s budget"
            if result.timed_out
            else f"exited {result.exit_code}"
        )
        return result

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
            note=self._note,
            duration_seconds=round(time.monotonic() - start, 2),
        )
