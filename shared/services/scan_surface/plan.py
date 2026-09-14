"""Build the scan surface plan for one scan and keep it in `scan_surface_items`."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import cast, delete, func, literal_column, select, true, update
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.scan_surface import (
    DropReason,
    SurfaceClass,
    SurfaceState,
    Tier,
)
from shared.definitions.vulnerabilities import CoverageStatus, TemplateOrigin
from shared.definitions.vulnerabilities import Surface as SurfaceMode
from shared.logging import get_logger
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.scan_surface import ScanSurfaceItem
from shared.models.subdomain import Subdomain
from shared.models.vuln_template import VulnTemplate
from shared.services.scan_surface.cluster import (
    Cluster,
    RootCandidate,
    cluster_roots,
)
from shared.services.scan_surface.normalize import parse_root, service_value
from shared.services.scan_surface.rank import base_rank, cluster_rank
from shared.services.scan_surface.tech import host_tags
from shared.services.scope_filter import ip_excluded, matches_any
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

_INSERT_CHUNK = 1000
_ROOT_PATH = "/"
_RAN = frozenset(
    {
        CoverageStatus.COMPLETED.value,
        CoverageStatus.PARTIAL.value,
        CoverageStatus.FAILED.value,
    }
)


@dataclass
class SurfaceItem:
    """One planned input, with the members it stands for."""

    id: uuid.UUID
    class_: str
    value: str
    host: str | None = None
    port: int | None = None
    scheme: str | None = None
    asset_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None
    port_id: uuid.UUID | None = None
    subdomain_id: uuid.UUID | None = None
    cluster_id: uuid.UUID | None = None
    representative_id: uuid.UUID | None = None
    signals: list[str] = field(default_factory=list)
    members: list[SurfaceItem] = field(default_factory=list)
    rank: float = 0.0
    guarded: bool = False
    tags: list[str] = field(default_factory=list)
    unmapped_tech: list[str] = field(default_factory=list)
    tiers_planned: list[str] = field(default_factory=list)
    drop_reason: str | None = None
    state: str = SurfaceState.PLANNED.value
    note: str | None = None

    @property
    def size(self) -> int:
        return 1 + len(self.members)


@dataclass
class SurfacePlan:
    roots: list[SurfaceItem] = field(default_factory=list)
    names: list[SurfaceItem] = field(default_factory=list)
    services: list[SurfaceItem] = field(default_factory=list)
    requests: list[SurfaceItem] = field(default_factory=list)
    bases: list[SurfaceItem] = field(default_factory=list)
    dropped: list[SurfaceItem] = field(default_factory=list)
    unmapped_tech: Counter = field(default_factory=Counter)
    # origin root value -> the web assets it stands for
    equivalents: dict[str, list[SurfaceItem]] = field(default_factory=dict)

    @property
    def members(self) -> list[SurfaceItem]:
        return [m for root in self.roots for m in root.members]

    @property
    def every_root(self) -> list[SurfaceItem]:
        """Representatives and members, the tier that runs on all web assets."""
        out: list[SurfaceItem] = []
        for root in self.roots:
            out.append(root)
            out.extend(root.members)
        return out

    def targets(self) -> list[str]:
        return [
            item.value
            for item in (
                *self.roots,
                *self.services,
                *self.names,
                *self.requests,
                *self.bases,
            )
        ]

    def is_empty(self) -> bool:
        return not (
            self.roots or self.services or self.names or self.requests or self.bases
        )

    def members_of(self, root_value: str) -> list[SurfaceItem]:
        if self.equivalents:
            return self.equivalents.get(root_value, [])
        for root in self.roots:
            if root.value == root_value:
                return root.members
        return []


# ---------- reads ----------


def library_tags(session: Session) -> frozenset[str]:
    """Every tag the check library carries."""
    tag = func.jsonb_array_elements_text(cast(VulnTemplate.tags, JSONB)).table_valued(
        "value"
    )
    rows = session.execute(
        select(tag.c.value)
        .select_from(VulnTemplate)
        .join(tag, true())
        .where(VulnTemplate.origin == TemplateOrigin.OFFICIAL.value)
        .distinct()
    )
    return frozenset(str(v).lower() for (v,) in rows if v)


def covered_before(
    session: Session, target_id: uuid.UUID, scan_id: uuid.UUID
) -> set[str]:
    """Roots an earlier scan of this target swept at the universal tier."""
    rows = session.execute(
        select(ScanSurfaceItem.value)
        .where(
            ScanSurfaceItem.target_id == target_id,
            ScanSurfaceItem.scan_id != scan_id,
            ScanSurfaceItem.class_ == SurfaceClass.ROOT.value,
            cast(ScanSurfaceItem.tiers_done, JSONB).has_key(Tier.UNIVERSAL.value),
        )
        .distinct()
    )
    return {str(v) for (v,) in rows}


def _endpoint_counts(session: Session, scan_id: uuid.UUID) -> dict[tuple, int]:
    rows = session.execute(
        select(Endpoint.scheme, Endpoint.host, Endpoint.port, func.count())
        .where(Endpoint.scan_id == scan_id)
        .group_by(Endpoint.scheme, Endpoint.host, Endpoint.port)
    )
    return {
        ((scheme or "").lower(), (host or "").lower(), int(port or 0)): int(count)
        for scheme, host, port, count in rows
    }


def _root_candidates(
    session: Session,
    scan_id: uuid.UUID,
    *,
    excluded_hosts: list[str],
    excluded_paths: list[str],
    excluded_ips: list[str],
    vocabulary: frozenset[str],
    covered: set[str],
    unmapped: Counter,
) -> tuple[list[RootCandidate], list[SurfaceItem]]:
    counts = _endpoint_counts(session, scan_id)
    root_excluded = matches_any(_ROOT_PATH, excluded_paths) if excluded_paths else False
    seen: dict[str, RootCandidate] = {}
    candidates: list[RootCandidate] = []
    dropped: list[SurfaceItem] = []
    rows = session.execute(
        select(HttpAsset, literal_column("http_assets.software"))
        .where(HttpAsset.scan_id == scan_id)
        .order_by(HttpAsset.url)
    )
    for row, software in rows:
        root = parse_root(row.url, scheme=row.scheme, port=row.port)
        if root is None:
            continue
        item = SurfaceItem(
            id=uuid.uuid4(),
            class_=SurfaceClass.ROOT.value,
            value=root.value,
            host=root.host,
            port=root.port,
            scheme=root.scheme,
            asset_id=row.id,
            state=SurfaceState.NOT_SCANNED.value,
        )
        if (
            matches_any(root.host, excluded_hosts)
            or (row.ip and ip_excluded(row.ip, excluded_ips))
            or root_excluded
        ):
            item.drop_reason = DropReason.OUT_OF_SCOPE.value
            dropped.append(item)
            continue
        if row.status_code is None:
            item.drop_reason = DropReason.NO_ANSWER.value
            dropped.append(item)
            continue
        if root.value in seen:
            item.drop_reason = DropReason.DUPLICATE_SPELLING.value
            item.representative_id = seen[root.value].asset_id
            dropped.append(item)
            continue
        tags, missing = host_tags(
            tech=list(row.tech or []),
            cpe=list(row.cpe or []),
            webserver=row.webserver,
            software=list(software or []),
            vocabulary=vocabulary,
        )
        unmapped.update(missing)
        candidate = RootCandidate(
            asset_id=row.id,
            value=root.value,
            scheme=root.scheme,
            host=root.host,
            port=root.port,
            status=row.status_code,
            title=row.title,
            content_hash=row.content_hash,
            content_length=row.content_length,
            words=row.words,
            lines=row.lines,
            webserver=row.webserver,
            ip=row.ip,
            a_records=list(row.a_records or []),
            aaaa_records=list(row.aaaa_records or []),
            is_cdn=bool(row.is_cdn),
            waf=row.waf,
            tls_fingerprint=row.tls_fingerprint,
            favicon_hash=row.favicon_hash,
            not_found=row.not_found,
            tech=list(row.tech or []),
            cpe=list(row.cpe or []),
            software=list(software or []),
            endpoints=counts.get((root.scheme, root.host, root.port), 0),
            covered_before=root.value in covered,
            tags=tags,
            unmapped_tech=missing,
        )
        candidate.rank = base_rank(candidate)
        seen[root.value] = candidate
        candidates.append(candidate)
    return candidates, dropped


def _item_of(candidate: RootCandidate, cluster: Cluster) -> SurfaceItem:
    return SurfaceItem(
        id=uuid.uuid4(),
        class_=SurfaceClass.ROOT.value,
        value=candidate.value,
        host=candidate.host,
        port=candidate.port,
        scheme=candidate.scheme,
        asset_id=candidate.asset_id,
        cluster_id=cluster.id,
        guarded=candidate.guarded,
        tags=list(candidate.tags),
        unmapped_tech=list(candidate.unmapped_tech),
    )


def _service_items(
    session: Session,
    scan_id: uuid.UUID,
    roots: list[SurfaceItem],
    *,
    mode: str,
    excluded_ips: list[str],
) -> list[SurfaceItem]:
    items: list[SurfaceItem] = []
    seen: set[str] = set()
    for root in roots:
        if root.scheme != "https" or not root.host or not root.port:
            continue
        value = service_value(root.host, root.port)
        if value in seen:
            continue
        seen.add(value)
        items.append(
            SurfaceItem(
                id=uuid.uuid4(),
                class_=SurfaceClass.SERVICE.value,
                value=value,
                host=root.host,
                port=root.port,
                scheme=root.scheme,
                asset_id=root.asset_id,
                guarded=root.guarded,
                rank=root.rank,
                tiers_planned=[Tier.SERVICES.value],
            )
        )
    if mode not in (SurfaceMode.SERVICES.value, SurfaceMode.FULL.value):
        return items
    rows = session.execute(
        select(Port.id, Port.ip, Port.number, Port.tls)
        .where(Port.scan_id == scan_id, Port.is_http.is_(False))
        .order_by(Port.ip, Port.number)
    )
    for port_id, ip, number, _tls in rows:
        if ip_excluded(ip, excluded_ips):
            continue
        value = service_value(ip, number)
        if value in seen:
            continue
        seen.add(value)
        items.append(
            SurfaceItem(
                id=uuid.uuid4(),
                class_=SurfaceClass.SERVICE.value,
                value=value,
                host=ip,
                port=int(number),
                port_id=port_id,
                tiers_planned=[Tier.SERVICES.value],
            )
        )
    return items


def _name_items(
    session: Session,
    scan_id: uuid.UUID,
    *,
    excluded_hosts: list[str],
) -> list[SurfaceItem]:
    items: list[SurfaceItem] = []
    rows = session.execute(
        select(Subdomain.id, Subdomain.name, Subdomain.is_cdn, Subdomain.waf)
        .where(
            Subdomain.scan_id == scan_id,
            Subdomain.is_excluded.is_(False),
            func.jsonb_array_length(cast(Subdomain.resolved_ips, JSONB)) > 0,
        )
        .order_by(Subdomain.name)
    )
    for subdomain_id, name, is_cdn, waf in rows:
        host = (name or "").lower()
        if not host or matches_any(host, excluded_hosts):
            continue
        items.append(
            SurfaceItem(
                id=uuid.uuid4(),
                class_=SurfaceClass.NAME.value,
                value=host,
                host=host,
                subdomain_id=subdomain_id,
                guarded=bool(is_cdn or waf),
                tiers_planned=[Tier.NAMES.value],
            )
        )
    return items


# ---------- build ----------


def build(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    resolved,
    mode: str,
    max_targets: int,
    root_tiers: Iterable[str],
) -> SurfacePlan:
    """Read what the scan found and decide what the scanner is handed."""
    excluded_hosts = list(resolved.excluded_subdomains or [])
    excluded_paths = list(resolved.excluded_paths or [])
    excluded_ips = list(resolved.excluded_ips or [])
    plan = SurfacePlan()
    vocabulary = library_tags(session)
    covered = covered_before(session, target_id, scan_id)

    candidates, dropped = _root_candidates(
        session,
        scan_id,
        excluded_hosts=excluded_hosts,
        excluded_paths=excluded_paths,
        excluded_ips=excluded_ips,
        vocabulary=vocabulary,
        covered=covered,
        unmapped=plan.unmapped_tech,
    )
    plan.dropped.extend(dropped)

    tiers = list(root_tiers)
    representatives: list[SurfaceItem] = []
    for cluster in cluster_roots(candidates):
        rep = _item_of(cluster.representative, cluster)
        rep.rank = cluster_rank(cluster.representative.rank, cluster.size)
        rep.tiers_planned = list(tiers)
        for member in cluster.members:
            item = _item_of(member, cluster)
            item.representative_id = rep.asset_id
            item.signals = list(cluster.signals.get(member.asset_id, []))
            item.state = SurfaceState.COVERED.value
            item.drop_reason = DropReason.COVERED_BY_ORIGIN.value
            item.rank = member.rank
            item.tiers_planned = (
                [Tier.ONE_REQUEST.value] if Tier.ONE_REQUEST.value in tiers else []
            )
            rep.members.append(item)
        representatives.append(rep)
    representatives.sort(key=lambda item: (-item.rank, item.value))

    kept = representatives[: max(0, max_targets)]
    for item in representatives[len(kept) :]:
        for row in (item, *item.members):
            row.drop_reason = DropReason.OVER_CAP.value
            row.state = SurfaceState.NOT_SCANNED.value
            row.tiers_planned = []
            plan.dropped.append(row)
    plan.roots = kept

    plan.services = _service_items(
        session, scan_id, kept, mode=mode, excluded_ips=excluded_ips
    )
    if mode == SurfaceMode.FULL.value:
        plan.names = _name_items(session, scan_id, excluded_hosts=excluded_hosts)
    return plan


# ---------- writes ----------


def _row(item: SurfaceItem, *, scan_id, target_id, project_id, now) -> dict:
    return {
        "id": item.id,
        "scan_id": scan_id,
        "target_id": target_id,
        "project_id": project_id,
        "class": item.class_,
        "value": item.value[:2000],
        "host": item.host,
        "port": item.port,
        "scheme": item.scheme,
        "http_asset_id": item.asset_id,
        "endpoint_id": item.endpoint_id,
        "port_id": item.port_id,
        "subdomain_id": item.subdomain_id,
        "cluster_id": item.cluster_id,
        "representative_id": item.representative_id,
        "cluster_signals": list(item.signals),
        "members": item.size,
        "drop_reason": item.drop_reason,
        "rank": item.rank,
        "batch": None,
        "guarded": item.guarded,
        "tags": list(item.tags),
        "unmapped_tech": list(item.unmapped_tech),
        "tiers_planned": list(item.tiers_planned),
        "tiers_done": {},
        "state": item.state,
        "note": item.note,
        "created_at": now,
    }


def write(
    session: Session,
    plan: SurfacePlan,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    classes: Iterable[str] = (
        SurfaceClass.ROOT.value,
        SurfaceClass.NAME.value,
        SurfaceClass.SERVICE.value,
    ),
) -> int:
    """Replace this scan's rows for the given classes with the plan."""
    now = utc_now()
    listed = list(classes)
    session.execute(
        delete(ScanSurfaceItem).where(
            ScanSurfaceItem.scan_id == scan_id, ScanSurfaceItem.class_.in_(listed)
        )
    )
    items: list[SurfaceItem] = [
        *plan.every_root,
        *plan.services,
        *plan.names,
        *plan.requests,
        *plan.bases,
        *plan.dropped,
    ]
    rows = [
        _row(item, scan_id=scan_id, target_id=target_id, project_id=project_id, now=now)
        for item in items
        if item.class_ in listed
    ]
    for start in range(0, len(rows), _INSERT_CHUNK):
        session.execute(
            ScanSurfaceItem.__table__.insert(), rows[start : start + _INSERT_CHUNK]
        )
    session.commit()
    return len(rows)


