"""How many scans run at once, and which pending scan starts next."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_, select, text, tuple_

from shared.definitions.scan_admission import AUTOMATIC
from shared.definitions.watch import WATCH_HOST_KEY
from shared.enums.scan import ScanStatus
from shared.logging import get_logger
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.models.scan import Scan
from shared.services import locks, worker_presence
from shared.services.celery_dispatch import dispatch_scan_run

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from sqlalchemy.sql.elements import ColumnElement

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def widest_step() -> int:
    from stages.registry import execution_plan  # noqa: PLC0415

    return max((len(step) for step in execution_plan()), default=1)


def automatic_limit() -> int:
    return max(1, worker_presence.stage_slots() // widest_step())


def resolve(configured: int | None) -> int:
    return configured if configured and configured > AUTOMATIC else automatic_limit()


def exempt(scan: Scan) -> bool:
    """A watch probe starts at once."""
    return bool((scan.execution_config or {}).get(WATCH_HOST_KEY))


def _is_probe() -> ColumnElement[bool]:
    return Scan.execution_config[WATCH_HOST_KEY].as_string().is_not(None)


def waiting() -> ColumnElement[bool]:
    """Pending scans that take their turn."""
    return and_(Scan.status == ScanStatus.PENDING.value, ~_is_probe())


def running() -> ColumnElement[bool]:
    return Scan.status == ScanStatus.RUNNING.value


def queue_order():
    return (Scan.created_at, Scan.id)


def _ahead_of(scan: Scan) -> ColumnElement[bool]:
    return tuple_(*queue_order()) < tuple_(scan.created_at, scan.id)


def configured(session: Session) -> int:
    value = session.scalar(
        select(InstanceSettings.concurrent_scans).where(
            InstanceSettings.singleton_key == SINGLETON_KEY
        )
    )
    return value or AUTOMATIC


def admits(session: Session, scan: Scan) -> bool:
    """Whether a pending scan may start now. Holds the admission lock to the end of the transaction."""
    if exempt(scan):
        return True
    limit = resolve(configured(session))
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": locks.SCAN_ADMISSION}
    )
    busy = session.scalar(
        select(func.count())
        .select_from(Scan)
        .where(or_(running(), and_(waiting(), _ahead_of(scan))))
    )
    return (busy or 0) < limit


def admissible(session: Session) -> list[Scan]:
    """The pending scans the limit lets start now, oldest first."""
    limit = resolve(configured(session))
    busy = session.scalar(select(func.count()).select_from(Scan).where(running())) or 0
    probes = list(
        session.execute(
            select(Scan).where(Scan.status == ScanStatus.PENDING.value, _is_probe())
        )
        .scalars()
        .all()
    )
    free = limit - busy
    if free <= 0:
        return probes
    turn = list(
        session.execute(
            select(Scan).where(waiting()).order_by(*queue_order()).limit(free)
        )
        .scalars()
        .all()
    )
    return probes + turn


def admit_waiting(session: Session) -> list[str]:
    """Send the launch for every pending scan whose turn has come."""
    started = []
    for scan in admissible(session):
        try:
            dispatch_scan_run(str(scan.id), scan.run_epoch or 0)
        except Exception:
            logger.warning("launch of queued scan %s not sent", scan.id, exc_info=True)
            continue
        started.append(str(scan.id))
    return started


def positions_query(ids: list) -> object:
    """Place of each waiting scan in the queue, counted from one."""
    ranked = (
        select(
            Scan.id.label("id"),
            func.row_number().over(order_by=queue_order()).label("place"),
        )
        .where(waiting())
        .subquery()
    )
    return select(ranked.c.id, ranked.c.place).where(ranked.c.id.in_(ids))


def running_query() -> object:
    return select(func.count()).select_from(Scan).where(running())
