from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.constants import SCANS_QUEUE
from shared.definitions.workers import INSPECT_TIMEOUT, QUEUES
from shared.models.dashboard import DashboardReadiness
from shared.models.vuln_template import VulnTemplate
from shared.services.celery_dispatch import get_celery_client

REQUIRED_QUEUES = frozenset(spec.name for spec in QUEUES)


def _workers() -> tuple[bool, int | None]:
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
        checks = int(
            await self.session.scalar(select(func.count(VulnTemplate.id))) or 0
        )
        try:
            online, slots = await asyncio.to_thread(_workers)
        except Exception:
            online, slots = False, None
        return DashboardReadiness(
            worker_online=online,
            worker_concurrency=slots,
            checks_ready=checks > 0,
            checks_total=checks,
        )