def mark(
    session: Session,
    item_ids: Iterable[uuid.UUID],
    *,
    tier: str,
    status: str,
    batch: int | None = None,
) -> int:
    """Record one tier's outcome on the items a batch carried."""
    ids = list(item_ids)
    if not ids:
        return 0
    stamp = f"{status}@{utc_now().isoformat()}"
    values: dict = {
        "tiers_done": cast(ScanSurfaceItem.tiers_done, JSONB).concat(
            cast({tier: stamp}, JSONB)
        )
    }
    if batch is not None:
        values["batch"] = batch
    updated = 0
    for start in range(0, len(ids), _INSERT_CHUNK):
        updated += session.execute(
            update(ScanSurfaceItem)
            .where(ScanSurfaceItem.id.in_(ids[start : start + _INSERT_CHUNK]))
            .values(**values)
        ).rowcount
    session.commit()
    return updated


def split_members(session: Session, item_ids: Iterable[uuid.UUID], note: str) -> int:
    """A member that did not reproduce its origin's finding stands on its own."""
    ids = list(item_ids)
    if not ids:
        return 0
    updated = session.execute(
        update(ScanSurfaceItem)
        .where(ScanSurfaceItem.id.in_(ids))
        .values(
            drop_reason=None,
            state=SurfaceState.PARTIAL.value,
            note=note[:500],
        )
    ).rowcount
    session.commit()
    return updated


