"""Which bounty programs pay for a target."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import Text, bindparam, func, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.relations import MAX_COVERED_PROGRAMS
from shared.definitions.watch import excluded_by, plan_scope
from shared.models.bounty_program import BountyProgram, BountyScope
from shared.models.relations import ProgramMatch, TargetPrograms
from shared.models.target import Target
from shared.utils.net import split_host_port

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")


def host_of(value: str | None) -> str:
    """The hostname a scope entry or a target value is about."""
    raw = _SCHEME.sub("", (value or "").strip().lower()).split("/")[0]
    return split_host_port(raw)[0].removeprefix("*.").rstrip(".")


def scope_values(hosts: set[str]) -> list[str]:
    """Each host and every run of characters that follows one of its dots."""
    out: set[str] = set()
    for host in hosts:
        out.add(host)
        dot = host.find(".")
        while dot != -1:
            tail = host[dot + 1 :]
            out.update(tail[:end] for end in range(len(tail) + 1))
            dot = host.find(".", dot + 1)
    return sorted(out)


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
        programs, scopes_by_program = await self._load({host})
        items: list[ProgramMatch] = []
        for program in programs:
            match = self._match_scopes(
                program, host, scopes_by_program.get(program.id, [])
            )
            if match is not None:
                items.append(match)
        items.sort(key=lambda m: (not m.in_scope, not m.offers_bounties, m.name))
        return TargetPrograms(items=items[:MAX_COVERED_PROGRAMS], total=len(items))

    async def best_for_hosts(self, hosts: set[str]) -> dict[str, ProgramMatch]:
        """The strongest program match for each host."""
        clean = {host_of(h) for h in hosts} - {""}
        if not clean:
            return {}
        programs, scopes_by_program = await self._load(clean)
        best: dict[str, ProgramMatch] = {}
        for host in clean:
            matches: list[ProgramMatch] = []
            for program in programs:
                match = self._match_scopes(
                    program, host, scopes_by_program.get(program.id, [])
                )
                if match is not None:
                    matches.append(match)
            if matches:
                matches.sort(
                    key=lambda m: (not m.in_scope, not m.offers_bounties, m.name)
                )
                best[host] = matches[0]
        return best

    async def _load(self, hosts: set[str]) -> tuple[list, dict[UUID, list]]:
        """Programs with a scope entry these hosts could sit under, and their scopes."""
        values = bindparam("values", scope_values(hosts), type_=ARRAY(Text))
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
                func.lower(BountyScope.target_value).in_(select(func.unnest(values))),
            )
            .distinct()
        )
        programs = list(rows.all())
        if not programs:
            return [], {}
        scope_rows = await self.session.execute(
            select(
                BountyScope.program_id,
                BountyScope.id,
                BountyScope.asset_type,
                BountyScope.asset_identifier,
                BountyScope.scope_state,
                BountyScope.target_value,
                BountyScope.target_type,
                BountyScope.eligible_for_bounty,
                BountyScope.max_severity,
            ).where(BountyScope.program_id.in_([p.id for p in programs]))
        )
        scopes_by_program: dict[UUID, list] = {}
        for row in scope_rows.all():
            scopes_by_program.setdefault(row.program_id, []).append(row)
        return programs, scopes_by_program

    def _match_scopes(self, program, host: str, scopes: list) -> ProgramMatch | None:
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
