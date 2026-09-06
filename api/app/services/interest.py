"""Read side of interest: the rule library, the ranked list, and dismissals."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import bindparam, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import compile_query, parse_query
from app.services.asset_query.ast import QuerySyntaxError
from app.services.asset_query.compiler import QueryContext
from shared.definitions.interest import (
    BAND_FLOOR,
    BAND_LABELS,
    BAND_ORDER,
    BAND_TONES,
    JUDGEMENT_SOURCES,
    KEYWORD_FIELD_LABELS,
    KINDS,
    MAX_RULES,
    MAX_SCORE,
    RULE_MODE_LABELS,
    SOURCE_HELP,
    SOURCE_LABELS,
    InterestSource,
    RuleMode,
    coerce_kind,
    kind_label,
    kind_weight,
)
from shared.logging import get_logger
from shared.models.interest import (
    BandEntry,
    InterestCatalog,
    InterestDismissal,
    InterestFilter,
    InterestPage,
    InterestRow,
    InterestRule,
    InterestRuleCreate,
    InterestRuleRead,
    InterestRuleUpdate,
    InterestSignal,
    InterestSummary,
    KindEntry,
    RulePreview,
    RuleSuggestion,
    SignalRead,
    SourceEntry,
)
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

PREVIEW_CAP = 2000
SAMPLE = 5


class InterestError(ValueError):
    """The rule cannot be stored as written."""


def catalog() -> InterestCatalog:
    from interest.registry import provider_names  # noqa: PLC0415

    return InterestCatalog(
        kinds=[
            KindEntry(
                key=k.key, label=k.label, help=k.help, weight=k.weight, tone=k.tone
            )
            for k in KINDS
        ],
        sources=[
            SourceEntry(
                key=key,
                label=label,
                help=SOURCE_HELP.get(key, ""),
                judgement=key in JUDGEMENT_SOURCES,
            )
            for key, label in SOURCE_LABELS.items()
        ],
        bands=[
            BandEntry(
                key=band,
                label=BAND_LABELS[band],
                tone=BAND_TONES[band],
                floor=BAND_FLOOR[band],
            )
            for band in BAND_ORDER
        ],
        modes=dict(RULE_MODE_LABELS),
        keyword_fields=dict(KEYWORD_FIELD_LABELS),
        max_score=MAX_SCORE,
        providers=list(provider_names()),
    )


def _to_read(rule: InterestRule, matches: int | None = None) -> InterestRuleRead:
    return InterestRuleRead(
        id=rule.id,
        project_id=rule.project_id,
        name=rule.name,
        description=rule.description,
        mode=rule.mode,
        query=rule.query,
        keywords=list(rule.keywords or []),
        keyword_fields=list(rule.keyword_fields or []),
        live_only=rule.live_only,
        kind=rule.kind,
        kind_label=kind_label(rule.kind),
        weight=rule.weight if rule.weight is not None else kind_weight(rule.kind),
        enabled=rule.enabled,
        builtin=rule.builtin,
        notify=rule.notify,
        updated_at=rule.updated_at,
        matches=matches,
    )


class InterestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_builtin(self) -> None:
        from interest.presets import PRESETS, drift  # noqa: PLC0415

        rows = {
            row.name: row
            for row in (
                await self.session.execute(
                    select(InterestRule).where(InterestRule.builtin.is_(True))
                )
            )
            .scalars()
            .all()
        }
        changed = False
        for preset in PRESETS:
            current = rows.get(preset.name)
            if current is not None:
                for key, value in drift(current, preset).items():
                    setattr(current, key, value)
                    current.updated_at = utc_now()
                    changed = True
                continue
            self.session.add(
                InterestRule(
                    project_id=None,
                    name=preset.name,
                    description=preset.description,
                    mode=preset.mode,
                    query=preset.query,
                    keywords=list(preset.keywords),
                    keyword_fields=list(preset.keyword_fields),
                    live_only=preset.live_only,
                    kind=preset.kind,
                    weight=preset.weight,
                    enabled=preset.enabled,
                    builtin=True,
                    notify=preset.notify,
                )
            )
            changed = True
        if changed:
            await self.session.commit()

    async def rules(self, project_id: uuid.UUID) -> list[InterestRuleRead]:
        await self.ensure_builtin()
        rows = (
            (
                await self.session.execute(
                    select(InterestRule)
                    .where(
                        or_(
                            InterestRule.project_id.is_(None),
                            InterestRule.project_id == project_id,
                        )
                    )
                    .order_by(InterestRule.builtin.desc(), InterestRule.name)
                )
            )
            .scalars()
            .all()
        )
        counts = await self._match_counts(project_id)
        return [_to_read(row, counts.get(row.id, 0)) for row in rows]

    async def _match_counts(self, project_id: uuid.UUID) -> dict[uuid.UUID, int]:
        rows = await self.session.execute(
            select(
                InterestSignal.rule_id,
                func.count(func.distinct(InterestSignal.host)),
            )
            .where(
                InterestSignal.project_id == project_id,
                InterestSignal.rule_id.isnot(None),
            )
            .group_by(InterestSignal.rule_id)
        )
        return {row[0]: int(row[1]) for row in rows}

    def _validate(self, query: str) -> None:
        if not query.strip():
            return
        try:
            compile_query(
                parse_query(query), QueryContext(scan_id=uuid.uuid4(), now=utc_now())
            )
        except QuerySyntaxError as exc:
            raise InterestError(exc.message) from exc

    async def create(
        self, payload: InterestRuleCreate, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> InterestRuleRead:
        total = await self.session.scalar(
            select(func.count(InterestRule.id)).where(
                InterestRule.project_id == project_id
            )
        )
        if int(total or 0) >= MAX_RULES:
            msg = f"A project may hold {MAX_RULES} rules."
            raise InterestError(msg)

        mode = (
            payload.mode if payload.mode in RULE_MODE_LABELS else RuleMode.QUERY.value
        )
        keywords = [w.strip() for w in payload.keywords if w.strip()]
        if mode == RuleMode.KEYWORD.value and not keywords:
            msg = "Add at least one keyword."
            raise InterestError(msg)
        if mode == RuleMode.QUERY.value:
            if not payload.query.strip():
                msg = "Add a query."
                raise InterestError(msg)
            self._validate(payload.query)

        rule = InterestRule(
            project_id=project_id,
            name=payload.name.strip(),
            description=payload.description,
            mode=mode,
            query=payload.query.strip(),
            keywords=keywords,
            keyword_fields=[
                f for f in payload.keyword_fields if f in KEYWORD_FIELD_LABELS
            ]
            or ["host"],
            live_only=payload.live_only,
            kind=coerce_kind(payload.kind),
            weight=payload.weight,
            enabled=payload.enabled,
            builtin=False,
            notify=payload.notify,
            created_by=user_id,
        )
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return _to_read(rule, 0)

    async def update(
        self, rule_id: uuid.UUID, payload: InterestRuleUpdate
    ) -> InterestRuleRead | None:
        rule = await self.session.get(InterestRule, rule_id)
        if rule is None:
            return None
        data = payload.model_dump(exclude_unset=True)

        # a shipped rule keeps its identity; only what it matches and whether it runs may move
        if rule.builtin:
            allowed = {
                "enabled",
                "notify",
                "keywords",
                "keyword_fields",
                "weight",
                "live_only",
            }
            data = {k: v for k, v in data.items() if k in allowed}

        if "query" in data and data["query"] is not None:
            self._validate(data["query"])
        if "keywords" in data and data["keywords"] is not None:
            data["keywords"] = [w.strip() for w in data["keywords"] if w.strip()]
        if "keyword_fields" in data and data["keyword_fields"] is not None:
            data["keyword_fields"] = [
                f for f in data["keyword_fields"] if f in KEYWORD_FIELD_LABELS
            ] or ["host"]
        if "kind" in data and data["kind"] is not None:
            data["kind"] = coerce_kind(data["kind"])

        for key, value in data.items():
            setattr(rule, key, value)
        rule.updated_at = utc_now()
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return _to_read(rule)

    async def delete(self, rule_id: uuid.UUID) -> bool:
        rule = await self.session.get(InterestRule, rule_id)
        if rule is None or rule.builtin:
            return False
        await self.session.delete(rule)
        await self.session.commit()
        return True

    async def preview(self, query: str, scan_id: uuid.UUID | None) -> RulePreview:
        if not query.strip():
            return RulePreview()
        try:
            node = parse_query(query)
        except QuerySyntaxError as exc:
            return RulePreview(error=exc.message)
        if scan_id is None:
            return RulePreview()
        try:
            predicate = compile_query(
                node, QueryContext(scan_id=scan_id, now=utc_now())
            )
        except QuerySyntaxError as exc:
            return RulePreview(error=exc.message)

        stmt = select(Subdomain.name).where(
            Subdomain.scan_id == scan_id, Subdomain.is_excluded.is_(False)
        )
        if predicate is not None:
            stmt = stmt.where(predicate)
        rows = (await self.session.execute(stmt.limit(PREVIEW_CAP))).scalars().all()
        return RulePreview(
            matches=len(rows),
            capped=len(rows) >= PREVIEW_CAP,
            sample=list(rows[:SAMPLE]),
        )


from shared.services.interest import HOST_ROLLUP_SQL  # noqa: E402


def _signature(rules: list[InterestRule]) -> str:
    from shared.services.interest import signature  # noqa: PLC0415

    return signature(rules)


class InterestReadService(InterestService):
    async def _applicable(self, project_id: uuid.UUID) -> list[InterestRule]:
        return list(
            (
                await self.session.execute(
                    select(InterestRule).where(
                        InterestRule.enabled.is_(True),
                        or_(
                            InterestRule.project_id.is_(None),
                            InterestRule.project_id == project_id,
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )

    def _filtered(self, scan_id: uuid.UUID, f: InterestFilter):
        stmt = select(Subdomain).where(
            Subdomain.scan_id == scan_id,
            Subdomain.interest_band.isnot(None),
        )
        if f.q:
            stmt = stmt.where(Subdomain.name.ilike(f"%{f.q.strip()}%"))
        if f.bands:
            stmt = stmt.where(Subdomain.interest_band.in_(f.bands))
        if f.kinds:
            stmt = stmt.where(
                select(1)
                .where(
                    InterestSignal.subdomain_id == Subdomain.id,
                    InterestSignal.scan_id == scan_id,
                    InterestSignal.kind.in_(f.kinds),
                )
                .exists()
            )
        if f.sources:
            stmt = stmt.where(
                select(1)
                .where(
                    InterestSignal.subdomain_id == Subdomain.id,
                    InterestSignal.scan_id == scan_id,
                    InterestSignal.source.in_(f.sources),
                )
                .exists()
            )
        return stmt

    async def page(self, scan: Scan, f: InterestFilter) -> InterestPage:
        stmt = self._filtered(scan.id, f)
        total = int(
            await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
            or 0
        )
        descending = f.order != "asc"
        column = Subdomain.name if f.sort == "host" else Subdomain.interest_score
        ordering = column.desc() if descending else column.asc()
        rows = (
            (
                await self.session.execute(
                    stmt.order_by(ordering, Subdomain.name)
                    .offset(f.offset)
                    .limit(f.limit)
                )
            )
            .scalars()
            .all()
        )
        signals = await self._signals(scan.id, [r.id for r in rows])
        return InterestPage(
            rows=[self._row(r, signals.get(r.id, [])) for r in rows],
            total=total,
            summary=await self.summary(scan),
        )

    async def _signals(
        self, scan_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[InterestSignal]]:
        if not ids:
            return {}
        rows = (
            (
                await self.session.execute(
                    select(InterestSignal)
                    .where(
                        InterestSignal.scan_id == scan_id,
                        InterestSignal.subdomain_id.in_(ids),
                    )
                    .order_by(InterestSignal.weight.desc())
                )
            )
            .scalars()
            .all()
        )
        grouped: dict[uuid.UUID, list[InterestSignal]] = defaultdict(list)
        for row in rows:
            grouped[row.subdomain_id].append(row)
        return grouped

    def _row(self, host: Subdomain, signals: list[InterestSignal]) -> InterestRow:
        kinds = list(host.interest_kinds or [])
        return InterestRow(
            subdomain_id=host.id,
            host=host.name,
            score=host.interest_score,
            band=host.interest_band or "",
            kinds=kinds,
            sources=sorted({s.source for s in signals}),
            signals=[
                SignalRead(
                    source=s.source,
                    kind=s.kind,
                    kind_label=kind_label(s.kind),
                    label=s.label,
                    reason=s.reason,
                    evidence=s.evidence,
                    weight=s.weight,
                    rule_id=s.rule_id,
                    model=s.model,
                    judgement=s.source in JUDGEMENT_SOURCES,
                )
                for s in signals
            ],
            http_status=host.http_status,
            page_title=host.page_title,
            tech=list(host.tech or []),
            webserver=host.webserver,
            resolved_ips=list(host.resolved_ips or []),
            asn=host.asn,
            asn_org=host.asn_org,
            is_cdn=host.is_cdn,
            screenshot_path=host.screenshot_path,
            is_new="newly_appeared" in kinds,
        )

    async def summary(self, scan: Scan) -> InterestSummary:
        from shared.services.ai.config import load_config_async  # noqa: PLC0415

        bands = {
            row[0]: int(row[1])
            for row in await self.session.execute(
                select(Subdomain.interest_band, func.count(Subdomain.id))
                .where(
                    Subdomain.scan_id == scan.id, Subdomain.interest_band.isnot(None)
                )
                .group_by(Subdomain.interest_band)
            )
        }
        sources = {
            row[0]: int(row[1])
            for row in await self.session.execute(
                select(
                    InterestSignal.source,
                    func.count(func.distinct(InterestSignal.subdomain_id)),
                )
                .where(InterestSignal.scan_id == scan.id)
                .group_by(InterestSignal.source)
            )
        }
        kinds = {
            row[0]: int(row[1])
            for row in await self.session.execute(
                select(
                    InterestSignal.kind,
                    func.count(func.distinct(InterestSignal.subdomain_id)),
                )
                .where(InterestSignal.scan_id == scan.id)
                .group_by(InterestSignal.kind)
            )
        }
        dismissed = int(
            await self.session.scalar(
                select(func.count(InterestDismissal.id)).where(
                    InterestDismissal.target_id == scan.target_id
                )
            )
            or 0
        )
        cfg = await load_config_async(self.session)
        rules = await self._applicable(scan.project_id)
        return InterestSummary(
            total=sum(bands.values()),
            bands=bands,
            sources=sources,
            kinds=kinds,
            dismissed=dismissed,
            judged_hosts=sources.get(InterestSource.AI.value, 0),
            judged_at=scan.interest_judged_at,
            model=scan.interest_model,
            ai_available=bool(cfg and cfg.available),
            ai_enabled=bool(cfg and cfg.allows("asset_judgement")),
            stale=scan.interest_signature != _signature(rules),
        )

    async def dismiss(
        self,
        *,
        target_id: uuid.UUID,
        project_id: uuid.UUID,
        host: str,
        kind: str,
        note: str | None,
        user_id: uuid.UUID,
    ) -> None:
        existing = await self.session.scalar(
            select(InterestDismissal).where(
                InterestDismissal.target_id == target_id,
                InterestDismissal.host == host,
                InterestDismissal.kind == kind,
            )
        )
        if existing is None:
            self.session.add(
                InterestDismissal(
                    target_id=target_id,
                    project_id=project_id,
                    host=host,
                    kind=kind,
                    note=note,
                    created_by=user_id,
                )
            )
        await self.session.execute(
            delete(InterestSignal).where(
                InterestSignal.target_id == target_id,
                InterestSignal.host == host,
                *([InterestSignal.kind == kind] if kind else []),
            )
        )
        # the denormalised rank has to follow the signals, or the row stays in the list
        await self.session.execute(
            text(HOST_ROLLUP_SQL).bindparams(
                bindparam("tid", target_id),
                bindparam("host", host),
                bindparam("cap", MAX_SCORE),
            )
        )
        await self.session.commit()

    async def restore(self, dismissal_id: uuid.UUID) -> bool:
        row = await self.session.get(InterestDismissal, dismissal_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    async def dismissals(
        self,
        *,
        target_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> list[InterestDismissal]:
        stmt = select(InterestDismissal)
        if target_id is not None:
            stmt = stmt.where(InterestDismissal.target_id == target_id)
        if project_id is not None:
            stmt = stmt.where(InterestDismissal.project_id == project_id)
        return list(
            (
                await self.session.execute(
                    stmt.order_by(InterestDismissal.created_at.desc()).limit(500)
                )
            )
            .scalars()
            .all()
        )

    async def suggestions(self, scan: Scan) -> list[RuleSuggestion]:
        """A proposal, counted against this scan, that becomes a rule only if someone accepts it."""
        from interest.providers.ai.suggest import MAX_EXAMPLES, propose  # noqa: PLC0415
        from shared.services.ai.config import load_config_async  # noqa: PLC0415

        cfg = await load_config_async(self.session)
        if cfg is None:
            return []

        rows = (
            await self.session.execute(
                select(InterestSignal.host, InterestSignal.kind, InterestSignal.reason)
                .where(
                    InterestSignal.scan_id == scan.id,
                    InterestSignal.source == InterestSource.AI.value,
                    InterestSignal.reason != "",
                )
                .order_by(InterestSignal.weight.desc())
                .limit(MAX_EXAMPLES)
            )
        ).all()
        if not rows:
            return []

        examples = [
            {"host": r.host, "reason_kind": r.kind, "reason": r.reason} for r in rows
        ]
        existing = {
            (row or "").strip()
            for row in (
                await self.session.execute(
                    select(InterestRule.query).where(
                        or_(
                            InterestRule.project_id.is_(None),
                            InterestRule.project_id == scan.project_id,
                        )
                    )
                )
            ).scalars()
        }

        out: list[RuleSuggestion] = []
        for item in propose(self.session, cfg, examples):
            query = item["query"]
            if query in existing:
                continue
            preview = await self.preview(query, scan.id)
            # a rule that matches nothing, everything, or does not compile is not a suggestion
            if preview.error or preview.matches == 0:
                continue
            out.append(
                RuleSuggestion(
                    name=item["name"],
                    kind=item["kind"],
                    kind_label=item["kind_label"],
                    query=query,
                    reason=item["reason"],
                    matches=preview.matches,
                )
            )
        await self.session.commit()
        return out
