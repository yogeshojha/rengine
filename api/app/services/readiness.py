from __future__ import annotations

import asyncio
import threading
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.constants import SCANS_QUEUE
from shared.definitions.workers import INSPECT_TIMEOUT, QUEUES
from shared.models.dashboard import DashboardReadiness
from shared.models.vuln_template import VulnTemplate
from shared.services.celery_dispatch import get_celery_client

REQUIRED_QUEUES = frozenset(spec.name for spec in QUEUES)
ONLINE_TTL_SECONDS = 30.0

_last: dict[str, tuple[float, bool, int | None]] = {}
_inspecting = threading.Lock()


def _workers() -> tuple[bool, int | None]:
    asked = time.monotonic()
    seen = _last.get("workers")
    if seen is not None and seen[1] and asked - seen[0] < ONLINE_TTL_SECONDS:
        return True, seen[2]
    if seen is None:
        _inspecting.acquire()
    elif not _inspecting.acquire(blocking=False):
        return seen[1], seen[2]
    try:
        seen = _last.get("workers")
        if seen is not None and seen[0] >= asked:
            return seen[1], seen[2]
        online, slots = _inspect()
        _last["workers"] = (time.monotonic(), online, slots)
        return online, slots
    finally:
        _inspecting.release()


def _inspect() -> tuple[bool, int | None]:
    inspect = get_celery_client().control.inspect(timeout=INSPECT_TIMEOUT)
    pong = inspect.ping() or {}
    online = [name for name, reply in pong.items() if reply.get("ok") == "pong"]
    if not online:
        return False, None
    queues = inspect.active_queues() or {}
    consumed = {name: {q["name"] for q in queues.get(name, [])} for name in online}
    if not REQUIRED_QUEUES.issubset(set().union(*consumed.values())):
        return False, None
    stats = inspect.stats() or {}
    slots = sum(
        int(stats.get(name, {}).get("pool", {}).get("max-concurrency") or 0)
        for name in online
        if SCANS_QUEUE in consumed[name]
    )
    return True, slots or None


class ReadinessService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def readiness(self) -> DashboardReadiness:
        try:
            online, slots = await asyncio.to_thread(_workers)
        except Exception:
            online, slots = False, None
        checks = int(
            await self.session.scalar(select(func.count(VulnTemplate.id))) or 0
        )
        return DashboardReadiness(
            worker_online=online,
            worker_concurrency=slots,
            checks_ready=checks > 0,
            checks_total=checks,
        )