def settle(session: Session, scan_id: uuid.UUID) -> None:
    """Decide each representative's state from the tiers that ran."""
    rows = session.execute(
        select(
            ScanSurfaceItem.id,
            ScanSurfaceItem.tiers_planned,
            ScanSurfaceItem.tiers_done,
            ScanSurfaceItem.state,
        ).where(
            ScanSurfaceItem.scan_id == scan_id,
            ScanSurfaceItem.drop_reason.is_(None),
            ScanSurfaceItem.note.is_(None),
        )
    ).all()
    by_state: dict[str, list[uuid.UUID]] = {}
    for item_id, planned_raw, done_raw, _state in rows:
        planned = list(planned_raw or [])
        done = dict(done_raw or {})
        outcomes = {t: str(done.get(t, "")).split("@", 1)[0] for t in planned}
        finished = [
            t for t, o in outcomes.items() if o == CoverageStatus.COMPLETED.value
        ]
        ran = [t for t, o in outcomes.items() if o in _RAN]
        if not planned or not ran:
            state = SurfaceState.NOT_SCANNED.value
        elif len(finished) == len(planned):
            state = SurfaceState.SCANNED.value
        else:
            state = SurfaceState.PARTIAL.value
        by_state.setdefault(state, []).append(item_id)
    for state, ids in by_state.items():
        for start in range(0, len(ids), _INSERT_CHUNK):
            session.execute(
                update(ScanSurfaceItem)
                .where(ScanSurfaceItem.id.in_(ids[start : start + _INSERT_CHUNK]))
                .values(state=state)
            )
    session.commit()


__all__ = [
    "SurfaceItem",
    "SurfacePlan",
    "build",
    "covered_before",
    "library_tags",
    "mark",
    "settle",
    "split_members",
    "write",
]
