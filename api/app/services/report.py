"""Report CRUD, the builder catalog and the hand-off to the worker."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from reports.fonts import vendored
from reports.presets import PRESETS, Preset
from reports.registry import catalog as section_catalog
from reports.registry import section as lookup_section
from reports.theme import ThemeError, builtin_source, builtin_themes, theme_summary
from reports.theme import parse as parse_theme
from shared.definitions.ai import (
    REPORT_TASKS,
    TASK_OUTPUT_TOKENS,
    price,
)
from shared.definitions.compliance import FRAMEWORKS
from shared.definitions.report_fonts import (
    FONT_ROLE_HELP,
    FONT_ROLE_LABELS,
    MAX_FACES,
    MAX_FAMILIES,
    FontOrigin,
    FontRole,
)
from shared.definitions.report_theme import (
    COVER_ART_LABELS,
    COVER_LAYOUT_LABELS,
    FINDING_STYLE_LABELS,
    HEADING_STYLE_LABELS,
    MAX_THEME_BYTES,
    TABLE_STYLE_LABELS,
    ThemeOrigin,
    ThemeTokens,
)
from shared.definitions.reports import (
    AUDIENCE_HELP,
    AUDIENCE_LABELS,
    DENSITY_LABELS,
    DEPTH_LABELS,
    FORMAT_LABELS,
    MAX_SECTIONS,
    PAGE_SIZE_LABELS,
    REPORT_ROOT,
    SCOPE_HELP,
    SCOPE_LABELS,
    SECTION_GROUP_LABELS,
    SECTION_GROUP_ORDER,
    SLOT_TOKENS,
    NarrativeOptions,
    ReportBranding,
    ReportFormat,
    ReportSpec,
    ReportStatus,
    ReportStyle,
    SectionEntry,
    coerce_scope,
)
from shared.definitions.vulnerabilities import SEVERITY_ORDER, Severity
from shared.models.instance_settings import InstanceSettings
from shared.models.report import (
    FontFace,
    FrameworkSummary,
    Report,
    ReportCatalog,
    ReportCreate,
    ReportDefaults,
    ReportEstimate,
    ReportFile,
    ReportFont,
    ReportFontRead,
    ReportFontUpload,
    ReportRead,
    ReportTemplate,
    ReportTemplateCreate,
    ReportTemplateRead,
    ReportTemplateUpdate,
    ReportTheme,
    ReportThemeRead,
    ThemeSummary,
)
from shared.models.scan import Scan
from shared.models.target import Target
from shared.services.ai.config import load_config_async
from shared.services.celery_dispatch import dispatch_report
from shared.services.report_fonts import (
    FontError,
    clean_name,
    decode,
    delete_family,
    slugify,
    store_face,
)
from shared.utils.datetime import utc_now
from shared.utils.slug import generate_slug

_MAX_LIST = 200


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- catalog ----------

    async def catalog(self) -> ReportCatalog:
        cfg = await load_config_async(self.session)
        themes = await self._theme_summaries()
        return ReportCatalog(
            sections=section_catalog(),
            groups=[
                {"key": key, "label": SECTION_GROUP_LABELS[key]}
                for key in SECTION_GROUP_ORDER
            ],
            themes=themes,
            presets=[_preset_payload(p) for p in PRESETS],
            fonts=await self.fonts(),
            font_roles=[
                {"key": k, "label": v, "help": FONT_ROLE_HELP.get(k, "")}
                for k, v in FONT_ROLE_LABELS.items()
            ],
            page_sizes=[{"key": k, "label": v} for k, v in PAGE_SIZE_LABELS.items()],
            formats=[{"key": k, "label": v} for k, v in FORMAT_LABELS.items()],
            scopes=[
                {"key": k, "label": v, "help": SCOPE_HELP.get(k, "")}
                for k, v in SCOPE_LABELS.items()
            ],
            slot_tokens=[{"token": t.token, "label": t.label} for t in SLOT_TOKENS],
            frameworks=[
                FrameworkSummary(
                    key=f.key,
                    name=f.name,
                    version=f.version,
                    description=f.description,
                    url=f.url,
                    scope_note=f.scope_note,
                    controls=[
                        {"id": c.id, "title": c.title, "note": c.note}
                        for c in f.controls
                    ],
                )
                for f in FRAMEWORKS
            ],
            cover_layouts=[
                {"key": k, "label": v} for k, v in COVER_LAYOUT_LABELS.items()
            ],
            cover_art=[{"key": k, "label": v} for k, v in COVER_ART_LABELS.items()],
            table_styles=[
                {"key": k, "label": v} for k, v in TABLE_STYLE_LABELS.items()
            ],
            finding_styles=[
                {"key": k, "label": v} for k, v in FINDING_STYLE_LABELS.items()
            ],
            heading_styles=[
                {"key": k, "label": v} for k, v in HEADING_STYLE_LABELS.items()
            ],
            audiences=[
                {"key": k, "label": v, "help": AUDIENCE_HELP.get(k, "")}
                for k, v in AUDIENCE_LABELS.items()
            ],
            depths=[{"key": k, "label": v} for k, v in DEPTH_LABELS.items()],
            densities=[{"key": k, "label": v} for k, v in DENSITY_LABELS.items()],
            ai_available=bool(cfg and cfg.allows("report_narrative")),
            ai_model=cfg.model if cfg else "",
        )

    async def _theme_summaries(self) -> list[ThemeSummary]:
        await self.sync_themes()
        rows = (
            (
                await self.session.execute(
                    select(ReportTheme).order_by(ReportTheme.origin, ReportTheme.name)
                )
            )
            .scalars()
            .all()
        )
        out: list[ThemeSummary] = []
        for row in rows:
            try:
                tokens = ThemeTokens.model_validate(row.tokens)
            except ValueError:
                continue
            out.append(ThemeSummary(**theme_summary(tokens, row.origin)))
        return out

    async def sync_themes(self) -> None:
        """Shipped themes are indexed on read so the picker never starts empty."""
        changed = False
        for slug, tokens in builtin_themes().items():
            source = builtin_source(slug)
            row = (
                (
                    await self.session.execute(
                        select(ReportTheme).where(ReportTheme.slug == slug)
                    )
                )
                .scalars()
                .first()
            )
            values = {
                "name": tokens.name,
                "description": tokens.description,
                "author": tokens.author,
                "version": tokens.version,
                "origin": ThemeOrigin.BUILTIN.value,
                "tokens": tokens.model_dump(),
                "source": source,
                "updated_at": utc_now(),
            }
            if row is None:
                self.session.add(ReportTheme(slug=slug, **values))
                changed = True
            elif row.source != source:
                for key, value in values.items():
                    setattr(row, key, value)
                self.session.add(row)
                changed = True
        if changed:
            await self.session.commit()

    # ---------- themes ----------

    async def themes(self) -> list[ReportThemeRead]:
        await self.sync_themes()
        rows = (
            (
                await self.session.execute(
                    select(ReportTheme).order_by(ReportTheme.origin, ReportTheme.name)
                )
            )
            .scalars()
            .all()
        )
        return [
            ReportThemeRead.model_validate(row, from_attributes=True) for row in rows
        ]

    async def theme_source(self, slug: str) -> str:
        row = (
            (
                await self.session.execute(
                    select(ReportTheme).where(ReportTheme.slug == slug)
                )
            )
            .scalars()
            .first()
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Theme not found")
        return row.source or builtin_source(slug)

    async def upload_theme(
        self, content: str, user_id: UUID, *, slug: str = ""
    ) -> ReportThemeRead:
        if len(content.encode("utf-8", errors="ignore")) > MAX_THEME_BYTES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "That theme file is too large."
            )
        try:
            tokens = parse_theme(content, slug=slug)
        except ThemeError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

        existing = (
            (
                await self.session.execute(
                    select(ReportTheme).where(ReportTheme.slug == tokens.key)
                )
            )
            .scalars()
            .first()
        )
        if existing is not None and existing.origin == ThemeOrigin.BUILTIN.value:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"'{tokens.key}' is a shipped theme. Choose a different key.",
            )
        values = {
            "name": tokens.name,
            "description": tokens.description,
            "author": tokens.author,
            "version": tokens.version,
            "origin": ThemeOrigin.CUSTOM.value,
            "tokens": tokens.model_dump(),
            "source": content,
            "uploaded_by": user_id,
            "updated_at": utc_now(),
        }
        if existing is None:
            row = ReportTheme(slug=tokens.key, **values)
            self.session.add(row)
        else:
            row = existing
            for key, value in values.items():
                setattr(row, key, value)
            self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return ReportThemeRead.model_validate(row, from_attributes=True)

    async def delete_theme(self, slug: str) -> None:
        row = (
            (
                await self.session.execute(
                    select(ReportTheme).where(ReportTheme.slug == slug)
                )
            )
            .scalars()
            .first()
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Theme not found")
        if row.origin == ThemeOrigin.BUILTIN.value:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "A shipped theme cannot be deleted."
            )
        await self.session.delete(row)
        await self.session.commit()

    # ---------- fonts ----------

    async def fonts(self) -> list[ReportFontRead]:
        rows = (
            (await self.session.execute(select(ReportFont).order_by(ReportFont.name)))
            .scalars()
            .all()
        )
        custom = [
            ReportFontRead(
                id=row.id,
                slug=row.slug,
                name=row.name,
                role=row.role,
                origin=row.origin,
                note=row.note,
                faces=[FontFace.model_validate(f) for f in (row.faces or [])],
                weights=sorted({int(f.get("weight", 400)) for f in (row.faces or [])}),
                bytes=row.bytes,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return [*vendored(), *custom]

    async def upload_font(
        self, data: ReportFontUpload, user_id: UUID
    ) -> ReportFontRead:
        if data.role not in tuple(r.value for r in FontRole):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Choose a sans, serif or monospaced role."
            )
        if len(data.faces) > MAX_FACES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"A family may hold at most {MAX_FACES} faces.",
            )
        count = int(await self.session.scalar(select(func.count(ReportFont.id))) or 0)

        try:
            name = clean_name(data.name)
            slug = slugify(name)
        except FontError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

        existing = (
            (
                await self.session.execute(
                    select(ReportFont).where(ReportFont.slug == slug)
                )
            )
            .scalars()
            .first()
        )
        if existing is None and count >= MAX_FAMILIES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"This instance already holds {MAX_FAMILIES} typefaces. Delete one first.",
            )
        if slug in {f.slug for f in vendored()}:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"'{slug}' is a shipped typeface. Choose a different name.",
            )

        faces: list[dict] = []
        try:
            for face in data.faces:
                faces.append(
                    store_face(
                        slug,
                        decode(face.content),
                        weight=face.weight,
                        italic=face.italic,
                    )
                )
        except FontError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

        values = {
            "name": name,
            "role": data.role,
            "origin": FontOrigin.CUSTOM.value,
            "note": data.note.strip(),
            "faces": faces,
            "bytes": sum(f["bytes"] for f in faces),
            "uploaded_by": user_id,
            "updated_at": utc_now(),
        }
        if existing is None:
            row = ReportFont(slug=slug, **values)
            self.session.add(row)
        else:
            row = existing
            for key, value in values.items():
                setattr(row, key, value)
            self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return ReportFontRead(
            id=row.id,
            slug=row.slug,
            name=row.name,
            role=row.role,
            origin=row.origin,
            note=row.note,
            faces=[FontFace.model_validate(f) for f in row.faces],
            weights=sorted({int(f["weight"]) for f in row.faces}),
            bytes=row.bytes,
            created_at=row.created_at,
        )

    async def delete_font(self, slug: str) -> None:
        row = (
            (
                await self.session.execute(
                    select(ReportFont).where(ReportFont.slug == slug)
                )
            )
            .scalars()
            .first()
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Typeface not found")
        try:
            delete_family(row.slug, row.origin)
        except FontError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        await self.session.delete(row)
        await self.session.commit()

    # ---------- instance defaults ----------

    async def _settings(self) -> InstanceSettings:
        row = (
            (await self.session.execute(select(InstanceSettings).limit(1)))
            .scalars()
            .first()
        )
        if row is None:
            row = InstanceSettings()
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
        return row

    async def defaults(self) -> ReportDefaults:
        row = await self._settings()
        return ReportDefaults.model_validate(row.report_defaults or {})

    async def set_defaults(self, data: ReportDefaults) -> ReportDefaults:
        row = await self._settings()
        row.report_defaults = data.model_dump()
        row.updated_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        return data

    # ---------- templates ----------

    async def seed_templates(self, project_id: UUID) -> None:
        count = await self.session.scalar(
            select(func.count(ReportTemplate.id)).where(
                ReportTemplate.project_id == project_id,
                ReportTemplate.is_builtin.is_(True),
            )
        )
        if count:
            return
        for preset in PRESETS:
            style = ReportStyle(theme=preset.theme, density=preset.density)
            narrative = NarrativeOptions(audience=preset.audience, depth=preset.depth)
            self.session.add(
                ReportTemplate(
                    project_id=project_id,
                    slug=preset.slug,
                    name=preset.name,
                    description=preset.description,
                    title=preset.title,
                    subtitle=preset.subtitle,
                    preset=preset.slug,
                    tags=list(preset.tags),
                    scope=preset.scope,
                    sections=[e.model_dump() for e in preset.entries()],
                    theme=preset.theme,
                    style=style.model_dump(),
                    branding=ReportBranding().model_dump(),
                    narrative=narrative.model_dump(),
                    formats=list(preset.formats),
                    is_builtin=True,
                    is_default=preset.default,
                )
            )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()

    async def templates(self, project_id: UUID) -> list[ReportTemplateRead]:
        await self.seed_templates(project_id)
        rows = (
            (
                await self.session.execute(
                    select(ReportTemplate)
                    .where(ReportTemplate.project_id == project_id)
                    .order_by(ReportTemplate.is_builtin.desc(), ReportTemplate.name)
                )
            )
            .scalars()
            .all()
        )
        return [_template_read(row) for row in rows]

    async def template(self, template_id: UUID, project_id: UUID) -> ReportTemplate:
        row = await self.session.get(ReportTemplate, template_id)
        if row is None or row.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Report template not found")
        return row

    async def create_template(
        self, data: ReportTemplateCreate, project_id: UUID, user_id: UUID
    ) -> ReportTemplateRead:
        sections = data.sections
        if data.clone_of is not None:
            source = await self.template(data.clone_of, project_id)
            sections = sections or [
                SectionEntry.model_validate(s) for s in source.sections
            ]
            base_style = ReportStyle.model_validate(source.style or {})
            base_branding = ReportBranding.model_validate(source.branding or {})
            base_narrative = NarrativeOptions.model_validate(source.narrative or {})
        else:
            base_style, base_branding, base_narrative = (
                data.style,
                data.branding,
                data.narrative,
            )
        _validate_sections(sections)
        row = ReportTemplate(
            project_id=project_id,
            slug=await self._unique_slug(project_id, data.name),
            name=data.name,
            description=data.description,
            title=data.title,
            subtitle=data.subtitle,
            scope=coerce_scope(data.scope),
            sections=[s.model_dump() for s in sections],
            theme=data.theme or base_style.theme,
            style=base_style.model_dump(),
            branding=base_branding.model_dump(),
            narrative=base_narrative.model_dump(),
            formats=data.formats or [ReportFormat.PDF.value],
            created_by=user_id,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return _template_read(row)

    async def update_template(
        self, template_id: UUID, project_id: UUID, data: ReportTemplateUpdate
    ) -> ReportTemplateRead:
        row = await self.template(template_id, project_id)
        if row.is_builtin:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "A shipped template cannot be edited. Duplicate it and edit the copy.",
            )
        payload = data.model_dump(exclude_unset=True)
        if data.sections is not None:
            _validate_sections(data.sections)
            row.sections = [s.model_dump() for s in data.sections]
            payload.pop("sections", None)
        for key in ("style", "branding", "narrative"):
            value = payload.pop(key, None)
            if value is not None:
                setattr(row, key, value)
        for key, value in payload.items():
            if value is not None:
                setattr(row, key, value)
        if data.theme:
            row.theme = data.theme
            style = dict(row.style or {})
            style["theme"] = data.theme
            row.style = style
        row.updated_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return _template_read(row)

    async def delete_template(self, template_id: UUID, project_id: UUID) -> None:
        row = await self.template(template_id, project_id)
        if row.is_builtin:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "A shipped template cannot be deleted."
            )
        await self.session.delete(row)
        await self.session.commit()

    async def _unique_slug(self, project_id: UUID, name: str) -> str:
        base = generate_slug(name)[:56] or "report"
        slug = base
        index = 2
        while await self.session.scalar(
            select(func.count(ReportTemplate.id)).where(
                ReportTemplate.project_id == project_id, ReportTemplate.slug == slug
            )
        ):
            slug = f"{base}-{index}"
            index += 1
        return slug

    # ---------- reports ----------

    async def _subject(
        self, data: ReportCreate, project_id: UUID
    ) -> tuple[Scan | None, Target]:
        scan = None
        target = None
        if data.scan_id is not None:
            scan = await self.session.get(Scan, data.scan_id)
            if scan is None or scan.project_id != project_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
            target = await self.session.get(Target, scan.target_id)
        elif data.target_id is not None:
            target = await self.session.get(Target, data.target_id)
        if target is None or target.project_id != project_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Choose a scan or a target for this report.",
            )
        return scan, target

    async def build_spec(
        self, data: ReportCreate, project_id: UUID
    ) -> tuple[ReportSpec, ReportTemplate | None]:
        template = None
        if data.template_id is not None:
            template = await self.template(data.template_id, project_id)

        sections = data.sections
        if sections is None and template is not None:
            sections = [SectionEntry.model_validate(s) for s in template.sections]
        if not sections:
            preset = PRESETS[0]
            sections = preset.entries()
        _validate_sections(sections)

        style = data.style or ReportStyle.model_validate(
            (template.style if template else {}) or {}
        )
        if data.theme:
            style.theme = data.theme
        elif template is not None and template.theme:
            style.theme = template.theme

        branding = data.branding or ReportBranding.model_validate(
            (template.branding if template else {}) or {}
        )
        defaults = await self.defaults()
        branding = _fill_empty(branding, defaults.branding)
        if not style.theme and defaults.theme:
            style.theme = defaults.theme
        narrative = data.narrative or NarrativeOptions.model_validate(
            (template.narrative if template else {}) or {}
        )
        cfg = await load_config_async(self.session)
        if narrative.ai_enabled and not (cfg and cfg.allows("report_narrative")):
            narrative.ai_enabled = False

        title = (
            data.title
            or (template.title if template else "")
            or "Security Assessment Report"
        )
        subtitle = data.subtitle or (template.subtitle if template else "")
        formats = (
            data.formats
            or (template.formats if template else None)
            or [ReportFormat.PDF.value]
        )

        return (
            ReportSpec(
                title=title,
                subtitle=subtitle,
                scope=coerce_scope(
                    data.scope or (template.scope if template else None)
                ),
                sections=sections,
                style=style,
                branding=branding,
                narrative=narrative,
                formats=[f for f in formats if f in FORMAT_LABELS],
            ),
            template,
        )

    async def create(
        self, data: ReportCreate, project_id: UUID, user_id: UUID
    ) -> ReportRead:
        scan, target = await self._subject(data, project_id)
        spec, template = await self.build_spec(data, project_id)

        report = Report(
            project_id=project_id,
            template_id=template.id if template else None,
            template_name=template.name if template else "Custom",
            scope=spec.scope,
            scan_id=scan.id if scan else None,
            target_id=target.id,
            subject=target.target_value,
            title=spec.title,
            spec=spec.model_dump(),
            status=ReportStatus.QUEUED.value,
            step="Queued",
            created_by=user_id,
        )
        self.session.add(report)
        if template is not None:
            template.used_count += 1
            template.last_used_at = utc_now()
            self.session.add(template)
        await self.session.commit()
        await self.session.refresh(report)

        dispatch_report(str(report.id))
        return self.to_read(report)

    async def _volumes(
        self, scan: Scan | None, severities: list[str] | None = None
    ) -> tuple[int, int, int, dict[str, int]]:
        """What the document will draw on, counted the way the sections filter it."""
        if scan is None:
            return (0, 0, 0, {})
        from shared.models.subdomain import Subdomain  # noqa: PLC0415
        from shared.models.vulnerability import Vulnerability  # noqa: PLC0415

        scoped = [Vulnerability.scan_id == scan.id]
        if severities is not None:
            scoped.append(Vulnerability.severity.in_(severities))
        findings = int(
            await self.session.scalar(
                select(func.count(Vulnerability.id)).where(*scoped)
            )
            or 0
        )
        issues = int(
            await self.session.scalar(
                select(func.count(func.distinct(Vulnerability.template_id))).where(
                    *scoped
                )
            )
            or 0
        )
        rows = (
            await self.session.execute(
                select(
                    Vulnerability.severity,
                    func.count(func.distinct(Vulnerability.template_id)),
                )
                .where(*scoped)
                .group_by(Vulnerability.severity)
            )
        ).all()
        by_severity = {str(severity): int(count) for severity, count in rows}
        assets = int(
            await self.session.scalar(
                select(func.count(Subdomain.id)).where(Subdomain.scan_id == scan.id)
            )
            or 0
        )
        return (findings, issues, assets, by_severity)

    async def estimate(self, data: ReportCreate, project_id: UUID) -> ReportEstimate:
        scan, _target = await self._subject(data, project_id)
        spec, _ = await self.build_spec(data, project_id)
        cfg = await load_config_async(self.session)
        enabled = [s for s in spec.sections if s.enabled]
        findings_cfg = _section_config(enabled, "findings_detail")
        findings, issues, assets, by_severity = await self._volumes(
            scan, findings_cfg.get("severities") if findings_cfg else None
        )
        estimate = ReportEstimate(
            sections=len(enabled),
            findings=findings,
            assets=assets,
            pages_estimated=_pages(
                enabled,
                issues=issues,
                assets=assets,
                by_severity=by_severity,
                chapter_breaks=spec.style.chapter_breaks,
            ),
        )
        if spec.narrative.ai_enabled and cfg is not None:
            calls = len(
                [
                    t
                    for t in REPORT_TASKS
                    if t
                    in (
                        "executive_summary",
                        "risk_narrative",
                        "remediation_plan",
                        "surface_narrative",
                    )
                ]
            )
            if spec.narrative.explain_findings:
                calls += min(spec.narrative.max_explained_issues, max(1, findings // 8))
            estimate.ai_calls = calls
            estimate.ai_input_tokens = calls * 3000
            estimate.ai_output_tokens = (
                sum(TASK_OUTPUT_TOKENS.get(t, 900) for t in REPORT_TASKS)
                + (calls - len(REPORT_TASKS)) * 500
            )
            cost = price(cfg.model, estimate.ai_input_tokens, estimate.ai_output_tokens)
            estimate.ai_cost_usd = round(cost, 4) if cost else 0.0
            if cost is None:
                estimate.warnings.append(
                    "This provider does not publish per-token pricing here, so no cost is shown."
                )
        for entry in enabled:
            spec_row = lookup_section(entry.section)
            if spec_row is None:
                estimate.warnings.append(
                    f"'{entry.section}' is not a known section and will be skipped."
                )
        return estimate

    async def list(
        self,
        project_id: UUID,
        *,
        scan_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> list[ReportRead]:
        query = select(Report).where(Report.project_id == project_id)
        if scan_id is not None:
            query = query.where(Report.scan_id == scan_id)
        if target_id is not None:
            query = query.where(Report.target_id == target_id)
        rows = (
            (
                await self.session.execute(
                    query.order_by(Report.created_at.desc()).limit(_MAX_LIST)
                )
            )
            .scalars()
            .all()
        )
        return [self.to_read(row) for row in rows]

    async def get(self, report_id: UUID, project_id: UUID) -> Report:
        row = await self.session.get(Report, report_id)
        if row is None or row.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
        return row

    async def delete(self, report_id: UUID, project_id: UUID) -> None:
        row = await self.get(report_id, project_id)
        root = Path(REPORT_ROOT) / str(row.id)
        if root.exists():
            for item in root.iterdir():
                item.unlink(missing_ok=True)
            root.rmdir()
        await self.session.delete(row)
        await self.session.commit()

    async def retry(self, report_id: UUID, project_id: UUID) -> ReportRead:
        row = await self.get(report_id, project_id)
        row.status = ReportStatus.QUEUED.value
        row.progress = 0
        row.step = "Queued"
        row.error = None
        row.started_at = None
        row.completed_at = None
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        dispatch_report(str(row.id))
        return self.to_read(row)

    def file_path(self, report: Report, fmt: str) -> tuple[Path, str]:
        for entry in report.files or []:
            if entry.get("format") == fmt:
                path = Path(REPORT_ROOT) / str(report.id) / str(entry.get("filename"))
                if path.is_file():
                    return path, str(entry.get("filename"))
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "That format was not generated for this report."
        )

    @staticmethod
    def to_read(report: Report) -> ReportRead:
        spec = report.spec or {}
        style = spec.get("style") or {}
        return ReportRead(
            id=report.id,
            project_id=report.project_id,
            template_id=report.template_id,
            template_name=report.template_name,
            scope=report.scope,
            scan_id=report.scan_id,
            target_id=report.target_id,
            subject=report.subject,
            title=report.title,
            status=report.status,
            progress=report.progress,
            step=report.step,
            error=report.error,
            files=[ReportFile.model_validate(f) for f in (report.files or [])],
            page_count=report.page_count,
            stats=report.stats or {},
            theme=style.get("theme", ""),
            formats=[f.get("format") for f in (report.files or [])]
            or list(spec.get("formats") or []),
            ai_used=report.ai_used,
            ai_model=report.ai_model,
            ai_calls=report.ai_calls,
            ai_input_tokens=report.ai_input_tokens,
            ai_output_tokens=report.ai_output_tokens,
            ai_cached_calls=report.ai_cached_calls,
            duration_seconds=report.duration_seconds,
            created_by=report.created_by,
            created_at=report.created_at,
            started_at=report.started_at,
            completed_at=report.completed_at,
            expires_at=report.expires_at,
        )


# a table section prints roughly this many rows on a page
_ROWS_PER_PAGE = 42
# a weakness, with and without its request and response
_PAGES_PER_ISSUE = 0.9
_PAGES_PER_ISSUE_EVIDENCE = 1.8
# a rolled-up observation costs a table row rather than an entry
_ROLLED_PER_PAGE = 26
_QUIET_SEVERITIES = frozenset({Severity.INFO.value, Severity.UNKNOWN.value})
# a chapter that runs on reclaims most of the page its predecessor left unfilled
_PAGE_SAVED_PER_RUN_ON = 0.4
_PAGE_TAIL_PER_CHAPTER = 0.3


def _section_config(sections: list[SectionEntry], name: str) -> dict | None:
    entry = next((e for e in sections if e.section == name), None)
    if entry is None:
        return None
    spec = lookup_section(name)
    return {**(spec.defaults if spec else {}), **(entry.config or {})}


def _pages(
    sections: list[SectionEntry],
    *,
    issues: int,
    assets: int,
    by_severity: dict[str, int] | None = None,
    chapter_breaks: bool = True,
) -> int:
    """Estimated length, read from each section's own limits rather than the raw totals."""
    total = 0.0
    for entry in sections:
        spec = lookup_section(entry.section)
        if spec is None:
            continue
        config = {**spec.defaults, **(entry.config or {})}
        name = spec.name
        if name == "findings_detail":
            weight = (
                _PAGES_PER_ISSUE_EVIDENCE
                if config.get("show_evidence", True)
                else _PAGES_PER_ISSUE
            )
            counts = by_severity or {}
            shown = min(issues, int(config.get("max_issues", 60)))
            scale = shown / issues if issues else 0.0
            # each tier costs a different amount: a table row, a short entry, a full write-up
            quiet = (
                sum(counts.get(s, 0) for s in _QUIET_SEVERITIES)
                if config.get("roll_up_info", True)
                else 0
            )
            cut = SEVERITY_ORDER.index(config.get("detail_from", Severity.MEDIUM.value))
            brief = sum(
                count
                for severity, count in counts.items()
                if severity in SEVERITY_ORDER
                and severity not in _QUIET_SEVERITIES
                and SEVERITY_ORDER.index(severity) > cut
            )
            full = max(0, issues - quiet - brief)
            total += scale * (
                full * weight + brief * _PAGES_PER_ISSUE + quiet / _ROLLED_PER_PAGE
            )
        elif name == "appendix_assets":
            total += max(1.0, min(assets, int(config.get("max_rows", 1500))) / 260)
        elif "max_rows" in config:
            total += max(1.0, min(assets, int(config["max_rows"])) / _ROWS_PER_PAGE)
        elif name == "screenshots":
            per_page = max(1, int(config.get("columns", 2) or 2)) * 3
            total += max(1.0, int(config.get("max_images", 12)) / per_page)
        elif name == "cover":
            total += 1
        else:
            total += 1
    tails = max(0, len(sections) - 2)
    # a chapter that starts its own page leaves part of the previous one unfilled
    total += (
        _PAGE_TAIL_PER_CHAPTER if chapter_breaks else -_PAGE_SAVED_PER_RUN_ON
    ) * tails
    return max(2, round(total))


