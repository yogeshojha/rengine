"""A target's infostealer report, its hosts read against the scan that covers them."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.infostealer import (
    AUDIENCE_ORDER,
    MAX_PATHS_PER_HOST,
    Audience,
    HostStanding,
    any_query,
)
from shared.models.infostealer import (
    InfostealerHost,
    InfostealerLogin,
    InfostealerPath,
    InfostealerSummary,
    NamedCountRead,
    TargetInfostealer,
    TargetInfostealerRead,
)
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain


def _named(rows: list) -> list[NamedCountRead]:
    return [NamedCountRead.model_validate(r) for r in rows or [] if isinstance(r, dict)]


def _standing(status: int | None, addresses: int | None) -> str:
    if status is not None:
        return HostStanding.WEB_ASSET.value
    if addresses:
        return HostStanding.RESOLVED.value
    return HostStanding.UNRESOLVED.value


class InfostealerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _record(self, target_id: UUID) -> TargetInfostealer | None:
        return await self.session.scalar(
            select(TargetInfostealer).where(TargetInfostealer.target_id == target_id)
        )

    async def _host_count(self, target_id: UUID) -> int:
        count = await self.session.scalar(
            select(func.count(func.distinct(InfostealerLogin.host))).where(
                InfostealerLogin.target_id == target_id
            )
        )
        return int(count or 0)

    async def summary(self, target_id: UUID) -> InfostealerSummary | None:
        record = await self._record(target_id)
        if record is None:
            return None
        return InfostealerSummary(
            domain=record.domain,
            checked_at=record.checked_at,
            total=record.total,
            employees=record.employees,
            users=record.users,
            third_parties=record.third_parties,
            host_count=await self._host_count(target_id),
        )

    async def _covering(self, target_id: UUID, scan_id: UUID | None) -> UUID | None:
        if scan_id is None:
            return None
        owner = await self.session.scalar(
            select(Scan.target_id).where(Scan.id == scan_id)
        )
        return scan_id if owner == target_id else None

    async def _standings(
        self, scan_id: UUID | None, names: list[str]
    ) -> dict[str, str]:
        if scan_id is None or not names:
            return {}
        rows = await self.session.execute(
            select(
                Subdomain.name,
                Subdomain.http_status,
                func.json_array_length(Subdomain.resolved_ips),
            ).where(Subdomain.scan_id == scan_id, Subdomain.name.in_(names))
        )
        return {name: _standing(status, addresses) for name, status, addresses in rows}

    async def report(
        self, target_id: UUID, scan_id: UUID | None = None
    ) -> TargetInfostealerRead | None:
        record = await self._record(target_id)
        if record is None:
            return None
        logins = (
            await self.session.scalars(
                select(InfostealerLogin).where(InfostealerLogin.target_id == target_id)
            )
        ).all()
        by_host: dict[str, list[InfostealerLogin]] = defaultdict(list)
        for login in logins:
            by_host[login.host].append(login)
        covering = await self._covering(target_id, scan_id)
        standings = await self._standings(covering, sorted(by_host))
        rank = {audience: i for i, audience in enumerate(AUDIENCE_ORDER)}

        hosts: list[InfostealerHost] = []
        for host, rows in by_host.items():
            rows.sort(
                key=lambda r: (
                    rank.get(r.audience, len(rank)),
                    -r.credentials,
                    r.path or "",
                )
            )
            hosts.append(
                InfostealerHost(
                    host=host,
                    employee_credentials=sum(
                        r.credentials
                        for r in rows
                        if r.audience == Audience.EMPLOYEE.value
                    ),
                    user_credentials=sum(
                        r.credentials for r in rows if r.audience == Audience.USER.value
                    ),
                    standing=standings.get(host, HostStanding.ABSENT.value),
                    paths=[
                        InfostealerPath(
                            audience=r.audience,
                            scheme=r.scheme,
                            port=r.port,
                            path=r.path,
                            credentials=r.credentials,
                        )
                        for r in rows[:MAX_PATHS_PER_HOST]
                    ],
                )
            )
        hosts.sort(key=lambda h: (-h.employee_credentials, -h.user_credentials, h.host))

        return TargetInfostealerRead(
            domain=record.domain,
            checked_at=record.checked_at,
            total=record.total,
            employees=record.employees,
            users=record.users,
            third_parties=record.third_parties,
            host_count=len(hosts),
            total_urls=record.total_urls,
            last_employee_at=record.last_employee_at,
            last_user_at=record.last_user_at,
            scan_id=covering,
            in_scan=sum(1 for h in hosts if h.standing != HostStanding.ABSENT.value),
            query=any_query(),
            hosts=hosts,
            families=_named(record.families),
            passwords=record.passwords or {},
            applications=_named(record.applications),
            services=_named(record.services),
        )
