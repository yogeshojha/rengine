"""Blocks: rows, groups and CVE records an answer shows, read from a stored query."""

from __future__ import annotations

import re
import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ask import tools
from app.services.ask.estate import causes, facts
from app.services.ask.estate.dimensions import DIMENSIONS, ROW_DIMENSIONS, groupable
from app.services.ask.estate.reading import fields_of, reading
from app.services.ask.estate.scope import Resolved
from app.services.surface_scope import SurfaceScopeService
from mcp.dimensions import Dimension
from mcp.errors import InvalidParamsError
from mcp.tools.query_assets import _explain
from shared.definitions.ask import (
    BLOCK_GROUPS,
    BLOCK_ROWS,
    MAX_BLOCK_QUERY,
    MAX_BLOCK_TITLE,
    BlockKind,
)
from shared.definitions.surface import SURFACE_NOUN
from shared.definitions.vulnerabilities import CVE_ID
from shared.logging import get_logger
from shared.models.ask import (
    AnswerBlock,
    BlockCauses,
    BlockData,
    BlockFactRead,
    BlockGroup,
)
from shared.models.vuln_template import VulnTemplate
from shared.services.asset_query import QueryScope, QuerySyntaxError, lead_cache
from shared.services.asset_query.parser import tokenize
from shared.utils.text import strip_control

logger = get_logger(__name__)

META_KEYS = ("id", "scan_id", "target_value", "targets", "fixed_in")
TERM = "TERM"
CMP = "CMP"
URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)
FIELDISH = re.compile(
    r"^([a-z][a-z0-9_]*(?:\.[a-z0-9_-]+)*)(?:!=|>=|<=|!~|[:=<>~])", re.I
)
MAX_DESCRIPTION = 700
RECORD_ROWS = 8
NOT_SHOWN = "Secret values are not shown in Ask. Group secrets by kind or state."
# a thread over one target groups by that target alone
SINGLE_TARGET_SKIP = frozenset({"target"})
TOO_LONG = (
    "The query and the scope's targets are too long to read together. Narrow the scope."
)


class BlockError(ValueError):
    pass


def dimension_of(key: str | None) -> Dimension:
    dim = DIMENSIONS.get(key or "")
    if dim is None:
        known = ", ".join(DIMENSIONS)
        msg = f"Unknown dimension {key!r}. Use one of: {known}."
        raise BlockError(msg)
    return dim


def clean_query(query: Any) -> str | None:
    if not isinstance(query, str):
        return None
    text = strip_control(query).strip()
    if len(text) > MAX_BLOCK_QUERY:
        msg = f"The query is longer than {MAX_BLOCK_QUERY} characters."
        raise BlockError(msg)
    return text or None


def check_fields(dim: Dimension, query: str | None) -> None:
    """Refuse a field the grammar does not know."""
    if not query:
        return
    try:
        tokens = tokenize(query, dim.registry)
    except QuerySyntaxError as exc:
        raise BlockError(str(exc)) from None
    for token in tokens:
        if token.kind == CMP and not all(
            any(c.isalnum() for c in v) for v in token.values
        ):
            msg = f"{token.field} needs a value with a letter or digit."
            raise BlockError(msg)
        if token.kind != TERM or token.quoted:
            continue
        text = token.text or query[token.start : token.end]
        if URL.match(text):
            continue
        found = FIELDISH.match(text)
        if found:
            msg = f"{dim.label} have no field {found.group(1)!r}."
            raise BlockError(msg)


def clean_title(title: Any, dimension: str | None = None) -> str | None:
    """The model's title, kept only when it names the rows its count is of."""
    if not isinstance(title, str):
        return None
    text = " ".join(title.split())[:MAX_BLOCK_TITLE]
    if dimension in SURFACE_NOUN:
        heads = {noun.split()[-1].lower() for noun in SURFACE_NOUN[dimension]}
        if not heads & set(text.lower().split()):
            return None
    return text or None