def _fill_empty(branding: ReportBranding, defaults: ReportBranding) -> ReportBranding:
    """Instance defaults fill what a template left blank; they never overwrite a choice."""
    merged = branding.model_dump()
    for key, fallback in defaults.model_dump().items():
        if not merged.get(key) and fallback:
            merged[key] = fallback
    return ReportBranding.model_validate(merged)


def _validate_sections(sections: list[SectionEntry]) -> None:
    if len(sections) > MAX_SECTIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"A report may hold at most {MAX_SECTIONS} sections.",
        )
    seen: set[str] = set()
    for entry in sections:
        spec = lookup_section(entry.section)
        if spec is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Unknown section '{entry.section}'."
            )
        if not spec.repeatable and entry.section in seen:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"'{spec.title}' can only appear once in a report.",
            )
        seen.add(entry.section)
        try:
            spec.config(entry.config)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"{spec.title}: {exc}"
            ) from exc


def _template_read(row: ReportTemplate) -> ReportTemplateRead:
    return ReportTemplateRead(
        id=row.id,
        project_id=row.project_id,
        slug=row.slug,
        name=row.name,
        description=row.description,
        title=row.title,
        subtitle=row.subtitle,
        preset=row.preset,
        tags=list(row.tags or []),
        scope=row.scope,
        sections=[SectionEntry.model_validate(s) for s in (row.sections or [])],
        theme=row.theme,
        style=ReportStyle.model_validate(row.style or {}),
        branding=ReportBranding.model_validate(row.branding or {}),
        narrative=NarrativeOptions.model_validate(row.narrative or {}),
        formats=list(row.formats or []),
        is_builtin=row.is_builtin,
        is_default=row.is_default,
        used_count=row.used_count,
        last_used_at=row.last_used_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _preset_payload(preset: Preset) -> dict:
    return {
        "slug": preset.slug,
        "name": preset.name,
        "description": preset.description,
        "scope": preset.scope,
        "theme": preset.theme,
        "title": preset.title,
        "subtitle": preset.subtitle,
        "audience": preset.audience,
        "depth": preset.depth,
        "density": preset.density,
        "formats": list(preset.formats),
        "tags": list(preset.tags),
        "sections": [
            {"section": name, "config": dict(config)}
            for name, config in preset.sections
        ],
    }
