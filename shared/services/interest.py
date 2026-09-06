"""Runs every provider over one scan and writes what it found. The worker's side of interest."""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import bindparam, delete, or_, select, text
from sqlalchemy.orm import Session

from interest import InterestContext, RawSignal, providers
from interest.presets import PRESETS, drift
from shared.definitions.interest import (
    BAND_FLOOR,
    BAND_ORDER,
    MAX_SCORE,
    MAX_SIGNALS_PER_HOST,
    InterestBand,
    InterestSource,
    RuleMode,
    kind_weight,
)
from shared.definitions.notifications import InterestLead
from shared.logging import get_logger
from shared.models.interest import InterestDismissal, InterestRule, InterestSignal
from shared.models.scan import Scan
from shared.services.ai.config import AIConfig
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

SIGNATURE_VERSION = "1"
DETERMINISTIC_SOURCES: tuple[str, ...] = (
    InterestSource.KEYWORD.value,
    InterestSource.RULE.value,
    InterestSource.CORRELATION.value,
)


@dataclass
class EvaluationResult:
    hosts: int = 0
    signals: int = 0
    bands: dict[str, int] = field(default_factory=dict)
    kinds: dict[str, int] = field(default_factory=dict)
    ai_used: bool = False
    model: str | None = None
    ran: list[str] = field(default_factory=list)


def _band_case(column: str) -> str:
    parts = " ".join(
        f"WHEN {column} >= {int(BAND_FLOOR[band])} THEN '{band}'" for band in BAND_ORDER
    )
    return f"CASE {parts} ELSE NULL END"


_RESET_SQL = """
UPDATE subdomains
SET interest_score = 0, interest_band = NULL, interest_kinds = '[]'::json
WHERE scan_id = :sid AND (interest_score <> 0 OR interest_band IS NOT NULL)
"""

_ROLLUP_SQL = f"""
WITH agg AS (
    SELECT subdomain_id,
           LEAST(:cap, SUM(weight))::int AS score,
           jsonb_agg(DISTINCT kind) AS kinds
    FROM interest_signals
    WHERE scan_id = :sid
    GROUP BY subdomain_id
)
UPDATE subdomains s
SET interest_score = agg.score,
    interest_band = {_band_case("agg.score")},
    interest_kinds = agg.kinds::text::json
FROM agg
WHERE s.id = agg.subdomain_id AND s.scan_id = :sid
"""  # noqa: S608


HOST_ROLLUP_SQL = f"""
WITH scoped AS (
    SELECT id FROM subdomains WHERE target_id = :tid AND name = :host
),
agg AS (
    SELECT sig.subdomain_id,
           LEAST(:cap, SUM(sig.weight))::int AS score,
           jsonb_agg(DISTINCT sig.kind) AS kinds
    FROM interest_signals sig
    JOIN scoped ON scoped.id = sig.subdomain_id
    GROUP BY sig.subdomain_id
)
UPDATE subdomains s
SET interest_score = COALESCE(agg.score, 0),
    interest_band = {_band_case("COALESCE(agg.score, 0)")},
    interest_kinds = COALESCE(agg.kinds::text::json, '[]'::json)
FROM scoped
LEFT JOIN agg ON agg.subdomain_id = scoped.id
WHERE s.id = scoped.id
"""  # noqa: S608


