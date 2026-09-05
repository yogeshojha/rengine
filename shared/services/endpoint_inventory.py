"""The only writer of `endpoints`: merges observations by structural signature, never losing a source."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from shared.definitions.endpoints import (
    MAX_PARAM_SAMPLES,
    EndpointSource,
    classify,
    coerce_source,
    interests_for,
    parse_url,
    source_rank,
)
from shared.logging import get_logger
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

_BATCH = 500
_CONSTRAINT = "uq_endpoint_scan_signature"


@dataclass
class EndpointObservation:
    """One provider's sighting of one URL."""

    url: str
    found_on: str | None = None
    detail: str | None = None
    observed_at: datetime | None = None
    methods: list[str] = field(default_factory=list)
    # probe results, only meaningful when the provider actually made the request
    is_probed: bool = False
    status_code: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    title: str | None = None
    words: int | None = None
    lines: int | None = None
    response_time: float | None = None
    redirect_location: str | None = None
    content_hash: str | None = None
    tech: list[str] = field(default_factory=list)


@dataclass
class UpsertResult:
    created: int = 0
    updated: int = 0
    rejected: int = 0
    seen: int = 0


@dataclass
class AssetIndex:
    """The web assets and hostnames this scan already recorded, keyed the way a URL names them."""

    assets: dict[tuple[str, int], uuid.UUID]
    subdomains: dict[str, uuid.UUID]


def build_index(session: Session, scan_id: uuid.UUID) -> AssetIndex:
    assets: dict[tuple[str, int], uuid.UUID] = {}
    for row in session.execute(
        select(HttpAsset.id, HttpAsset.host, HttpAsset.port).where(
            HttpAsset.scan_id == scan_id
        )
    ):
        assets.setdefault((row.host.lower(), int(row.port or 0)), row.id)

    subdomains: dict[str, uuid.UUID] = {}
    for row in session.execute(
        select(Subdomain.id, Subdomain.name).where(Subdomain.scan_id == scan_id)
    ):
        subdomains.setdefault(row.name.lower(), row.id)

    return AssetIndex(assets=assets, subdomains=subdomains)


@dataclass
class _Merged:
    """One signature's worth of observations, folded before the database is touched."""

    signature: str
    url: str
    scheme: str
    host: str
    port: int
    path: str
    dir_path: str
    filename: str | None
    extension: str | None
    depth: int
    params: list[str]
    samples: list[dict]
    more_variants: bool = False
    methods: set[str] = field(default_factory=set)
    found_on: str | None = None
    detail: str | None = None
    observed_at: datetime | None = None
    is_probed: bool = False
    status_code: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    title: str | None = None
    words: int | None = None
    lines: int | None = None
    response_time: float | None = None
    redirect_location: str | None = None
    content_hash: str | None = None
    tech: list[str] = field(default_factory=list)

    def add_sample(self, values: dict[str, str]) -> None:
        if not values or values in self.samples:
            return
        if len(self.samples) >= MAX_PARAM_SAMPLES:
            self.more_variants = True
            return
        self.samples.append(values)

    def absorb(self, obs: EndpointObservation) -> None:
        self.methods.update(m.upper() for m in obs.methods or () if m)
        if self.found_on is None:
            self.found_on = obs.found_on
        if self.detail is None:
            self.detail = obs.detail
        if obs.observed_at and (
            self.observed_at is None or obs.observed_at < self.observed_at
        ):
            self.observed_at = obs.observed_at
        if not obs.is_probed:
            return
        # coalesce, never overwrite: a crawler reports a status and a title but no words,
        # lines or hash, and must not erase what a full probe already recorded
        self.is_probed = True
        for field_ in (
            "status_code",
            "content_type",
            "content_length",
            "title",
            "words",
            "lines",
            "response_time",
            "redirect_location",
            "content_hash",
        ):
            value = getattr(obs, field_)
            if value is not None:
                setattr(self, field_, value)
        if obs.tech:
            self.tech = list(obs.tech)


def _fold(
    observations: list[EndpointObservation], default_scheme: str
) -> tuple[dict[str, _Merged], int]:
    folded: dict[str, _Merged] = {}
    rejected = 0
    for obs in observations:
        parsed = parse_url(obs.url, default_scheme=default_scheme)
        if parsed is None:
            rejected += 1
            continue
        merged = folded.get(parsed.signature)
        if merged is None:
            merged = _Merged(
                signature=parsed.signature,
                url=parsed.url,
                scheme=parsed.scheme,
                host=parsed.host,
                port=parsed.port,
                path=parsed.path,
                dir_path=parsed.dir_path,
                filename=parsed.filename,
                extension=parsed.extension,
                depth=parsed.depth,
                params=list(parsed.params),
                samples=[],
            )
            folded[parsed.signature] = merged
        merged.add_sample(dict(parsed.param_values))
        merged.absorb(obs)
    return folded, rejected


