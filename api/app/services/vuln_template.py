from __future__ import annotations

import contextlib
from pathlib import Path
from uuid import UUID

from sqlalchemy import cast, delete, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.vulnerabilities import (
    HEADLESS_SETS,
    PROTOCOL_LABELS,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    TEMPLATE_SETS,
    Protocol,
    TemplateOrigin,
)
from shared.logging import get_logger
from shared.models.vuln_template import (
    SelectionBreakdown,
    SelectionPreview,
    TemplateFilter,
    TemplateLibraryStats,
    TemplatePage,
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
from shared.models.vulnerability import Vulnerability
from shared.services.celery_dispatch import dispatch_template_sync
from shared.services.vuln_templates import (
    TemplateError,
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


_TAG_LIMIT = 40


class VulnTemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hits():
        return (
            select(
                Vulnerability.template_id.label("template_id"),
                func.count().label("findings"),
            )
            .group_by(Vulnerability.template_id)
            .subquery()
        )

    @staticmethod
    def _to_read(
        row: VulnTemplate, *, raw: bool = False, findings: int = 0
    ) -> VulnTemplateRead:
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
            findings=findings,
            raw=row.raw if raw else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def stats(self) -> TemplateLibraryStats:
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
        protocol = {
            name: int(count)
            for name, count in (
                await self.session.execute(
                    select(VulnTemplate.protocol, func.count()).group_by(
                        VulnTemplate.protocol
                    )
                )
            ).all()
        }
        tag = func.jsonb_array_elements_text(
            cast(VulnTemplate.tags, JSONB)
        ).column_valued("tag")
        tags = (
            await self.session.execute(
                select(tag, func.count())
                .select_from(VulnTemplate)
                .group_by(tag)
                .order_by(func.count().desc(), tag)
                .limit(_TAG_LIMIT)
            )
        ).all()
        last = await self.session.scalar(select(func.max(VulnTemplate.updated_at)))
        fired = await self.session.scalar(
            select(func.count(func.distinct(Vulnerability.template_id)))
        )
        return TemplateLibraryStats(
            ready=total > 0,
            total=total,
            official=by_origin.get(TemplateOrigin.OFFICIAL.value, 0),
            custom=by_origin.get(TemplateOrigin.CUSTOM.value, 0),
            by_severity=[
                SelectionBreakdown(
                    key=name, label=SEVERITY_LABELS[name], count=severity.get(name, 0)
                )
                for name in SEVERITY_ORDER
                if severity.get(name)
            ],
            by_protocol=[
                SelectionBreakdown(
                    key=name, label=PROTOCOL_LABELS.get(name, name), count=count
                )
                for name, count in sorted(protocol.items(), key=lambda item: -item[1])
            ],
            sets=await self._set_counts(),
            tags=[
                SelectionBreakdown(key=str(name), label=str(name), count=int(count))
                for name, count in tags
            ],
            fired=int(fired or 0),
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
        hits = self._hits()
        findings = func.coalesce(hits.c.findings, 0)
        query = select(VulnTemplate, findings).outerjoin(
            hits, hits.c.template_id == VulnTemplate.template_id
        )
        if f.fired:
            query = query.where(hits.c.findings > 0)
        if f.origins:
            query = query.where(VulnTemplate.origin.in_(f.origins))
        if f.severities:
            query = query.where(VulnTemplate.severity.in_(f.severities))
        if f.protocols:
            query = query.where(VulnTemplate.protocol.in_(f.protocols))
        if f.tags:
            query = query.where(
                func.jsonb_exists_any(
                    cast(VulnTemplate.tags, JSONB),
                    pg_array(sorted({t.lower() for t in f.tags})),
                )
            )
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
        ordering = (
            [findings.desc(), VulnTemplate.name]
            if f.fired
            else [VulnTemplate.origin, VulnTemplate.name]
        )
        rows = await self.session.execute(
            query.order_by(*ordering).limit(f.limit).offset(f.offset)
        )
        return TemplatePage(
            items=[
                self._to_read(row, findings=int(count or 0))
                for row, count in rows.all()
            ],
            total=int(total or 0),
        )

    async def get(self, template_id: UUID) -> VulnTemplateRead | None:
        row = await self.session.get(VulnTemplate, template_id)
        return self._to_read(row, raw=True) if row else None

    async def preview(self, selection: TemplateSelection) -> SelectionPreview:
        total_rows = await self.session.scalar(select(func.count(VulnTemplate.id)))
        if not total_rows:
            return SelectionPreview(
                ready=False,
                warnings=[
                    "The check library is empty. Sync it before running a vulnerability scan."
                ],
            )
        predicate = selection_predicate(selection)
        severity = (
            await self.session.execute(
                select(
                    VulnTemplate.severity, func.count(), func.sum(VulnTemplate.requests)
                )
                .where(predicate)
                .group_by(VulnTemplate.severity)
            )
        ).all()
        protocol = (
            await self.session.execute(
                select(VulnTemplate.protocol, func.count())
                .where(predicate)
                .group_by(VulnTemplate.protocol)
            )
        ).all()
        official = sum(int(count) for _, count, _ in severity)
        requests = sum(int(total or 0) for _, _, total in severity)

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

        by_set = []
        for key in selection.template_sets:
            narrowed = selection.model_copy(update={"template_sets": [key]})
            spec = next((s for s in TEMPLATE_SETS if s.key == key), None)
            count = await self.session.scalar(
                select(func.count()).where(selection_predicate(narrowed))
            )
            by_set.append(
                SelectionBreakdown(
                    key=key,
                    label=spec.label if spec else key,
                    count=int(count or 0),
                )
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
                "Browser checks are selected but the browser is off, so they will not run."
            )
        return SelectionPreview(
            ready=True,
            total=total,
            official=official,
            custom=custom,
            by_severity=[
                SelectionBreakdown(
                    key=name,
                    label=SEVERITY_LABELS.get(name, name),
                    count=int(count),
                )
                for name, count, _ in sorted(
                    severity,
                    key=lambda item: (
                        SEVERITY_ORDER.index(item[0])
                        if item[0] in SEVERITY_ORDER
                        else len(SEVERITY_ORDER)
                    ),
                )
            ],
            by_set=by_set,
            by_protocol=[
                SelectionBreakdown(
                    key=name, label=PROTOCOL_LABELS.get(name, name), count=int(count)
                )
                for name, count in sorted(protocol, key=lambda item: -item[1])
            ],
            estimated_requests=requests,
            warnings=warnings,
        )

    async def upload(
        self, data: VulnTemplateUploadRequest, user_id: UUID
    ) -> VulnTemplateUploadResult:
        result = VulnTemplateUploadResult()
        for item in data.files:
            try:
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
            existing = await self.session.scalar(
                select(VulnTemplate).where(
                    VulnTemplate.origin == TemplateOrigin.CUSTOM.value,
                    VulnTemplate.path == relative,
                )
            )
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
        """Replace an uploaded check in place; the path stays put so selections survive."""
        row = await self.session.get(VulnTemplate, template_id)
        if row is None:
            return None
        if row.origin != TemplateOrigin.CUSTOM.value:
            msg = "Project templates are read-only. Sync replaces them, so an edit would not survive."
            raise TemplateError(msg)
        parsed = parse_template(content)
        destination = _resolve(custom_root(), row.path)
        if destination is None:
            msg = "This check is no longer at a writable path in the library."
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
            message="Downloading and indexing the check library. This takes a few minutes."
            if ok
            else "The scanner queue is unavailable. The sync was not started.",
        )


__all__ = ["Protocol", "VulnTemplateService"]
