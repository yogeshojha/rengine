from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import update

from shared.definitions.surface import SURFACE_COUNT_COLUMNS, SurfaceDimension
from shared.enums.scan import Phase
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_context import PROBE_SCHEME
from shared.services.celery_dispatch import dispatch_interest_live
from shared.services.debounce import claim
from shared.services.orchestrator.aggregate import derived_counts
from shared.utils.text import REFUSED_ROW
from shared.utils.validation import extract_asn_number
from stages.config import StageConfig
from stages.sink import DEFAULT_ROWS, DEFAULT_SECONDS, ResultSink
from tools.runner import CLIToolRunner
from tools.runner.abort import StageAbortedError

logger = get_logger(__name__)

LIVE_JUDGE_SECONDS = 90

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from shared.services.orchestrator.events import ScanEventPublisher
    from shared.services.scan_resolve import ResolvedScanConfig
    from tools.runner.models import CommandRecorder


@dataclass
class StageContext:
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
class StageResult:
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    partial: bool = False


@dataclass
class NetOptions:
    """User network config threaded into every tool that supports it."""

    proxy_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    probe_scheme: str | None = None


ALL_TARGETS: frozenset[str] = frozenset(t.value for t in TargetType)
IP_TARGETS: frozenset[str] = frozenset(
    {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}
)
DOMAIN_TARGETS: frozenset[str] = frozenset({TargetType.DOMAIN.value})
RANGE_TARGETS: frozenset[str] = frozenset(
    {TargetType.IP_RANGE.value, TargetType.ASN.value}
)


def parse_asn(value: str) -> int | None:
    """The AS number a target value names, or None when it names none."""
    try:
        return extract_asn_number(value)
    except ValueError:
        return None


class Stage(ABC):
    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str] = ""
    phase: ClassVar[str] = Phase.EXPANSION.value
    depends_on: ClassVar[frozenset[str]] = frozenset()
    applies_to: ClassVar[frozenset[str]] = ALL_TARGETS
    tools: ClassVar[tuple[str, ...]] = ()
    api_keys: ClassVar[tuple[str, ...]] = ()
    requires_api_keys: ClassVar[bool] = False
    touches_target: ClassVar[bool] = True
    deferrable: ClassVar[bool] = True
    launch_fields: ClassVar[tuple[str, ...]] = ()
    catalog_hidden: ClassVar[bool] = False
    always_on: ClassVar[bool] = False
    consumes: ClassVar[frozenset[str]] = frozenset()
    produces: ClassVar[frozenset[str]] = frozenset()
    group: ClassVar[str] = ""
    role: ClassVar[str] = ""
    config_model: ClassVar[type[StageConfig]] = StageConfig

    def __init__(self, session: Session, context: StageContext) -> None:
        self.session = session
        self.ctx = context

    @cached_property
    def cfg(self):
        return self.config_model(**(self.ctx.resolved.stages.get(self.name) or {}))

    def should_run(self) -> bool:
        return self.cfg.enabled

    @abstractmethod
    def run(self) -> StageResult: ...

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
            raise StageAbortedError

    def follow_redirects(self, default: bool) -> bool:
        """The scan context's answer when it gave one, the stage's otherwise."""
        override = self.ctx.resolved.follow_redirects
        return default if override is None else override

    def net_options(self) -> NetOptions:
        """Proxy, headers and probe scheme from the resolved scan config."""
        return NetOptions(
            proxy_url=self.ctx.resolved.proxy_url,
            headers=dict(self.ctx.resolved.headers or {}),
            probe_scheme=PROBE_SCHEME.get(self.ctx.resolved.http_protocol),
        )

    def results_sink[T](
        self,
        dimension: str,
        write: Callable[[list[T]], int],
        *,
        rows: int = DEFAULT_ROWS,
        seconds: float = DEFAULT_SECONDS,
    ) -> ResultSink[T]:
        """A sink whose every flush is committed by `write` and then announced to the UI."""
        return ResultSink(
            write,
            announce=lambda _written: self.publish_results(dimension),
            rows=rows,
            seconds=seconds,
        )

    def flush_rows(self, batch: list) -> int:
        """Flush a batch inside a savepoint, returning how many rows the DB refused."""
        pending = list(batch)
        rejected = 0
        try:
            with self.session.begin_nested():
                self.session.add_all(pending)
                self.session.flush()
        except REFUSED_ROW:
            logger.warning("row batch rejected, retrying row by row", stage=self.name)
            for obj in pending:
                try:
                    with self.session.begin_nested():
                        self.session.add(obj)
                        self.session.flush()
                except REFUSED_ROW:
                    rejected += 1
        for obj in pending:
            if obj in self.session:
                self.session.expunge(obj)
        return rejected

    def publish_results(self, dimension: str) -> None:
        """Roll this dimension's scan counters forward and say that rows landed."""
        columns = SURFACE_COUNT_COLUMNS.get(dimension)
        if not columns:
            return
        try:
            counts = derived_counts(self.session, self.ctx.scan_id, columns)
            self.session.execute(
                update(Scan).where(Scan.id == self.ctx.scan_id).values(**counts)
            )
            self.session.commit()
        except Exception:
            logger.warning("live result counters could not be updated", exc_info=True)
            self.session.rollback()
            return
        self._judge_live(dimension)
        if self.ctx.events is None:
            return
        try:
            self.ctx.events.results_found(dimension=dimension, counts=counts)
        except Exception:
            logger.warning("results event emit failed", exc_info=True)

    def _judge_live(self, dimension: str) -> None:
        """Hosts landed."""
        if dimension != SurfaceDimension.WEB_ASSETS.value:
            return
        if not claim(f"interest:{self.ctx.scan_id}", LIVE_JUDGE_SECONDS):
            return
        dispatch_interest_live(str(self.ctx.scan_id))

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
