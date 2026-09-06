"""Focused scans: re-run stages against assets chosen in an earlier run."""

from __future__ import annotations

import ipaddress
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scan import ScanService
from shared.definitions.rescan import (
    MAX_SEED_ASSETS,
    RESCANNABLE_STAGES,
    SEED_KIND_NOUN,
    SeedKind,
    seed_kind_for,
    stages_for,
)
from shared.definitions.surface import SURFACE_LABELS, SURFACE_NOUN, SURFACE_ORDER
from shared.enums.scan import SCAN_LIVE_STATUSES, Phase, ScanScope, StageRole
from shared.models.recheck import AssetRecheck, RecheckRead
from shared.models.scan import (
    RescanCreate,
    RescanDimension,
    RescanSchema,
    Scan,
    ScanCreate,
    ScanRead,
    SeedAsset,
)
from shared.models.vuln_template import VulnTemplate
from stages.registry import stage_by_name


def _seed_kind(value: str, default: str) -> str:
    """An address is an address whichever dimension it was picked from."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return default
    return SeedKind.ADDRESS.value


_VULN_STAGE = "vulnerability_scan"
_DISCOVERY = Phase.DISCOVERY.value
_MAX_RUNS = 50


def rescan_schema() -> RescanSchema:
    return RescanSchema(
        dimensions=[
            RescanDimension(
                dimension=dimension,
                label=SURFACE_LABELS[dimension],
                noun=SURFACE_NOUN[dimension][0],
                noun_plural=SURFACE_NOUN[dimension][1],
                seed_kind=seed_kind_for(dimension),
                default_stages=list(stages_for(dimension)),
            )
            for dimension in SURFACE_ORDER
        ],
        rescannable_stages=sorted(RESCANNABLE_STAGES),
        max_assets=MAX_SEED_ASSETS,
    )


class RescanService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.scans = ScanService(session)

    async def create(
        self, data: RescanCreate, project_id: UUID, created_by: UUID
    ) -> ScanRead:
        parent = await self._parent(data.parent_scan_id, project_id)
        picked = self._stages(data.stages, data.dimension)
        overrides = await self._overrides(picked, data)
        kind = seed_kind_for(data.dimension)
        # one level of nesting: a rescan of a rescan belongs to the census that seeded both
        anchor = (
            parent.parent_scan_id
            if parent.scope == ScanScope.FOCUSED.value and parent.parent_scan_id
            else parent.id
        )
        return await self.scans.create(
            ScanCreate(
                engine_id=None,
                context_id=data.context_id or parent.context_id,
                target_id=parent.target_id,
                overrides=overrides,
                intensity=data.intensity
                or (parent.execution_config or {}).get("intensity"),
                seed_assets=[
                    SeedAsset(kind=_seed_kind(value, kind), value=value)
                    for value in data.assets
                ],
                parent_scan_id=anchor,
                dimension=data.dimension,
            ),
            project_id,
            created_by,
        )

    async def rechecks(
        self, parent_scan_id: UUID, project_id: UUID
    ) -> list[RecheckRead]:
        """Every rescan of this run, newest first, one entry per asset it touched."""
        runs = (
            (
                await self.session.execute(
                    select(Scan)
                    .where(
                        Scan.parent_scan_id == parent_scan_id,
                        Scan.project_id == project_id,
                    )
                    .order_by(Scan.created_at.desc())
                    .limit(_MAX_RUNS)
                )
            )
            .scalars()
            .all()
        )
        if not runs:
            return []
        rows = (
            (
                await self.session.execute(
                    select(AssetRecheck).where(
                        AssetRecheck.scan_id.in_([r.id for r in runs])
                    )
                )
            )
            .scalars()
            .all()
        )
        diffed = {(row.scan_id, row.asset_key): row for row in rows}
        known = stage_by_name()

        out: list[RecheckRead] = []
        for run in runs:
            config = run.execution_config or {}
            titles = [
                known[name].title
                for name, values in (config.get("stages") or {}).items()
                if name in known
                and name in RESCANNABLE_STAGES
                and (values or {}).get("enabled")
            ]
            duration = (
                (run.completed_at - run.started_at).total_seconds()
                if run.completed_at and run.started_at
                else None
            )
            for seed in config.get("seed_assets") or []:
                key = seed.get("value") or ""
                row = diffed.get((run.id, key))
                out.append(
                    RecheckRead(
                        id=row.id if row else run.id,
                        scan_id=run.id,
                        parent_scan_id=parent_scan_id,
                        dimension=config.get("_dimension") or "",
                        asset_kind=seed.get("kind") or "",
                        asset_key=key,
                        changed=bool(row.changed) if row else False,
                        changes=row.changes if row else [],
                        created_at=run.created_at,
                        status=run.status,
                        stage_titles=sorted(titles),
                        duration_seconds=duration,
                    )
                )
        return out

    async def _parent(self, scan_id: UUID, project_id: UUID) -> Scan:
        scan = await self.session.get(Scan, scan_id)
        if scan is None or scan.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
            )
        if scan.status in SCAN_LIVE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This run has not finished. Wait for it to complete before rescanning its assets.",
            )
        return scan

    @staticmethod
    def _stages(requested: list[str], dimension: str) -> list[str]:
        picked = list(dict.fromkeys(requested)) or list(stages_for(dimension))
        unknown = [name for name in picked if name not in RESCANNABLE_STAGES]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"'{unknown[0]}' cannot run on chosen assets. "
                    f"Rescannable stages: {', '.join(sorted(RESCANNABLE_STAGES))}."
                ),
            )
        return picked

    async def _overrides(self, picked: list[str], data: RescanCreate) -> dict:
        known = stage_by_name()
        # the seed is the only source of assets: nothing may enumerate the target again
        overrides = {
            name: {"enabled": False}
            for name, spec in known.items()
            if not spec.catalog_hidden
            and (
                spec.role == StageRole.CAPABILITY.value
                or (not spec.consumes and (spec.produces or spec.phase == _DISCOVERY))
            )
        }
        for name in picked:
            overrides[name] = {**(overrides.get(name) or {}), "enabled": True}
        for name, values in (data.overrides or {}).items():
            if name in known and not known[name].catalog_hidden:
                overrides[name] = {**(overrides.get(name) or {}), **(values or {})}
        if data.template_ids and _VULN_STAGE in picked:
            overrides[_VULN_STAGE] = {
                **overrides[_VULN_STAGE],
                **await self._only_templates(data.template_ids),
            }
        return overrides

    async def _only_templates(self, template_ids: list[str]) -> dict:
        """Re-verify exactly the checks that produced the selected findings."""
        rows = (
            (
                await self.session.execute(
                    select(VulnTemplate.id).where(
                        VulnTemplate.template_id.in_(template_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            return {}
        return {
            "template_sets": [],
            "include_tags": [],
            "custom_templates": [str(row) for row in rows],
        }

    @staticmethod
    def seed_noun(kind: str, count: int) -> str:
        singular, plural = SEED_KIND_NOUN.get(kind, ("asset", "assets"))
        return singular if count == 1 else plural
