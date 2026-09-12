"""The only writer of `endpoints`: merges observations by structural signature."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import StatementError

from shared.definitions.endpoints import (
    MAX_PARAM_SAMPLES,
    EndpointSource,
    classify,
    coerce_source,
    interests_for,
    parse_url,
    shape_for,
    source_rank,
)
from shared.logging import get_logger
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.services.endpoint_noise import NoisePolicy, Sifter
from shared.utils.datetime import utc_now
from shared.utils.text import scrub

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
    dropped: dict[str, int] = field(default_factory=dict)

    def add(self, other: UpsertResult) -> None:
        self.created += other.created
        self.updated += other.updated
        self.rejected += other.rejected
        self.seen += other.seen
        for rule, count in other.dropped.items():
            self.dropped[rule] = self.dropped.get(rule, 0) + count


@dataclass
class AssetIndex:
    """The web assets and hostnames this scan already recorded, keyed the way a URL names them."""

    assets: dict[tuple[str, int], uuid.UUID]
    subdomains: dict[str, uuid.UUID]


def build_index(
    session: Session, scan_id: uuid.UUID, hosts: list[str] | None = None
) -> AssetIndex:
    asset_query = select(HttpAsset.id, HttpAsset.host, HttpAsset.port).where(
        HttpAsset.scan_id == scan_id
    )
    host_query = select(Subdomain.id, Subdomain.name).where(
        Subdomain.scan_id == scan_id
    )
    if hosts is not None:
        asset_query = asset_query.where(HttpAsset.host.in_(hosts))
        host_query = host_query.where(Subdomain.name.in_(hosts))
    assets: dict[tuple[str, int], uuid.UUID] = {}
    for row in session.execute(asset_query):
        assets.setdefault((row.host.lower(), int(row.port or 0)), row.id)

    subdomains: dict[str, uuid.UUID] = {}
    for row in session.execute(host_query):
        subdomains.setdefault(row.name.lower(), row.id)

    return AssetIndex(assets=assets, subdomains=subdomains)


@dataclass
class _Merged:
    """One signature's worth of observations, folded before the database is touched."""

    signature: str
    family: str
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
    observations: list[EndpointObservation],
    default_scheme: str,
    sifter: Sifter | None = None,
) -> tuple[dict[str, _Merged], int, dict[str, int]]:
    folded: dict[str, _Merged] = {}
    rejected = 0
    dropped: dict[str, int] = {}
    if sifter is not None:
        sifted = sifter.sift(observations, default_scheme)
        pairs = sifted.kept
        rejected = sifted.dropped.pop("rejected", 0)
        dropped = dict(sifted.dropped)
    else:
        pairs = []
        for obs in observations:
            parsed = parse_url(obs.url, default_scheme=default_scheme)
            if parsed is None:
                rejected += 1
                continue
            pairs.append((obs, parsed))
    for obs, parsed in pairs:
        merged = folded.get(parsed.signature)
        if merged is None:
            merged = _Merged(
                signature=parsed.signature,
                family=parsed.family,
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
    return folded, rejected, dropped


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
    endpoint_class = classify(merged.path, merged.extension, merged.content_type)
    interest = interests_for(
        merged.path,
        merged.params,
        endpoint_class=endpoint_class,
        extension=merged.extension,
    )
    return scrub(
        {
            "id": uuid.uuid4(),
            "scan_id": scan_id,
            "target_id": target_id,
            "project_id": project_id,
            "signature": merged.signature,
            "family": merged.family,
            "url": merged.url,
            "host": merged.host,
            "port": merged.port,
            "scheme": merged.scheme,
            "path": merged.path,
            "shape": shape_for(merged.path)[0],
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
            "endpoint_class": endpoint_class,
            "interest": interest,
            "http_asset_id": index.assets.get((merged.host, merged.port)),
            "subdomain_id": index.subdomains.get(merged.host),
            "archive_last_seen": merged.observed_at,
            "discovered_at": now,
            "created_at": now,
        }
    )


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
        changed["interest"] = interests_for(
            merged.path,
            merged.params,
            endpoint_class=changed["endpoint_class"],
            extension=merged.extension,
        )
        if merged.tech:
            changed["tech"] = merged.tech
    return scrub(changed)


def _insert_rows(session: Session, rows: list[dict]) -> tuple[set[str], int]:
    """Insert inside a savepoint."""
    try:
        with session.begin_nested():
            written = session.execute(
                insert(Endpoint)
                .values(rows)
                .on_conflict_do_nothing(constraint=_CONSTRAINT)
                .returning(Endpoint.signature)
            )
            return set(written.scalars().all()), 0
    except StatementError:
        logger.warning("endpoint batch rejected, retrying row by row")
    created: set[str] = set()
    refused = 0
    for row in rows:
        try:
            with session.begin_nested():
                written = session.execute(
                    insert(Endpoint)
                    .values([row])
                    .on_conflict_do_nothing(constraint=_CONSTRAINT)
                    .returning(Endpoint.signature)
                )
                created.update(written.scalars().all())
        except StatementError:
            refused += 1
    return created, refused


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
    sifter: Sifter | None = None,
    policy: NoisePolicy | None = None,
) -> UpsertResult:
    """Merge one provider's sightings into the scan's endpoints."""
    resolved_source = coerce_source(source)
    if sifter is None:
        sifter = Sifter(session, scan_id, policy)
    folded, rejected, dropped = _fold(observations, default_scheme, sifter)
    result = UpsertResult(rejected=rejected, seen=len(observations), dropped=dropped)
    if not folded:
        session.commit()
        return result

    resolved_index = index if index is not None else build_index(session, scan_id)
    now = utc_now()
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
            created, refused = _insert_rows(session, fresh)
            result.created += len(created)
            result.rejected += refused
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

        shaped: dict[frozenset[str], list[dict]] = {}
        for row in merge:
            changes = _changes(row, folded[row.signature], resolved_source, now)
            if not changes:
                continue
            shaped.setdefault(frozenset(changes), []).append({"id": row.id, **changes})
            result.updated += 1
        for payload in shaped.values():
            session.execute(update(Endpoint), payload)

    session.commit()
    return result


def verify(
    session: Session,
    *,
    scan_id: uuid.UUID,
    observations: list[EndpointObservation],
    default_scheme: str = "https",
) -> UpsertResult:
    """Apply probe results to endpoints that already exist."""
    folded, rejected, _dropped = _fold(observations, default_scheme)
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
        payload: list[dict] = []
        for row in rows:
            merged = folded[row.signature]
            if not merged.is_probed:
                continue
            klass = classify(merged.path, merged.extension, merged.content_type)
            payload.append(
                {
                    "id": row.id,
                    "is_probed": True,
                    "status_code": merged.status_code,
                    "content_type": merged.content_type,
                    "content_length": merged.content_length,
                    "title": merged.title,
                    "words": merged.words,
                    "lines": merged.lines,
                    "response_time": merged.response_time,
                    "redirect_location": merged.redirect_location,
                    "content_hash": merged.content_hash,
                    "tech": merged.tech or list(row.tech or []),
                    "endpoint_class": klass,
                    "interest": interests_for(
                        merged.path,
                        list(row.params or []),
                        endpoint_class=klass,
                        extension=merged.extension,
                    ),
                    "methods": sorted(set(row.methods or []) | merged.methods),
                }
            )
        if payload:
            session.execute(update(Endpoint), payload)
            result.updated += len(payload)
    session.commit()
    return result


def seed_from_assets(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    sifter: Sifter | None = None,
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
        sifter=sifter,
    )
