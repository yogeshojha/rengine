"""Which bounty programs pay for a target."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.relations import MAX_COVERED_PROGRAMS
from shared.definitions.watch import excluded_by, plan_scope
from shared.models.bounty_program import BountyProgram, BountyScope
from shared.models.relations import ProgramMatch, TargetPrograms
from shared.models.target import Target

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")


def host_of(value: str | None) -> str:
    """The hostname a scope entry or a target value is about."""
    raw = _SCHEME.sub("", (value or "").strip().lower()).split("/")[0]
    return raw.split(":")[0].removeprefix("*.").rstrip(".")


def scope_match(host: str, scopes: list) -> tuple[object | None, bool]:
    """The scope entry this host sits under, and whether the program excludes it."""
    plan = plan_scope(scopes)
    item = next((i for i in plan.items if i.matches(host)), None)
    if item is None:
        return None, False
    by_id = {str(scope.id): scope for scope in scopes}
    return by_id.get(item.scope_id), excluded_by(host, plan.excluded_subdomains)


class ProgramCoverageService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_target(self, project_id: UUID, target_id: UUID) -> TargetPrograms:
        target = await self.session.scalar(
            select(Target).where(
                Target.id == target_id, Target.project_id == project_id
            )
        )
        if target is None:
            return TargetPrograms()
        return await self.for_host(host_of(target.target_value))

    async def for_host(self, host: str) -> TargetPrograms:
        if not host:
            return TargetPrograms()
        programs = await self._candidates(host)
        items: list[ProgramMatch] = []
        for program in programs:
            match = await self._match(program, host)
            if match is not None:
                items.append(match)
        items.sort(key=lambda m: (not m.in_scope, not m.offers_bounties, m.name))
        return TargetPrograms(items=items[:MAX_COVERED_PROGRAMS], total=len(items))

    async def _candidates(self, host: str) -> list:
        """Programs with a scope entry this host could sit under."""
        value = func.lower(BountyScope.target_value)
        rows = await self.session.execute(
            select(
                BountyProgram.id,
                BountyProgram.handle,
                BountyProgram.name,
                BountyProgram.platform,
                BountyProgram.url,
                BountyProgram.offers_bounties,
            )
            .join(BountyScope, BountyScope.program_id == BountyProgram.id)
            .where(
                BountyScope.target_value.isnot(None),
                or_(value == host, func.strpos(host, "." + value) > 0),
            )
            .distinct()
        )
        return list(rows.all())

    async def _match(self, program, host: str) -> ProgramMatch | None:
        rows = await self.session.execute(
            select(
                BountyScope.id,
                BountyScope.asset_type,
                BountyScope.asset_identifier,
                BountyScope.scope_state,
                BountyScope.target_value,
                BountyScope.target_type,
                BountyScope.eligible_for_bounty,
                BountyScope.max_severity,
            ).where(BountyScope.program_id == program.id)
        )
        scopes = list(rows.all())
        scope, excluded = scope_match(host, scopes)
        if scope is None:
            return None
        return ProgramMatch(
            program_id=program.id,
            handle=program.handle,
            name=program.name,
            platform=program.platform,
            url=program.url,
            scope_identifier=scope.asset_identifier,
            asset_type=scope.asset_type,
            wildcard=scope.asset_identifier.strip().startswith("*."),
            in_scope=not excluded,
            offers_bounties=bool(program.offers_bounties),
            eligible_for_bounty=scope.eligible_for_bounty,
            max_severity=scope.max_severity,
        )
