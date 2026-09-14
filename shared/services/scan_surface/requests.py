"""Request and directory items: what a fuzzer and the exposure checks are handed."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import select

from shared.definitions.endpoints import EndpointClass
from shared.definitions.scan_surface import (
    BASE_MAX_DEPTH,
    MAX_BASES_PER_ORIGIN,
    MAX_REQUESTS,
    MAX_REQUESTS_PER_ORIGIN,
    SurfaceClass,
    Tier,
)
from shared.models.endpoint import Endpoint
from shared.models.scan_surface import ScanSurfaceItem
from shared.services.scan_surface.plan import SurfaceItem, SurfacePlan
from shared.services.scope_filter import matches_any

# endpoint classes a fuzzer can act on
FUZZABLE_CLASSES: frozenset[str] = frozenset(
    {
        EndpointClass.PAGE.value,
        EndpointClass.API.value,
        EndpointClass.DATA.value,
        EndpointClass.OTHER.value,
    }
)
_OK = 200
_GONE = frozenset({404, 410})
_LIVE_DIR = frozenset(range(200, 400)) | frozenset({401, 403})


@dataclass
class Origin:
    """One origin the root plan settled on, with the web assets it stands for."""

    item: SurfaceItem
    members: list[SurfaceItem]

    @property
    def value(self) -> str:
        return self.item.value


def origins(session, scan_id: uuid.UUID) -> dict[tuple[str, str, int], Origin]:
    """Every root the plan kept, keyed by (scheme, host, port), members folded onto their origin."""
    rows = session.execute(
        select(ScanSurfaceItem).where(
            ScanSurfaceItem.scan_id == scan_id,
            ScanSurfaceItem.class_ == SurfaceClass.ROOT.value,
        )
    ).scalars()
    items: dict[uuid.UUID, SurfaceItem] = {}
    listed: list[ScanSurfaceItem] = []
    for row in rows:
        listed.append(row)
        items[row.http_asset_id] = SurfaceItem(
            id=row.id,
            class_=row.class_,
            value=row.value,
            host=row.host,
            port=row.port,
            scheme=row.scheme,
            asset_id=row.http_asset_id,
            cluster_id=row.cluster_id,
            representative_id=row.representative_id,
            rank=row.rank,
            guarded=bool(row.guarded),
            tags=list(row.tags or []),
        )
    found: dict[tuple[str, str, int], Origin] = {}
    by_asset: dict[uuid.UUID, Origin] = {}
    for row in listed:
        if row.drop_reason is not None and row.representative_id is None:
            continue
        if row.representative_id is None:
            origin = Origin(item=items[row.http_asset_id], members=[])
            by_asset[row.http_asset_id] = origin
    for row in listed:
        if row.representative_id is None:
            continue
        origin = by_asset.get(row.representative_id)
        if origin is None:
            continue
        origin.members.append(items[row.http_asset_id])
        found[(row.scheme or "", (row.host or "").lower(), int(row.port or 0))] = origin
    for origin in by_asset.values():
        item = origin.item
        found[(item.scheme or "", (item.host or "").lower(), int(item.port or 0))] = (
            origin
        )
    return found


def _key(
    scheme: str | None, host: str | None, port: int | None
) -> tuple[str, str, int]:
    return ((scheme or "").lower(), (host or "").lower(), int(port or 0))


def _rewrite(origin_value: str, url: str) -> str:
    """The same path and query on the origin's own spelling."""
    parsed = urlsplit(url)
    tail = parsed.path or "/"
    if parsed.query:
        tail = f"{tail}?{parsed.query}"
    return f"{origin_value}{tail}"


def _request_item(origin: Origin, row: Endpoint) -> SurfaceItem:
    return SurfaceItem(
        id=uuid.uuid4(),
        class_=SurfaceClass.REQUEST.value,
        value=_rewrite(origin.value, row.url)[:2000],
        host=origin.item.host,
        port=origin.item.port,
        scheme=origin.item.scheme,
        asset_id=origin.item.asset_id,
        endpoint_id=row.id,
        cluster_id=origin.item.cluster_id,
        rank=origin.item.rank,
        guarded=origin.item.guarded,
        tiers_planned=[Tier.DAST.value],
    )