def _row(
    merged: _Merged,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    source: str,
    index: AssetIndex,
    now: datetime,
) -> dict:
    interest = interests_for(merged.path, merged.params)
    return {
        "id": uuid.uuid4(),
        "scan_id": scan_id,
        "target_id": target_id,
        "project_id": project_id,
        "signature": merged.signature,
        "url": merged.url,
        "host": merged.host,
        "port": merged.port,
        "scheme": merged.scheme,
        "path": merged.path,
        "dir_path": merged.dir_path,
        "filename": merged.filename,
        "extension": merged.extension,
        "depth": merged.depth,
        "params": merged.params,
        "param_count": len(merged.params),
        "param_samples": merged.samples,
        "variants": max(len(merged.samples), 1),
        "more_variants": merged.more_variants,
        "methods": sorted(merged.methods),
        "sources": [source],
        "primary_source": source,
        "discovery": {source: _evidence(merged, now)},
        "found_on": merged.found_on,
        "is_probed": merged.is_probed,
        "status_code": merged.status_code,
        "content_type": merged.content_type,
        "content_length": merged.content_length,
        "title": merged.title,
        "words": merged.words,
        "lines": merged.lines,
        "response_time": merged.response_time,
        "redirect_location": merged.redirect_location,
        "content_hash": merged.content_hash,
        "tech": merged.tech,
        "endpoint_class": classify(merged.path, merged.extension, merged.content_type),
        "interest": interest,
        "http_asset_id": index.assets.get((merged.host, merged.port)),
        "subdomain_id": index.subdomains.get(merged.host),
        "archive_last_seen": merged.observed_at,
        "discovered_at": now,
        "created_at": now,
    }


def _evidence(merged: _Merged, now: datetime) -> dict:
    entry: dict = {"at": (merged.observed_at or now).isoformat()}
    if merged.detail:
        entry["detail"] = merged.detail
    if merged.found_on:
        entry["found_on"] = merged.found_on
    return entry


def _changes(row: Endpoint, merged: _Merged, source: str, now: datetime) -> dict:
    """What this observation adds to a row another source already wrote."""
    changed: dict = {}

    sources = list(row.sources or [])
    if source not in sources:
        sources.append(source)
        changed["sources"] = sorted(sources, key=lambda s: (-source_rank(s), s))
    if source_rank(source) > source_rank(row.primary_source):
        changed["primary_source"] = source

    discovery = dict(row.discovery or {})
    if source not in discovery:
        discovery[source] = _evidence(merged, now)
        changed["discovery"] = discovery

    samples = list(row.param_samples or [])
    more = bool(row.more_variants)
    for sample in merged.samples:
        if sample in samples:
            continue
        if len(samples) >= MAX_PARAM_SAMPLES:
            more = True
            break
        samples.append(sample)
    if len(samples) != len(row.param_samples or []) or more != bool(row.more_variants):
        changed["param_samples"] = samples
        changed["variants"] = max(len(samples), 1)
        changed["more_variants"] = more

    methods = set(row.methods or []) | merged.methods
    if methods != set(row.methods or []):
        changed["methods"] = sorted(methods)

    if not row.found_on and merged.found_on:
        changed["found_on"] = merged.found_on

    if merged.observed_at and (
        row.archive_last_seen is None or merged.observed_at > row.archive_last_seen
    ):
        changed["archive_last_seen"] = merged.observed_at

    if merged.is_probed:
        changed["is_probed"] = True
        for field_ in (
            "status_code",
            "content_type",
            "content_length",
            "title",
            "words",
            "lines",
            "response_time",
            "redirect_location",
            "content_hash",
        ):
            value = getattr(merged, field_)
            if value is not None:
                changed[field_] = value
        content_type = merged.content_type or row.content_type
        changed["endpoint_class"] = classify(
            merged.path, merged.extension, content_type
        )
        if merged.tech:
            changed["tech"] = merged.tech
    return changed


