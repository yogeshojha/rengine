from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.asset_query import (
    EVIDENCE_LABELS,
    HOST_QUERY,
    SNIPPET_LENGTH,
    SNIPPET_RADIUS,
    Op,
)
from shared.models.asset_query import MatchEvidence
from shared.models.subdomain import Subdomain

from .ast import Node, positive_compares, positive_terms

MAX_PROBES = 4
_WHITESPACE = re.compile(r"\s+")
_ASSET_COLUMNS = ("body", "header", "path", "redirect", "cert")

_ASSET_SQL = text(
    """
    SELECT host,
           max(CASE WHEN response_body ILIKE :pattern THEN
                 substring(response_body
                   from greatest(1, position(lower(:needle) in lower(response_body)) - :radius)
                   for :width) END) AS body,
           max(CASE WHEN raw_response_header ILIKE :pattern THEN
                 substring(raw_response_header
                   from greatest(1, position(lower(:needle) in lower(raw_response_header)) - :radius)
                   for :width) END) AS header,
           max(CASE WHEN path ILIKE :pattern THEN path END) AS path,
           max(CASE WHEN location ILIKE :pattern THEN location END) AS redirect,
           max(COALESCE(
                 CASE WHEN tls_subject_cn ILIKE :pattern THEN tls_subject_cn END,
                 CASE WHEN tls_issuer ILIKE :pattern THEN tls_issuer END,
                 (SELECT v FROM jsonb_array_elements_text(cast(tls_sans AS jsonb)) v
                   WHERE v ILIKE :pattern LIMIT 1))) AS cert
    FROM http_assets
    WHERE scan_id = :scan_id AND host = ANY(:hosts)
    GROUP BY host
    """
).bindparams(bindparam("hosts", expanding=False))


@dataclass(frozen=True)
class Probe:
    term: str
    field: str | None


def probes(node: Node | None) -> list[Probe]:
    found: list[Probe] = []
    for term in positive_terms(node):
        if term.value:
            found.append(Probe(term.value, None))
    for cmp in positive_compares(node):
        spec = HOST_QUERY.by_name.get(cmp.name)
        if spec is None or spec.evidence is None or cmp.op not in (Op.MATCH, Op.EQ):
            continue
        for value in cmp.values:
            if value:
                found.append(Probe(value, spec.evidence))
    return found[:MAX_PROBES]


def _snippet(raw: str | None, term: str) -> str | None:
    if not raw:
        return None
    collapsed = _WHITESPACE.sub(" ", raw).strip()
    if not collapsed:
        return None
    lead = "…" if not collapsed.lower().startswith(term.lower()[:8]) else ""
    return f"{lead}{collapsed[:SNIPPET_LENGTH]}…"


def _add(bucket: dict[str, MatchEvidence], field: str, term: str, snippet: str | None):
    key = f"{field}:{term.lower()}"
    if key in bucket:
        return
    bucket[key] = MatchEvidence(
        field=field,
        label=EVIDENCE_LABELS.get(field, field),
        term=term,
        snippet=snippet,
    )


def _row_values(row: Subdomain) -> dict[str, list[str]]:
    return {
        "host": [row.name],
        "url": [v for v in (row.final_url, row.http_url) if v],
        "title": [row.page_title] if row.page_title else [],
        "server": [row.webserver] if row.webserver else [],
        "tech": list(row.tech or []),
        "ip": list(row.resolved_ips or []),
        "cname": [row.cname] if row.cname else [],
        "org": [row.asn_org] if row.asn_org else [],
        "cdn": [row.cdn_name] if row.cdn_name else [],
        "waf": [row.waf] if row.waf else [],
        "source": list(row.sources or []),
        "content_type": [row.content_type] if row.content_type else [],
        "favicon": [row.favicon_hash] if row.favicon_hash else [],
    }


async def collect(
    session: AsyncSession,
    scan_id: UUID,
    rows: list[Subdomain],
    node: Node | None,
) -> dict[UUID, list[MatchEvidence]]:
    found = probes(node)
    if not found or not rows:
        return {}
    buckets: dict[UUID, dict[str, MatchEvidence]] = {row.id: {} for row in rows}
    for row in rows:
        values = _row_values(row)
        for probe in found:
            needle = probe.term.lower()
            for field, candidates in values.items():
                if probe.field is not None and probe.field != field:
                    continue
                hit = next((c for c in candidates if needle in c.lower()), None)
                if hit is not None:
                    _add(buckets[row.id], field, probe.term, hit)
    await _asset_evidence(session, scan_id, rows, found, buckets)
    return {rid: list(items.values()) for rid, items in buckets.items() if items}


async def _asset_evidence(
    session: AsyncSession,
    scan_id: UUID,
    rows: list[Subdomain],
    found: list[Probe],
    buckets: dict[UUID, dict[str, MatchEvidence]],
) -> None:
    wanted = [p for p in found if p.field is None or p.field in _ASSET_COLUMNS]
    if not wanted:
        return
    by_host: dict[str, list[Subdomain]] = {}
    for row in rows:
        by_host.setdefault(row.name, []).append(row)
    hosts = list(by_host)
    for probe in wanted:
        pattern = f"%{probe.term}%"
        result = await session.execute(
            _ASSET_SQL,
            {
                "pattern": pattern,
                "needle": probe.term,
                "radius": SNIPPET_RADIUS,
                "width": SNIPPET_LENGTH,
                "scan_id": str(scan_id),
                "hosts": hosts,
            },
        )
        for record in result.mappings():
            for field in _ASSET_COLUMNS:
                if probe.field is not None and probe.field != field:
                    continue
                value = record[field]
                if not value:
                    continue
                snippet = _snippet(value, probe.term)
                for row in by_host.get(record["host"], []):
                    _add(buckets[row.id], field, probe.term, snippet)