def _better(candidate: Endpoint, current: Endpoint | None) -> bool:
    if current is None:
        return True
    ok = (
        candidate.status_code == _OK,
        int(candidate.variants or 1),
        -len(candidate.url),
    )
    now = (current.status_code == _OK, int(current.variants or 1), -len(current.url))
    return ok > now


def build_requests(
    session,
    *,
    scan_id: uuid.UUID,
    resolved,
    max_per_origin: int = MAX_REQUESTS_PER_ORIGIN,
    max_total: int = MAX_REQUESTS,
    bases: bool = False,
    max_bases_per_origin: int = MAX_BASES_PER_ORIGIN,
    base_depth: int = BASE_MAX_DEPTH,
) -> SurfacePlan:
    """One request per origin, shape, parameter set and method; one directory per origin and path."""
    excluded_paths = list(resolved.excluded_paths or [])
    known = origins(session, scan_id)
    plan = SurfacePlan()
    plan.equivalents = {o.value: o.members for o in known.values()}
    if not known:
        return plan

    rows = session.execute(
        select(Endpoint)
        .where(
            Endpoint.scan_id == scan_id,
            Endpoint.is_probed.is_(True),
            Endpoint.status_code.is_not(None),
        )
        .order_by(Endpoint.host, Endpoint.path, Endpoint.url)
    ).scalars()

    chosen: dict[tuple, tuple[Origin, Endpoint]] = {}
    dirs: dict[tuple[str, str], Origin] = {}
    for row in rows:
        origin = known.get(_key(row.scheme, row.host, row.port))
        if origin is None:
            continue
        if excluded_paths and matches_any(row.path or "/", excluded_paths):
            continue
        status = int(row.status_code or 0)
        if (
            row.param_count > 0
            and status not in _GONE
            and row.endpoint_class in FUZZABLE_CLASSES
        ):
            method = sorted(row.methods or ["GET"])[0]
            key = (origin.value, row.shape, tuple(sorted(row.params or [])), method)
            current = chosen.get(key)
            if _better(row, current[1] if current else None):
                chosen[key] = (origin, row)
        if (
            bases
            and status in _LIVE_DIR
            and row.dir_path
            and row.dir_path != "/"
            and row.dir_path.strip("/").count("/") < base_depth
        ):
            dirs.setdefault((origin.value, row.dir_path), origin)

    per_origin: dict[str, int] = {}
    ranked = sorted(chosen.values(), key=lambda pair: (-pair[0].item.rank, pair[1].url))
    for origin, row in ranked:
        if len(plan.requests) >= max_total:
            break
        taken = per_origin.get(origin.value, 0)
        if taken >= max_per_origin:
            continue
        per_origin[origin.value] = taken + 1
        plan.requests.append(_request_item(origin, row))

    per_origin = {}
    for (origin_value, dir_path), origin in sorted(
        dirs.items(), key=lambda kv: (-kv[1].item.rank, kv[0])
    ):
        taken = per_origin.get(origin_value, 0)
        if taken >= max_bases_per_origin:
            continue
        per_origin[origin_value] = taken + 1
        path = dir_path if dir_path.endswith("/") else f"{dir_path}/"
        plan.bases.append(
            SurfaceItem(
                id=uuid.uuid4(),
                class_=SurfaceClass.BASE.value,
                value=f"{origin_value}{path}"[:2000],
                host=origin.item.host,
                port=origin.item.port,
                scheme=origin.item.scheme,
                asset_id=origin.item.asset_id,
                cluster_id=origin.item.cluster_id,
                rank=origin.item.rank,
                guarded=origin.item.guarded,
                tiers_planned=[Tier.BASES.value],
            )
        )
    return plan


def by_origin(items: Iterable[SurfaceItem]) -> list[list[SurfaceItem]]:
    """Items grouped per origin, in rank order, so one invocation keeps a host together."""
    groups: dict[str, list[SurfaceItem]] = {}
    for item in items:
        groups.setdefault(
            (item.asset_id and str(item.asset_id)) or item.value, []
        ).append(item)
    return sorted(groups.values(), key=lambda g: (-g[0].rank, g[0].value))


__all__ = ["FUZZABLE_CLASSES", "Origin", "build_requests", "by_origin", "origins"]