def _row(dim: Dimension, item: Any) -> dict:
    data = item if isinstance(item, dict) else item.model_dump(mode="json")
    row = dim.compact(data)
    for key in META_KEYS:
        if data.get(key) not in (None, "", [], {}):
            row[f"_{key}"] = data[key]
    return row


async def _covered(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    resolved: Resolved,
    service: SurfaceScopeService | None = None,
) -> int:
    service = service or SurfaceScopeService(session)
    if resolved.scan is not None:
        return int(await service.scan_covers(resolved.scan, dim.key))
    picks = await service.scans_by_target(project_id, dim.key)
    return sum(1 for target_id in picks if target_id in resolved.targets)


async def _scope(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    resolved: Resolved,
    service: SurfaceScopeService | None = None,
):
    service = service or SurfaceScopeService(session)
    if resolved.scan is not None:
        if not await service.scan_covers(resolved.scan, dim.key):
            return QueryScope((), project_id=project_id)
        return QueryScope((resolved.scan,), project_id=project_id)
    if not resolved.targets:
        return QueryScope((), project_id=project_id)
    if resolved.clause:
        picks = await service.scans_by_target(project_id, dim.key)
        if not any(target_id in resolved.targets for target_id in picks):
            return QueryScope((), project_id=project_id)
        return await service.scope(project_id, dim.key)
    return await service.scope(project_id, dim.key, resolved.targets)


def scoped(resolved: Resolved, query: str | None) -> str | None:
    """The query a scoped link runs: the scope's targets, then the query."""
    if not resolved.clause:
        return query
    return f"{resolved.clause} and ({query})" if query else resolved.clause


def _filter(dim: Dimension, resolved: Resolved, query: str | None, **page: int):
    try:
        return dim.build_filter(scoped(resolved, query), **page)
    except (ValueError, InvalidParamsError) as exc:
        raise BlockError(TOO_LONG if resolved.clause else str(exc)) from None


def _unscoped(text: str | None, wide: str | None, query: str | None) -> str | None:
    if not text or wide == query or not wide:
        return text
    head = f"({wide}) and "
    if not text.startswith(head):
        return text
    rest = text[len(head) :]
    return f"({query}) and {rest}" if query else rest


def _refused(dim: Dimension, query: str | None, group_by: str | None = None) -> None:
    args = {"dimension": dim.key, "query": query}
    if group_by:
        args["group_by"] = group_by
        name = "group_assets"
    else:
        name = "query_assets"
    if reason := tools.refusal(name, args):
        raise BlockError(reason)


class _Extras(BaseModel):
    scope_total: int | None = None
    scope_capped: bool = False
    facts: list[BlockFactRead] = []
    causes: BlockCauses | None = None


async def _extras(
    session: AsyncSession,
    project_id: uuid.UUID,
    dim: Dimension,
    scope: Any,
    block: AnswerBlock,
    out: BlockData,
    *,
    pick: bool,
    single: bool,
    resolved: Resolved,
) -> None:
    """Causes, counted facts and the rows in scope. A failure leaves them out."""
    skip = SINGLE_TARGET_SKIP if single else frozenset()
    key = None if pick else block.cause_key
    wide = scoped(resolved, block.query)

    async def build() -> _Extras:
        got = _Extras()
        whole = await facts.count(
            session, project_id, dim, scope, scoped(resolved, None)
        )
        if whole is not None:
            got.scope_total, got.scope_capped = whole
        got.facts = await facts.read(
            session, project_id, dim, scope, wide, out.total, out.capped
        )
        if pick and not out.capped:
            got.causes = await causes.pick(
                session,
                project_id,
                dim,
                scope,
                wide,
                out.total,
                skip=skip,
                named=fields_of(dim, block.query),
            )
        elif key:
            got.causes = await causes.read(session, project_id, dim, scope, wide, key)
        for fact in got.facts:
            fact.query = _unscoped(fact.query, wide, block.query) or fact.query
        for group in got.causes.groups if got.causes else []:
            group.query = _unscoped(group.query, wide, block.query)
        return got

    try:
        got = await lead_cache.cached(
            session,
            name=f"ask:block:{dim.key}",
            scans=tuple(scope.ids),
            facets=f"{project_id}|{wide or ''}|{key or ('pick' if pick else '')}"
            f"|{out.total}|{int(single)}",
            model=_Extras,
            build=build,
        )
    except Exception as exc:
        logger.info("ask block extras failed", block=block.id, error=str(exc))
        return
    out.scope_total, out.scope_capped = got.scope_total, got.scope_capped
    out.facts = got.facts
    out.causes = got.causes
    if pick:
        block.cause_key = got.causes.key if got.causes else None


