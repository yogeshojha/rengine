from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from shared.logging import get_logger
from tools.runner import CLIToolRunner

logger = get_logger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from shared.services.orchestrator.events import ScanEventPublisher
    from shared.services.scan_resolve import ResolvedScanConfig
    from tools.runner.models import CommandRecorder


@dataclass
class EngineContext:
    scan_id: uuid.UUID
    target_id: uuid.UUID
    project_id: uuid.UUID
    target_value: str
    target_type: str
    resolved: ResolvedScanConfig
    activity_id: uuid.UUID | None = None
    stage_name: str | None = None
    recorder: CommandRecorder | None = None
    events: ScanEventPublisher | None = None
    is_aborted: Callable[[], bool] | None = None


@dataclass
class EngineResult:
    counts: dict[str, int] = field(default_factory=dict)


@dataclass
class NetOptions:
    """User network config threaded into every tool that supports it."""

    proxy_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    user_agent: str | None = None


class EngineAbortedError(Exception):
    """Raised when a stage detects the scan was cancelled mid-run."""


class Engine(ABC):
    name: ClassVar[str]

    def __init__(self, session: Session, context: EngineContext) -> None:
        self.session = session
        self.ctx = context

    @abstractmethod
    def should_run(self) -> bool: ...

    @abstractmethod
    def run(self) -> EngineResult: ...

    def runner(self, binary: str, default_timeout: int = 300) -> CLIToolRunner:
        """A CLIToolRunner pre-bound to this scan's recorder + the tool's custom args."""
        return CLIToolRunner(
            binary,
            default_timeout=default_timeout,
            recorder=self.ctx.recorder,
            extra_args=self.ctx.resolved.tool_args(binary),
        )

    def _check_abort(self) -> None:
        if self.ctx.is_aborted is not None and self.ctx.is_aborted():
            raise EngineAbortedError

    def net_options(self) -> NetOptions:
        """Proxy / headers / user-agent from the resolved scan config."""
        headers = dict(self.ctx.resolved.headers or {})
        user_agent = next(
            (v for k, v in headers.items() if k.lower() == "user-agent"), None
        )
        return NetOptions(
            proxy_url=self.ctx.resolved.proxy_url,
            headers=headers,
            user_agent=user_agent,
        )

    def emit_progress(self, message: str, source: str | None = None) -> None:
        if self.ctx.events is None:
            return
        try:
            self.ctx.events.stage_progress(
                activity_id=self.ctx.activity_id,
                stage=self.ctx.stage_name or self.name,
                message=message,
                source=source,
            )
        except Exception:
            logger.warning("stage progress emit failed", exc_info=True)
