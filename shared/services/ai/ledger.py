"""One row per provider call, written by the client itself."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from shared.definitions.ai import TASK_FEATURE, Charge, Usage, price
from shared.logging import get_logger
from shared.utils.datetime import utc_now
from shared.utils.net import redact_url_queries

logger = get_logger(__name__)

MAX_ERROR = 300
_USERINFO = re.compile(r"://[^/@\s]+@")


@dataclass(frozen=True)
class Source:
    kind: str = ""
    id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


@dataclass
class CallRecord:
    task: str
    provider: str
    model: str
    ok: bool
    usage: Usage = field(default_factory=Usage)
    charge: Charge | None = None
    latency_ms: int = 0
    cached: bool = False
    rounds: int = 1
    error: str | None = None
    source: Source = field(default_factory=Source)
    at: object = field(default_factory=utc_now)

    @property
    def feature(self) -> str:
        return TASK_FEATURE.get(self.task, self.task)

    def priced(self) -> Charge:
        if self.cached:
            return Charge(0.0)
        return self.charge or price(self.usage, None, self.provider)


Writer = Callable[[CallRecord], None]

_writer: Writer | None = None
_NO_SOURCE = Source()
_source: ContextVar[Source] = ContextVar("ai_source", default=_NO_SOURCE)


def register(writer: Writer | None) -> None:
    global _writer  # noqa: PLW0603
    _writer = writer


@contextmanager
def source(
    kind: str, id: uuid.UUID | None = None, user_id: uuid.UUID | None = None
) -> Iterator[None]:
    token = _source.set(Source(kind, id, user_id))
    try:
        yield
    finally:
        _source.reset(token)


def current() -> Source:
    return _source.get()


def scrub(text: str) -> str:
    """Error text with no URL query and no URL credentials."""
    return _USERINFO.sub("://", redact_url_queries(text))


def record(rec: CallRecord) -> None:
    if rec.source == _NO_SOURCE:
        rec.source = _source.get()
    if rec.error:
        rec.error = scrub(rec.error)[:MAX_ERROR]
    if _writer is None:
        logger.debug("ai call not recorded", task=rec.task, ok=rec.ok)
        return
    try:
        _writer(rec)
    except Exception as exc:
        logger.warning("ai ledger write failed", task=rec.task, error=str(exc))


def row_values(rec: CallRecord) -> dict:
    """The columns of one `ai_calls` row."""
    usage, charge = rec.usage, rec.priced()
    return {
        "at": rec.at,
        "task": rec.task,
        "feature": rec.feature,
        "provider": rec.provider,
        "model": rec.model,
        "ok": rec.ok,
        "cached": rec.cached,
        "rounds": rec.rounds,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": usage.cache_read_tokens,
        "cache_write_tokens": usage.cache_write_tokens,
        "cost_usd": charge.usd,
        "cost_source": charge.source,
        "input_per_mtok": charge.rates.input if charge.rates else None,
        "output_per_mtok": charge.rates.output if charge.rates else None,
        "latency_ms": rec.latency_ms,
        "error": rec.error,
        "source_kind": rec.source.kind or None,
        "source_id": rec.source.id,
        "user_id": rec.source.user_id,
    }