async def rows(
    session: AsyncSession,
    project_id: uuid.UUID,
    resolved: Resolved,
    block: AnswerBlock,
    *,
    limit: int = BLOCK_ROWS,
    offset: int = 0,
    extras: bool = True,
    pick: bool = False,
) -> BlockData:
    dim = dimension_of(block.dimension)
    if dim.key not in ROW_DIMENSIONS:
        raise BlockError(NOT_SHOWN)
    check_fields(dim, block.query)
    _refused(dim, block.query)
    out = BlockData(id=block.id, kind=BlockKind.ROWS.value, dimension=dim.key)
    out.scope_values = resolved.links
    out.reading = reading(dim, block.query)
    service = SurfaceScopeService(session)
    out.covered = await _covered(session, project_id, dim, resolved, service)
    scope = await _scope(session, project_id, dim, resolved, service)
    if not scope:
        out.total = 0
        return out
    f = _filter(dim, resolved, block.query, limit=limit, offset=offset)
    page = await dim.search(session, scope, f, project_id)
    if getattr(page, "error", None):
        raise BlockError(_explain(page.error, block.query or ""))
    out.total = page.total
    out.capped = bool(page.total_capped)
    out.rows = [_row(dim, item) for item in page.items]
    if extras:
        await _extras(
            session,
            project_id,
            dim,
            scope,
            block,
            out,
            pick=pick,
            single=resolved.count == 1,
            resolved=resolved,
        )
    return out


async def groups(
    session: AsyncSession,
    project_id: uuid.UUID,
    resolved: Resolved,
    block: AnswerBlock,
    *,
    cap: int = BLOCK_GROUPS,
) -> BlockData:
    dim = dimension_of(block.dimension)
    if not groupable(dim.key):
        msg = f"{dim.label} cannot be grouped in Ask. Show rows instead."
        raise BlockError(msg)
    keys = [d.key for d in dim.registry.dimensions]
    if block.group_by not in keys:
        msg = (
            f"{dim.label} cannot be grouped by {block.group_by!r}. "
            f"Use one of: {', '.join(keys)}."
        )
        raise BlockError(msg)
    check_fields(dim, block.query)
    _refused(dim, block.query, block.group_by)
    out = BlockData(id=block.id, kind=BlockKind.GROUPS.value, dimension=dim.key)
    out.scope_values = resolved.links
    out.reading = reading(dim, block.query)
    service = SurfaceScopeService(session)
    out.covered = await _covered(session, project_id, dim, resolved, service)
    scope = await _scope(session, project_id, dim, resolved, service)
    if not scope:
        out.total = 0
        return out
    f = _filter(dim, resolved, block.query, limit=1, offset=0)
    result = await dim.groups(session, scope, f, block.group_by, project_id)
    if getattr(result, "error", None):
        raise BlockError(_explain(result.error, block.query or ""))
    out.total = result.rows
    out.groups = [
        BlockGroup(
            value=str(g.value),
            label=str(g.label or g.value),
            count=g.count,
            query=g.query,
        )
        for g in result.groups[:cap]
    ]
    return out


async def _checks(session: AsyncSession, cve: str) -> int:
    held = cast(VulnTemplate.cve_ids, JSONB).has_key(cve)
    return int(
        await session.scalar(select(func.count()).select_from(VulnTemplate).where(held))
        or 0
    )