def ensure_builtin(session: Session) -> int:
    """Seed the shipped library once, the way wordlists and themes index themselves on read."""
    rows = {
        row.name: row
        for row in session.execute(
            select(InterestRule).where(InterestRule.builtin.is_(True))
        )
        .scalars()
        .all()
    }
    added = 0
    for preset in PRESETS:
        current = rows.get(preset.name)
        if current is not None:
            changes = drift(current, preset)
            if changes:
                for key, value in changes.items():
                    setattr(current, key, value)
                current.updated_at = utc_now()
                session.add(current)
                added += 1
            continue
        session.add(
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
        added += 1
    if added:
        session.commit()
    return added


def applicable_rules(session: Session, project_id: uuid.UUID) -> list[InterestRule]:
    return list(
        session.execute(
            select(InterestRule)
            .where(
                InterestRule.enabled.is_(True),
                or_(
                    InterestRule.project_id.is_(None),
                    InterestRule.project_id == project_id,
                ),
            )
            .order_by(InterestRule.builtin.desc(), InterestRule.name)
        )
        .scalars()
        .all()
    )


def signature(rules: list[InterestRule]) -> str:
    parts = sorted(
        f"{r.id}:{r.updated_at.timestamp():.0f}:{int(r.enabled)}" for r in rules
    )
    body = f"{SIGNATURE_VERSION}|" + "|".join(parts)
    return hashlib.sha256(body.encode()).hexdigest()


def _dismissed(session: Session, target_id: uuid.UUID) -> set[tuple[str, str]]:
    rows = session.execute(
        select(InterestDismissal.host, InterestDismissal.kind).where(
            InterestDismissal.target_id == target_id
        )
    ).all()
    return {(row.host.lower(), row.kind or "") for row in rows}


def _keep(signal: RawSignal, dismissed: set[tuple[str, str]]) -> bool:
    host = signal.host.lower()
    return (host, "") not in dismissed and (host, signal.kind) not in dismissed


def _collect(
    ctx: InterestContext, include_ai: bool
) -> tuple[list[RawSignal], list[str], bool]:
    gathered: list[RawSignal] = []
    ran: list[str] = []
    ai_used = False
    for provider in providers():
        if provider.requires_ai and not include_ai:
            continue
        try:
            if not provider.available(ctx):
                continue
            produced = list(provider.evaluate(ctx))
        except Exception:
            logger.warning(
                "interest provider failed", provider=provider.name, exc_info=True
            )
            continue
        ran.append(provider.name)
        if provider.requires_ai and produced:
            ai_used = True
        gathered.extend(produced)
    return gathered, ran, ai_used


def _prune(
    signals: list[RawSignal], dismissed: set[tuple[str, str]]
) -> list[RawSignal]:
    """A booster never flags a host on its own, and no host carries more reasons than fit."""
    by_host: dict[uuid.UUID, list[RawSignal]] = defaultdict(list)
    for signal in signals:
        if _keep(signal, dismissed):
            by_host[signal.subdomain_id].append(signal)

    kept: list[RawSignal] = []
    for group in by_host.values():
        anchored = [s for s in group if not s.booster]
        if not anchored:
            continue
        ordered = sorted(group, key=lambda s: (-s.weight, s.source, s.key))
        seen: set[tuple[str, str]] = set()
        for signal in ordered:
            key = (signal.source, signal.key)
            if key in seen:
                continue
            seen.add(key)
            kept.append(signal)
            if len(seen) >= MAX_SIGNALS_PER_HOST:
                break
    return kept


def evaluate(
    session: Session,
    scan: Scan,
    *,
    ai: AIConfig | None = None,
    include_ai: bool = True,
    rules: list[InterestRule] | None = None,
) -> EvaluationResult:
    resolved = applicable_rules(session, scan.project_id) if rules is None else rules
    ctx = InterestContext(
        session=session, scan=scan, rules=resolved, ai=ai, now=utc_now()
    )

    signals, ran, ai_used = _collect(ctx, include_ai)
    kept = _prune(signals, _dismissed(session, scan.target_id))

    sources = (
        tuple({s.source for s in signals}) if include_ai else DETERMINISTIC_SOURCES
    )
    session.execute(
        delete(InterestSignal).where(
            InterestSignal.scan_id == scan.id,
            InterestSignal.source.in_(sources or DETERMINISTIC_SOURCES),
        )
    )
    session.flush()

    rows = [
        InterestSignal(
            scan_id=scan.id,
            target_id=scan.target_id,
            project_id=scan.project_id,
            subdomain_id=s.subdomain_id,
            host=s.host[:500],
            source=s.source,
            key=s.key[:120],
            kind=s.kind,
            weight=max(0, min(MAX_SCORE, s.weight)),
            label=s.label[:80],
            reason=s.reason,
            evidence=s.evidence,
            rule_id=s.rule_id,
            model=s.model,
            prompt_version=s.prompt_version,
        )
        for s in kept
        if s.source in (sources or DETERMINISTIC_SOURCES)
    ]
    session.add_all(rows)
    session.flush()

    _rollup(session, scan)

    scan.interest_signature = signature(resolved)
    if ai_used:
        scan.interest_judged_at = utc_now()
        scan.interest_model = ai.model_for_task(fast=True) if ai else None
    session.add(scan)
    session.commit()

    return _summarise(session, scan, ran, ai_used, ai)


def _rollup(session: Session, scan: Scan) -> None:
    session.execute(text(_RESET_SQL).bindparams(bindparam("sid", scan.id)))
    session.execute(
        text(_ROLLUP_SQL).bindparams(
            bindparam("sid", scan.id), bindparam("cap", MAX_SCORE)
        )
    )
    session.flush()


def _summarise(
    session: Session,
    scan: Scan,
    ran: list[str],
    ai_used: bool,
    ai: AIConfig | None,
) -> EvaluationResult:
    rows = session.execute(
        text(
            """
            SELECT interest_band AS band, count(*) AS c
            FROM subdomains
            WHERE scan_id = :sid AND interest_band IS NOT NULL
            GROUP BY interest_band
            """
        ).bindparams(bindparam("sid", scan.id))
    ).all()
    bands = {row.band: int(row.c) for row in rows}
    kinds = {
        row.kind: int(row.c)
        for row in session.execute(
            text(
                """
                SELECT kind, count(DISTINCT subdomain_id) AS c
                FROM interest_signals WHERE scan_id = :sid GROUP BY kind
                """
            ).bindparams(bindparam("sid", scan.id))
        ).all()
    }
    signals = int(
        session.execute(
            text(
                "SELECT count(*) AS c FROM interest_signals WHERE scan_id = :sid"
            ).bindparams(bindparam("sid", scan.id))
        ).scalar()
        or 0
    )
    return EvaluationResult(
        hosts=sum(bands.values()),
        signals=signals,
        bands=bands,
        kinds=kinds,
        ai_used=ai_used,
        model=(ai.model_for_task(fast=True) if ai and ai_used else None),
        ran=ran,
    )


def is_stale(session: Session, scan: Scan) -> bool:
    return scan.interest_signature != signature(
        applicable_rules(session, scan.project_id)
    )


def keyword_rule_defaults() -> dict:
    preset = next(p for p in PRESETS if p.mode == RuleMode.KEYWORD.value)
    return {
        "keywords": list(preset.keywords),
        "keyword_fields": list(preset.keyword_fields),
        "weight": kind_weight(preset.kind),
    }


_NEW_LEADS_SQL = """
WITH cutoff AS (SELECT created_at FROM scans WHERE id = :sid),
prior AS (
    SELECT DISTINCT sig.host
    FROM interest_signals sig
    JOIN scans sc ON sc.id = sig.scan_id
    WHERE sig.target_id = :tid
      AND sig.scan_id <> :sid
      AND sc.created_at < (SELECT created_at FROM cutoff)
),
current AS (
    SELECT sub.id, sub.name AS host, sub.interest_band AS band, sub.interest_score AS score
    FROM subdomains sub
    WHERE sub.scan_id = :sid AND sub.interest_band IS NOT NULL
)
SELECT c.host,
       c.band,
       c.score,
       EXISTS (
           SELECT 1 FROM interest_signals sig
           JOIN interest_rules r ON r.id = sig.rule_id
           WHERE sig.subdomain_id = c.id AND sig.scan_id = :sid AND r.notify = true
       ) AS notify_rule,
       (
           SELECT array_agg(DISTINCT sig2.kind)
           FROM interest_signals sig2
           WHERE sig2.subdomain_id = c.id AND sig2.scan_id = :sid
       ) AS kinds
FROM current c
WHERE NOT EXISTS (SELECT 1 FROM prior p WHERE p.host = c.host)
ORDER BY c.score DESC, c.host
LIMIT :cap
"""

NOTIFY_BANDS: frozenset[str] = frozenset(
    {InterestBand.CRITICAL.value, InterestBand.HIGH.value}
)
LEAD_CAP = 25


def new_interesting(
    session: Session, scan: Scan, cap: int = LEAD_CAP
) -> list[InterestLead]:
    """A host this target has never flagged before, and only when it is worth an interrupt."""
    rows = session.execute(
        text(_NEW_LEADS_SQL).bindparams(
            bindparam("sid", scan.id),
            bindparam("tid", scan.target_id),
            bindparam("cap", cap),
        )
    ).all()
    leads = []
    for row in rows:
        if row.band not in NOTIFY_BANDS and not row.notify_rule:
            continue
        leads.append(
            InterestLead(
                host=row.host,
                band=row.band,
                score=int(row.score or 0),
                kinds=tuple(row.kinds or ()),
            )
        )
    return leads
