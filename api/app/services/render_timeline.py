"""Screenshots over the census runs of a target: one cell per run, flags per host."""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, BIT
from sqlalchemy.orm import aliased
from sqlalchemy.types import Uuid

from app.services.timeline import CLEAN, SINCE, TimelineColumn, TimelineService
from shared.definitions.correlation import SCREENSHOT_DISTANCE
from shared.definitions.timeline import (
    FLAPPING_TRANSITIONS,
    RENDER_STAGE,
    RenderFlag,
    RenderSort,
    RenderState,
)
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.timeline import RenderCell, RenderRow, RenderSearchResult
from shared.utils.imagehash import distance

UNSEEN = RenderState.UNSEEN.value


class Capture(NamedTuple):
    phash: int | None
    path: str | None
    http: bool


class RenderTimelineService(TimelineService):
    result = RenderSearchResult
    carried = ("changes", "last_ord", "first_now")

    def _stages(self) -> set[str]:
        return super()._stages() | {RENDER_STAGE}

    def _required(self) -> frozenset[str]:
        return super()._required() | {RENDER_STAGE}

    def _since(self):
        """When the first screenshot of the host was taken, across every scan."""
        other = aliased(Subdomain)
        return (
            select(func.min(func.coalesce(Scan.started_at, Scan.created_at)))
            .select_from(other)
            .join(Scan, Scan.id == other.scan_id)
            .where(
                other.target_id == Subdomain.target_id,
                other.name == Subdomain.name,
                other.screenshot_phash.isnot(None),
            )
            .correlate(Subdomain)
            .scalar_subquery()
        )

    def _flags(self, w, project_id: UUID):
        """Per host: render changes in the window, first and last change, newest row."""
        shown = or_(
            Subdomain.screenshot_phash.isnot(None), Subdomain.http_status.isnot(None)
        )
        names = (
            select(Subdomain.name)
            .distinct()
            .join(w, w.c.scan_id == Subdomain.scan_id)
            .where(Subdomain.project_id == project_id, w.c.observed.is_(True), shown)
            .cte("render_names")
        )
        rows = (
            select(
                Subdomain.id,
                Subdomain.name,
                w.c.ord,
                Subdomain.screenshot_phash.label("phash"),
                Subdomain.screenshot_path.isnot(None).label("image"),
            )
            .join(w, w.c.scan_id == Subdomain.scan_id)
            .join(names, names.c.name == Subdomain.name)
            .where(Subdomain.project_id == project_id, w.c.observed.is_(True))
            .cte("render_rows")
        )
        by_host = {"partition_by": rows.c.name, "order_by": rows.c.ord}
        captures = (
            select(
                rows.c.name,
                rows.c.ord,
                rows.c.image,
                rows.c.phash,
                func.lag(rows.c.phash).over(**by_host).label("pphash"),
            )
            .where(rows.c.phash.isnot(None))
            .cte("render_captures")
        )
        first = captures.c.pphash.is_(None)
        moved = (
            func.bit_count(cast(captures.c.phash.op("#")(captures.c.pphash), BIT(64)))
            > SCREENSHOT_DISTANCE
        )
        changed = and_(captures.c.pphash.isnot(None), moved)
        newest = select(func.max(w.c.ord)).scalar_subquery()
        per_host = (
            select(
                captures.c.name,
                func.count().filter(changed).label("changes"),
                func.max(captures.c.ord).filter(or_(changed, first)).label("last_ord"),
                func.min(captures.c.ord).label("first_ord"),
                func.bool_or(captures.c.image.is_(False)).label("expired"),
            )
            .group_by(captures.c.name)
            .cte("render_changes")
        )
        ordered = select(
            rows.c.name,
            rows.c.id,
            func.lead(rows.c.ord).over(**by_host).is_(None).label("last"),
        ).cte("render_ordered")
        latest = (
            select(
                ordered.c.name,
                func.array_agg(ordered.c.id, type_=ARRAY(Uuid))
                .filter(ordered.c.last)
                .label("ids"),
            )
            .group_by(ordered.c.name)
            .cte("render_latest")
        )
        return (
            select(
                latest.c.name,
                latest.c.ids[1].label("latest_id"),
                func.coalesce(per_host.c.changes, 0).label("changes"),
                per_host.c.last_ord,
                per_host.c.first_ord,
                (per_host.c.first_ord == newest).label("first_now"),
                func.coalesce(per_host.c.expired, False).label("expired"),
            )
            .select_from(latest)
            .outerjoin(per_host, per_host.c.name == latest.c.name)
            .cte("render_flags")
        )

    def _flag_predicates(self, flags, scan: Scan) -> dict[str, object]:
        uncaptured = and_(
            Subdomain.scan_id == scan.id,
            Subdomain.http_status.isnot(None),
            Subdomain.screenshot_phash.is_(None),
        )
        return {
            RenderFlag.NEW.value: flags.c.first_now.is_(True),
            RenderFlag.CHANGED.value: flags.c.changes > 0,
            RenderFlag.FLAPPING.value: flags.c.changes >= FLAPPING_TRANSITIONS,
            RenderFlag.EXPIRED.value: flags.c.expired.is_(True),
            RenderFlag.NOT_CAPTURED.value: uncaptured,
        }

    def _keyed_sorts(self, matched) -> dict[str, object]:
        return {
            RenderSort.LAST_CHANGE.value: matched.c.last_ord,
            RenderSort.CHANGES.value: matched.c.changes,
            RenderSort.FIRST_CAPTURED.value: matched.c[SINCE],
        }

    async def _cells(
        self, w, columns: list[TimelineColumn], project_id: UUID, names: list[str]
    ) -> dict[str, list[RenderCell]]:
        if not names:
            return {}
        result = await self.session.execute(
            select(
                Subdomain.name,
                w.c.ord,
                Subdomain.screenshot_phash,
                Subdomain.screenshot_path,
                Subdomain.http_status,
            )
            .join(w, w.c.scan_id == Subdomain.scan_id)
            .where(
                Subdomain.project_id == project_id,
                Subdomain.name.in_(names),
                w.c.observed.is_(True),
            )
        )
        seen: dict[str, dict[int, Capture]] = {}
        for name, ord_, phash, path, status in result.all():
            seen.setdefault(name, {})[ord_] = Capture(phash, path, status is not None)
        return {name: self._strip(columns, seen.get(name, {})) for name in names}

    @staticmethod
    def _strip(
        columns: list[TimelineColumn], rows: dict[int, Capture]
    ) -> list[RenderCell]:
        first = min(rows) if rows else None
        cells: list[RenderCell] = []
        previous: int | None = None
        for col in columns:
            unseen = first is None or col.ord < first
            if not col.observed:
                state = UNSEEN if unseen else RenderState.UNOBSERVED.value
                cells.append(RenderCell(state=state))
                continue
            found = all(
                state == CLEAN
                for stage, state in col.statuses.items()
                if stage != RENDER_STAGE
            )
            captured = col.statuses.get(RENDER_STAGE) == CLEAN
            row = rows.get(col.ord)
            if row is None:
                if unseen:
                    state = UNSEEN
                elif found:
                    state = RenderState.GONE.value
                else:
                    state = RenderState.UNCONFIRMED.value
                cells.append(RenderCell(state=state))
                continue
            if row.phash is None:
                if not row.http:
                    state = RenderState.NO_HTTP.value
                elif captured:
                    state = RenderState.NOT_CAPTURED.value
                else:
                    state = RenderState.UNCONFIRMED.value
                cells.append(RenderCell(state=state))
                continue
            if previous is None:
                state, moved = RenderState.FIRST.value, None
            else:
                moved = distance(previous, row.phash)
                state = (
                    RenderState.CHANGED.value
                    if moved > SCREENSHOT_DISTANCE
                    else RenderState.SAME.value
                )
            cells.append(RenderCell(state=state, path=row.path, distance=moved))
            previous = row.phash
        return cells

    def _row(self, host, m, cells, columns, flags: list[str]):
        return RenderRow(
            host=host,
            cells=cells,
            flags=flags,
            changes=m["changes"],
            first_capture_at=m[SINCE],
            last_change_scan_id=self._at(columns, m["last_ord"]),
        )


__all__ = ["RenderTimelineService"]