async def cve(
    session: AsyncSession,
    project_id: uuid.UUID,
    resolved: Resolved,
    block: AnswerBlock,
) -> BlockData:
    from app.services.cve_exposure import CveExposureService  # noqa: PLC0415

    name = (block.cve or "").strip().upper()
    if not CVE_ID.match(name):
        msg = f"{block.cve!r} is not a CVE identifier."
        raise BlockError(msg)
    if resolved.scan is not None:
        msg = (
            "A CVE summary reads every scan. In one scan, show vulnerability "
            f"or software rows with cve={name}."
        )
        raise BlockError(msg)
    report = await CveExposureService(session).exposure(
        project_id, name, resolved.targets if resolved.filtered else None
    )
    description = report.description or ""
    record = {
        "cve": name,
        "known": report.known,
        "severity": report.severity,
        "cvss_score": report.cvss_score,
        "cvss_vector": report.cvss_vector,
        "description": description[:MAX_DESCRIPTION],
        "published_at": report.published_at,
        "epss_score": report.epss_score,
        "epss_percentile": report.epss_percentile,
        "is_kev": report.is_kev,
        "kev_ransomware": report.kev_ransomware,
        "kev_date_added": report.kev_date_added,
        "kev_due_date": report.kev_due_date,
        "kev_required_action": report.kev_required_action,
        "exploit_score": report.exploit_score,
        "assets": report.assets,
        "targets": report.targets,
        "first_seen": report.first_seen,
        "ladder": [
            {
                "evidence": s.evidence,
                "count": s.count,
                "software": s.software,
                "findings": s.findings,
            }
            for s in report.ladder
        ],
        "by_target": [
            {"target": t.target_value, "assets": t.assets} for t in report.by_target
        ][:RECORD_ROWS],
        "locations": [
            {
                "host": loc.host,
                "ip": loc.ip,
                "port": loc.port,
                "evidence": loc.evidence,
                "dimension": loc.dimension,
                "target": loc.target_value,
            }
            for loc in report.locations[:RECORD_ROWS]
        ],
        "locations_total": report.locations_total,
        "suppressed": report.suppressed,
        "corpus_ready": report.corpus_ready,
        "finding_scans": report.finding_scans,
        "checks": await _checks(session, name),
    }
    return BlockData(
        id=block.id,
        kind=BlockKind.CVE.value,
        total=report.assets,
        record=record,
        scope_values=resolved.links,
    )


async def read(
    session: AsyncSession,
    project_id: uuid.UUID,
    resolved: Resolved,
    block: AnswerBlock,
) -> BlockData:
    """What a stored block shows now, or the error its query raises."""
    try:
        if block.kind == BlockKind.ROWS.value:
            return await rows(session, project_id, resolved, block)
        if block.kind == BlockKind.GROUPS.value:
            return await groups(session, project_id, resolved, block)
        if block.kind == BlockKind.CVE.value:
            return await cve(session, project_id, resolved, block)
    except BlockError as exc:
        return BlockData(
            id=block.id,
            kind=block.kind,
            dimension=block.dimension,
            error=str(exc),
            scope_values=resolved.links,
        )
    return BlockData(id=block.id, kind=block.kind, error="Unknown block.")


def noun(dimension: str | None, count: int | None) -> str:
    one, many = SURFACE_NOUN.get(dimension or "", ("row", "rows"))
    return one if count == 1 else many


def headline(data: BlockData) -> str:
    """One line a model reads back for a block."""
    if data.error:
        return f"{data.id} failed: {data.error}"
    plus = "+" if data.capped else ""
    if data.kind == BlockKind.CVE.value and data.record:
        assets = data.record.get("assets") or 0
        return (
            f"{data.id}: {data.record.get('cve')} on {assets} "
            f"{'asset' if assets == 1 else 'assets'}"
        )
    if data.kind == BlockKind.GROUPS.value:
        return (
            f"{data.id}: {len(data.groups)} groups over {data.total}{plus} "
            f"{noun(data.dimension, data.total)}"
        )
    return f"{data.id}: {data.total}{plus} {noun(data.dimension, data.total)}"
