from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.new_checks import TEMPLATES_MARK_KEY
from shared.definitions.vulnerabilities import (
    HEADLESS_SETS,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    TEMPLATE_SETS,
    TemplateOrigin,
)
from shared.logging import get_logger
from shared.models.vuln_template import (
    SelectionBreakdown,
    SelectionPreview,
    TemplateFilter,
    TemplateLibraryStats,
    TemplatePage,
    TemplateSeen,
    TemplateSelection,
    TemplateSetSpec,
    TemplateSource,
    TemplateSyncResult,
    VulnTemplate,
    VulnTemplateRead,
    VulnTemplateRejection,
    VulnTemplateUpdate,
    VulnTemplateUploadRequest,
    VulnTemplateUploadResult,
)
from shared.models.watch import UserMark
from shared.services.celery_dispatch import dispatch_template_sync
from shared.services.vuln_templates import (
    TemplateError,
    custom_path,
    custom_root,
    custom_row,
    official_root,
    parse_template,
    selection_predicate,
    sets_for,
    store_custom,
)
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


def _remove(path: Path | None) -> None:
    if path is None:
        return
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def _resolve(root: Path, relative: str) -> Path | None:
    """A library path that stays inside its root, or nothing."""
    try:
        base = root.resolve()
        candidate = (base / relative).resolve()
    except OSError:
        return None
    return candidate if candidate.is_relative_to(base) else None


def _read(root: Path, relative: str) -> str:
    path = _resolve(root, relative)
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


class VulnTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_read(row: VulnTemplate, *, raw: bool = False) -> VulnTemplateRead:
        return VulnTemplateRead(
            id=row.id,
            origin=row.origin,
            template_id=row.template_id,
            path=row.path,
            name=row.name,
            severity=row.severity,
            protocol=row.protocol,
            directory=row.directory,
            description=row.description,
            remediation=row.remediation,
            tags=list(row.tags or []),
            authors=list(row.authors or []),
            references=list(row.references or []),
            cve_ids=list(row.cve_ids or []),
            cwe_ids=list(row.cwe_ids or []),
            cvss_score=row.cvss_score,
            requests=row.requests,
            enabled=row.enabled,
            sets=sets_for(row.tags or [], row.path),
            raw=row.raw if raw else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def seen_at(self, user_id: UUID) -> datetime | None:
        return await self.session.scalar(
            select(UserMark.marked_at).where(
                UserMark.user_id == user_id, UserMark.key == TEMPLATES_MARK_KEY
            )
        )

    async def mark_seen(self, user_id: UUID) -> TemplateSeen:
        before = await self.seen_at(user_id)
        now = utc_now()
        stmt = pg_insert(UserMark).values(
            user_id=user_id, key=TEMPLATES_MARK_KEY, marked_at=now
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["user_id", "key"], set_={"marked_at": now}
            )
        )
        await self.session.commit()
        return TemplateSeen(seen_at=before, marked_at=now)

    async def stats(self, user_id: UUID) -> TemplateLibraryStats:
        seen = await self.seen_at(user_id)
        new = 0
        if seen is not None:
            new = int(
                await self.session.scalar(
                    select(func.count(VulnTemplate.id)).where(
                        VulnTemplate.origin == TemplateOrigin.OFFICIAL.value,
                        VulnTemplate.enabled.is_(True),
                        VulnTemplate.created_at > seen,
                    )
                )
                or 0
            )
        total = int(await self.session.scalar(select(func.count(VulnTemplate.id))) or 0)
        by_origin = {
            origin: int(count)
            for origin, count in (
                await self.session.execute(
                    select(VulnTemplate.origin, func.count()).group_by(
                        VulnTemplate.origin
                    )
                )
            ).all()
        }
        severity = {
            name: int(count)
            for name, count in (
                await self.session.execute(
                    select(VulnTemplate.severity, func.count()).group_by(
                        VulnTemplate.severity
                    )
                )
            ).all()
        }
        last = await self.session.scalar(select(func.max(VulnTemplate.updated_at)))
        callback = await self.session.scalar(
            select(func.count(VulnTemplate.id)).where(VulnTemplate.needs_oast.is_(True))
        )
        return TemplateLibraryStats(
            ready=total > 0,
            total=total,
            callback=int(callback or 0),
            official=by_origin.get(TemplateOrigin.OFFICIAL.value, 0),
            custom=by_origin.get(TemplateOrigin.CUSTOM.value, 0),
            by_severity=[
                SelectionBreakdown(
                    key=name, label=SEVERITY_LABELS[name], count=severity.get(name, 0)
                )
                for name in SEVERITY_ORDER
                if severity.get(name)
            ],
            sets=await self._set_counts(),
            new=new,
            seen_at=seen,
            last_synced_at=last,
        )

    async def _set_counts(self) -> list[TemplateSetSpec]:
        out = []
        for spec in TEMPLATE_SETS:
            selection = TemplateSelection(
                severities=list(SEVERITY_ORDER),
                template_sets=[spec.key],
                headless=spec.headless,
            )
            count = await self.session.scalar(
                select(func.count()).where(selection_predicate(selection))
            )
            out.append(
                TemplateSetSpec(
                    key=spec.key,
                    label=spec.label,
                    description=spec.description,
                    headless=spec.headless,
                    count=int(count or 0),
                )
            )
        return out

    async def list(self, f: TemplateFilter) -> TemplatePage:
        query = select(VulnTemplate)
        if f.callback:
            query = query.where(VulnTemplate.needs_oast.is_(True))
        if f.new_since is not None:
            query = query.where(
                VulnTemplate.origin == TemplateOrigin.OFFICIAL.value,
                VulnTemplate.enabled.is_(True),
                VulnTemplate.created_at > f.new_since,
            )
        if f.origins:
            query = query.where(VulnTemplate.origin.in_(f.origins))
        if f.severities:
            query = query.where(VulnTemplate.severity.in_(f.severities))
        if f.sets:
            selection = TemplateSelection(
                severities=list(SEVERITY_ORDER),
                template_sets=list(f.sets),
                headless=True,
            )
            query = query.where(selection_predicate(selection, official_only=False))
        if f.q:
            needle = f"%{f.q.strip()}%"
            query = query.where(
                or_(
                    VulnTemplate.name.ilike(needle),
                    VulnTemplate.template_id.ilike(needle),
                )
            )
        total = await self.session.scalar(
            select(func.count()).select_from(query.subquery())
        )
        if f.new_since is not None:
            ordering = [VulnTemplate.created_at.desc(), VulnTemplate.name]
        else:
            ordering = [VulnTemplate.origin, VulnTemplate.name]
        rows = await self.session.scalars(
            query.order_by(*ordering).limit(f.limit).offset(f.offset)
        )
        return TemplatePage(
            items=[self._to_read(row) for row in rows.all()],
            total=int(total or 0),
        )

    async def get(self, template_id: UUID) -> VulnTemplateRead | None:
        row = await self.session.get(VulnTemplate, template_id)
        return self._to_read(row, raw=True) if row else None

    async def preview(self, selection: TemplateSelection) -> SelectionPreview:
        total_rows = await self.session.scalar(select(func.count(VulnTemplate.id)))
        if not total_rows:
            return SelectionPreview(
                warnings=[
                    "The check library is empty. Sync it before running a vulnerability scan."
                ],
            )
        severity = (
            await self.session.execute(
                select(VulnTemplate.severity, func.count())
                .where(selection_predicate(selection))
                .group_by(VulnTemplate.severity)
            )
        ).all()
        official = sum(int(count) for _, count in severity)

        custom = 0
        if selection.custom_templates:
            custom = int(
                await self.session.scalar(
                    select(func.count()).where(
                        VulnTemplate.id.in_(list(selection.custom_templates)),
                        VulnTemplate.enabled.is_(True),
                    )
                )
                or 0
            )

        warnings = []
        total = official + custom
        if total == 0:
            warnings.append(
                "Nothing matches this plan. Widen the severities or add a check set."
            )
        headless_only = [k for k in selection.template_sets if k in HEADLESS_SETS]
        if headless_only and not selection.headless:
            warnings.append(
                "Browser checks are selected and the browser is off. They will not run."
            )
        return SelectionPreview(
            total=total,
            by_severity=[
                SelectionBreakdown(
                    key=name,
                    label=SEVERITY_LABELS.get(name, name),
                    count=int(count),
                )
                for name, count in sorted(
                    severity,
                    key=lambda item: (
                        SEVERITY_ORDER.index(item[0])
                        if item[0] in SEVERITY_ORDER
                        else len(SEVERITY_ORDER)
                    ),
                )
            ],
            warnings=warnings,
        )

    async def upload(
        self, data: VulnTemplateUploadRequest, user_id: UUID
    ) -> VulnTemplateUploadResult:
        result = VulnTemplateUploadResult()
        for item in data.files:
            try:
                if not data.replace:
                    taken = custom_path(parse_template(item.content), item.filename)
                    if await self._custom_at(taken) is not None:
                        result.rejected.append(
                            VulnTemplateRejection(
                                filename=item.filename,
                                reason="A custom check with this id exists. Change the id.",
                            )
                        )
                        continue
                parsed, relative = store_custom(item.content, item.filename)
            except TemplateError as exc:
                result.rejected.append(
                    VulnTemplateRejection(filename=item.filename, reason=str(exc))
                )
                continue
            except OSError as exc:
                logger.warning("template write failed", error=str(exc))
                result.rejected.append(
                    VulnTemplateRejection(
                        filename=item.filename,
                        reason="Could not be written to the library.",
                    )
                )
                continue
            existing = await self._custom_at(relative)
            values = custom_row(parsed, relative, item.content, user_id)
            if existing is not None:
                for key, value in values.items():
                    if key not in ("created_at", "uploaded_by"):
                        setattr(existing, key, value)
                existing.updated_at = utc_now()
                row = existing
                result.replaced += 1
            else:
                row = VulnTemplate(**values)
                self.session.add(row)
            await self.session.flush()
            result.accepted.append(self._to_read(row))
        await self.session.commit()
        return result

    async def _custom_at(self, relative: str) -> VulnTemplate | None:
        return await self.session.scalar(
            select(VulnTemplate).where(
                VulnTemplate.origin == TemplateOrigin.CUSTOM.value,
                VulnTemplate.path == relative,
            )
        )

    async def source(self, template_id: UUID) -> TemplateSource | None:
        row = await self.session.get(VulnTemplate, template_id)
        if row is None:
            return None
        custom = row.origin == TemplateOrigin.CUSTOM.value
        content = (
            row.raw
            if row.raw is not None
            else _read(custom_root() if custom else official_root(), row.path)
        )
        return TemplateSource(
            id=row.id,
            template_id=row.template_id,
            name=row.name,
            origin=row.origin,
            path=row.path,
            editable=custom,
            content=content,
        )

    async def rewrite(self, template_id: UUID, content: str) -> VulnTemplateRead | None:
        """Replace an uploaded check in place."""
        row = await self.session.get(VulnTemplate, template_id)
        if row is None:
            return None
        if row.origin != TemplateOrigin.CUSTOM.value:
            msg = "Default checks are read-only. Copy the source into a custom check to edit it."
            raise TemplateError(msg)
        parsed = parse_template(content)
        destination = _resolve(custom_root(), row.path)
        if destination is None:
            msg = "The check is not at a writable path in the library."
            raise TemplateError(msg)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        values = custom_row(parsed, row.path, content, row.uploaded_by)
        for key, value in values.items():
            if key not in ("created_at", "uploaded_by", "enabled", "path"):
                setattr(row, key, value)
        row.updated_at = utc_now()
        await self.session.commit()
        return self._to_read(row)

    async def update(
        self, template_id: UUID, data: VulnTemplateUpdate
    ) -> VulnTemplateRead | None:
        row = await self.session.get(VulnTemplate, template_id)
        if row is None:
            return None
        if data.enabled is not None:
            row.enabled = data.enabled
        row.updated_at = utc_now()
        await self.session.commit()
        return self._to_read(row)

    async def delete(self, template_id: UUID) -> bool:
        row = await self.session.get(VulnTemplate, template_id)
        if row is None or row.origin != TemplateOrigin.CUSTOM.value:
            return False
        _remove(_resolve(custom_root(), row.path))
        await self.session.execute(
            delete(VulnTemplate).where(VulnTemplate.id == template_id)
        )
        await self.session.commit()
        return True

    @staticmethod
    def sync() -> TemplateSyncResult:
        ok = dispatch_template_sync()
        return TemplateSyncResult(
            started=ok,
            message="Downloading and indexing the check library."
            if ok
            else "The task queue did not accept the sync. Check the worker.",
        )


__all__ = ["VulnTemplateService"]