def upsert(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    source: str,
    observations: list[EndpointObservation],
    index: AssetIndex | None = None,
    default_scheme: str = "https",
) -> UpsertResult:
    """Merge one provider's sightings into the scan's endpoints.

    A source is only ever added to a row, never replaced, and a probe result never
    reverts to unprobed.
    """
    resolved_source = coerce_source(source)
    folded, rejected = _fold(observations, default_scheme)
    result = UpsertResult(rejected=rejected, seen=len(observations))
    if not folded:
        session.commit()
        return result

    resolved_index = index if index is not None else build_index(session, scan_id)
    now = utc_now()
    # a stable key order keeps two providers upserting the same signatures from deadlocking
    signatures = sorted(folded)

    for start in range(0, len(signatures), _BATCH):
        chunk = signatures[start : start + _BATCH]
        existing = {
            row.signature: row
            for row in session.execute(
                select(Endpoint)
                .where(Endpoint.scan_id == scan_id, Endpoint.signature.in_(chunk))
                .order_by(Endpoint.signature)
                .with_for_update()
            )
            .scalars()
            .all()
        }

        missing = [sig for sig in chunk if sig not in existing]
        fresh = [
            _row(
                folded[sig],
                scan_id=scan_id,
                target_id=target_id,
                project_id=project_id,
                source=resolved_source,
                index=resolved_index,
                now=now,
            )
            for sig in missing
        ]
        merge: list[Endpoint] = list(existing.values())
        if fresh:
            written = session.execute(
                insert(Endpoint)
                .values(fresh)
                .on_conflict_do_nothing(constraint=_CONSTRAINT)
                .returning(Endpoint.signature)
            )
            created = set(written.scalars().all())
            result.created += len(created)
            # another writer won the race: merge into its row instead of dropping ours
            lost = [sig for sig in missing if sig not in created]
            if lost:
                merge.extend(
                    session.execute(
                        select(Endpoint)
                        .where(
                            Endpoint.scan_id == scan_id, Endpoint.signature.in_(lost)
                        )
                        .order_by(Endpoint.signature)
                        .with_for_update()
                    )
                    .scalars()
                    .all()
                )

        for row in merge:
            changes = _changes(row, folded[row.signature], resolved_source, now)
            if not changes:
                continue
            session.execute(
                update(Endpoint).where(Endpoint.id == row.id).values(**changes)
            )
            result.updated += 1

    session.commit()
    return result


def verify(
    session: Session,
    *,
    scan_id: uuid.UUID,
    observations: list[EndpointObservation],
    default_scheme: str = "https",
) -> UpsertResult:
    """Apply probe results to endpoints that already exist.

    A request that confirms an endpoint is not a claim that it was discovered, so this
    never touches `sources`, `discovery` or `primary_source`.
    """
    folded, rejected = _fold(observations, default_scheme)
    result = UpsertResult(rejected=rejected, seen=len(observations))
    if not folded:
        session.commit()
        return result

    signatures = sorted(folded)
    for start in range(0, len(signatures), _BATCH):
        chunk = signatures[start : start + _BATCH]
        rows = (
            session.execute(
                select(Endpoint)
                .where(Endpoint.scan_id == scan_id, Endpoint.signature.in_(chunk))
                .order_by(Endpoint.signature)
                .with_for_update()
            )
            .scalars()
            .all()
        )
        for row in rows:
            merged = folded[row.signature]
            if not merged.is_probed:
                continue
            session.execute(
                update(Endpoint)
                .where(Endpoint.id == row.id)
                .values(
                    is_probed=True,
                    status_code=merged.status_code,
                    content_type=merged.content_type,
                    content_length=merged.content_length,
                    title=merged.title,
                    words=merged.words,
                    lines=merged.lines,
                    response_time=merged.response_time,
                    redirect_location=merged.redirect_location,
                    content_hash=merged.content_hash,
                    tech=merged.tech or list(row.tech or []),
                    endpoint_class=classify(
                        merged.path, merged.extension, merged.content_type
                    ),
                    methods=sorted(set(row.methods or []) | merged.methods),
                )
            )
            result.updated += 1
    session.commit()
    return result


def seed_from_assets(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
) -> UpsertResult:
    """Every live web asset is an endpoint the scan already proved exists."""
    rows = session.execute(
        select(
            HttpAsset.url,
            HttpAsset.status_code,
            HttpAsset.content_type,
            HttpAsset.content_length,
            HttpAsset.title,
            HttpAsset.words,
            HttpAsset.lines,
            HttpAsset.response_time,
            HttpAsset.location,
            HttpAsset.content_hash,
            HttpAsset.tech,
            HttpAsset.method,
        ).where(HttpAsset.scan_id == scan_id)
    ).all()
    observations = [
        EndpointObservation(
            url=row.url,
            is_probed=row.status_code is not None,
            status_code=row.status_code,
            content_type=row.content_type,
            content_length=row.content_length,
            title=row.title,
            words=row.words,
            lines=row.lines,
            response_time=row.response_time,
            redirect_location=row.location,
            content_hash=row.content_hash,
            tech=list(row.tech or []),
            methods=[row.method] if row.method else [],
        )
        for row in rows
    ]
    return upsert(
        session,
        scan_id=scan_id,
        target_id=target_id,
        project_id=project_id,
        source=EndpointSource.SEED.value,
        observations=observations,
    )
