"""Response rules applied after the probe. Rows the response proves are not endpoints are deleted."""

from __future__ import annotations

import secrets
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from sqlalchemy import delete, select, update

from shared.definitions.domains import registrable_domain
from shared.definitions.endpoints import (
    ARCHIVE_SOURCES,
    CANARY_LENGTH,
    NOT_FOUND_TOLERANCE,
    SAME_REDIRECT_MIN,
    SAME_RESPONSE_MIN,
    SIMILAR_RESPONSE_MIN,
    EndpointSource,
    NoiseRule,
)
from shared.logging import get_logger
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

_DELETE_CHUNK = 1000
_GONE = frozenset({404, 410})
_CANARY_STATUSES = frozenset(range(200, 300)) | frozenset({403, 404, 410})
_OK = range(200, 300)
_REDIRECT = range(300, 400)
_ERROR = range(500, 600)
_PROTECTED_SOURCES = frozenset(
    {EndpointSource.PROXY.value, EndpointSource.IMPORT.value}
)
_DEFAULT_PORTS = {"http": 80, "https": 443}


# ---------- fingerprints ----------


@dataclass(frozen=True)
class Fingerprint:
    status: int | None
    content_hash: str | None
    words: int | None
    lines: int | None
    title: str | None

    @classmethod
    def of(cls, fields: dict) -> Fingerprint:
        return cls(
            status=fields.get("status_code"),
            content_hash=fields.get("content_hash"),
            words=fields.get("words"),
            lines=fields.get("lines"),
            title=(fields.get("title") or None),
        )

    @classmethod
    def from_json(cls, value: dict) -> Fingerprint:
        return cls(
            status=value.get("status"),
            content_hash=value.get("hash"),
            words=value.get("words"),
            lines=value.get("lines"),
            title=value.get("title"),
        )

    def to_json(self) -> dict:
        return {
            "status": self.status,
            "hash": self.content_hash,
            "words": self.words,
            "lines": self.lines,
            "title": self.title,
        }

    def matches(self, other: Fingerprint) -> bool:
        if self.status is None or self.status != other.status:
            return False
        if self.content_hash and self.content_hash == other.content_hash:
            return True
        if (self.title or None) != (other.title or None):
            return False
        return _close(self.words, other.words) and _close(self.lines, other.lines)


def _close(a: int | None, b: int | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= max(2, int(NOT_FOUND_TOLERANCE * max(a, b)))


def canary_urls(root: str) -> list[str]:
    """Three paths no site has, under one root."""
    token = secrets.token_hex(CANARY_LENGTH // 2)
    return [f"{root}/{token}", f"{root}/{token}.php", f"{root}/{token}/"]


def root_of(scheme: str, host: str, port: int) -> str:
    literal = f"[{host}]" if ":" in host else host
    if port and port != _DEFAULT_PORTS.get(scheme):
        return f"{scheme}://{literal}:{port}"
    return f"{scheme}://{literal}"


def store_fingerprints(
    session: Session, fingerprints: dict[uuid.UUID, list[Fingerprint]]
) -> None:
    """Keep each root's not-found answers on its web asset."""
    payload = [
        {"id": asset_id, "not_found": [fp.to_json() for fp in fps]}
        for asset_id, fps in fingerprints.items()
        if fps
    ]
    if payload:
        session.execute(update(HttpAsset), payload)
        session.commit()


# ---------- the judgement ----------


@dataclass
class _Row:
    id: uuid.UUID
    host: str
    scheme: str
    port: int
    path: str
    status: int | None
    content_hash: str | None
    words: int | None
    lines: int | None
    title: str | None
    location: str | None
    sources: frozenset[str]
    protected: bool

    @property
    def fingerprint(self) -> Fingerprint:
        return Fingerprint(
            self.status, self.content_hash, self.words, self.lines, self.title
        )

    @property
    def redirect(self) -> bool:
        return self.status in _REDIRECT

    @property
    def ok(self) -> bool:
        return self.status in _OK

    @property
    def error(self) -> bool:
        return self.status in _ERROR


def judge(
    session: Session,
    scan_id: uuid.UUID,
    *,
    hosts: Iterable[str] | None = None,
) -> Counter:
    """Delete probed rows the response proves are not endpoints. Returns counts per rule."""
    rows = _load(session, scan_id, hosts)
    if not rows:
        return Counter()
    fingerprints = _fingerprints(session, scan_id)
    in_scope = _scope(session, scan_id)
    verdicts: dict[uuid.UUID, str] = {}
    groups: dict[tuple[str, str, int], list[_Row]] = defaultdict(list)
    for row in rows:
        groups[(row.scheme, row.host, row.port)].append(row)
    for key, members in groups.items():
        _judge_host(members, fingerprints.get(key, []), in_scope, verdicts)
    if verdicts:
        ids = sorted(verdicts, key=str)
        for start in range(0, len(ids), _DELETE_CHUNK):
            session.execute(
                delete(Endpoint).where(
                    Endpoint.id.in_(ids[start : start + _DELETE_CHUNK])
                )
            )
        session.commit()
    return Counter(verdicts.values())


def _judge_host(
    rows: list[_Row],
    canaries: list[Fingerprint],
    in_scope: Callable[[str], bool],
    verdicts: dict[uuid.UUID, str],
) -> None:
    live = [r for r in rows if not r.protected]
    root = next((r for r in rows if r.path == "/"), None)
    for rule in (
        lambda rs: _gone(rs, canaries),
        lambda rs: _off_scope(rs, in_scope),
        _same_redirect,
        lambda rs: _catch_all(rs, root),
        _same_response,
        _similar_response,
    ):
        for row_id, verdict in rule(live).items():
            verdicts[row_id] = verdict
        live = [r for r in live if r.id not in verdicts]


def _gone(rows: list[_Row], canaries: list[Fingerprint]) -> dict[uuid.UUID, str]:
    out: dict[uuid.UUID, str] = {}
    for row in rows:
        if row.status in _GONE and row.sources and row.sources <= ARCHIVE_SOURCES:
            out[row.id] = NoiseRule.ARCHIVE_ROT.value
        elif row.status in _GONE or (
            not row.redirect and any(c.matches(row.fingerprint) for c in canaries)
        ):
            out[row.id] = NoiseRule.NOT_FOUND.value
    return out


def _off_scope(
    rows: list[_Row], in_scope: Callable[[str], bool]
) -> dict[uuid.UUID, str]:
    return {
        row.id: NoiseRule.OFF_SCOPE.value
        for row in rows
        if row.redirect
        and row.location
        and not _location_in_scope(row.location, in_scope)
    }


def _same_redirect(rows: list[_Row]) -> dict[uuid.UUID, str]:
    by_location: dict[str, list[_Row]] = defaultdict(list)
    for row in rows:
        if row.redirect and row.location:
            by_location[row.location].append(row)
    return {
        row.id: NoiseRule.SAME_REDIRECT.value
        for members in by_location.values()
        if len(members) >= SAME_REDIRECT_MIN
        for row in _all_but_shortest(members)
    }


def _catch_all(rows: list[_Row], root: _Row | None) -> dict[uuid.UUID, str]:
    if root is None or not root.content_hash or not root.ok:
        return {}
    return {
        row.id: NoiseRule.CATCH_ALL.value
        for row in rows
        if row.ok and row.content_hash == root.content_hash
    }


def _same_response(rows: list[_Row]) -> dict[uuid.UUID, str]:
    by_body: dict[tuple[int | None, str], list[_Row]] = defaultdict(list)
    for row in rows:
        if (row.ok or row.error) and row.content_hash:
            by_body[(row.status, row.content_hash)].append(row)
    return {
        row.id: NoiseRule.SAME_RESPONSE.value
        for members in by_body.values()
        if len(members) >= SAME_RESPONSE_MIN
        for row in _all_but_shortest(members)
    }


def _similar_response(rows: list[_Row]) -> dict[uuid.UUID, str]:
    by_title: dict[tuple[int | None, str], list[_Row]] = defaultdict(list)
    for row in rows:
        if row.ok and row.title:
            by_title[(row.status, row.title)].append(row)
    return {
        row.id: NoiseRule.SIMILAR_RESPONSE.value
        for members in by_title.values()
        for cluster in _clusters(members)
        if len(cluster) >= SIMILAR_RESPONSE_MIN
        for row in cluster[1:]
    }


def _all_but_shortest(rows: list[_Row]) -> list[_Row]:
    ordered = sorted(rows, key=lambda r: (r.path != "/", len(r.path), r.path))
    return ordered[1:]


def _clusters(rows: list[_Row]) -> list[list[_Row]]:
    """Rows whose word and line counts sit within tolerance of a cluster's first member."""
    ordered = sorted(rows, key=lambda r: (r.path != "/", len(r.path), r.path))
    clusters: list[list[_Row]] = []
    for row in ordered:
        for cluster in clusters:
            anchor = cluster[0]
            if _close(anchor.words, row.words) and _close(anchor.lines, row.lines):
                cluster.append(row)
                break
        else:
            clusters.append([row])
    return clusters


def _location_in_scope(location: str, in_scope: Callable[[str], bool]) -> bool:
    try:
        host = (urlsplit(location).hostname or "").lower()
    except ValueError:
        return True
    return not host or in_scope(host)


# ---------- loading ----------


def _load(
    session: Session, scan_id: uuid.UUID, hosts: Iterable[str] | None
) -> list[_Row]:
    query = select(
        Endpoint.id,
        Endpoint.host,
        Endpoint.scheme,
        Endpoint.port,
        Endpoint.path,
        Endpoint.status_code,
        Endpoint.content_hash,
        Endpoint.words,
        Endpoint.lines,
        Endpoint.title,
        Endpoint.redirect_location,
        Endpoint.sources,
    ).where(Endpoint.scan_id == scan_id, Endpoint.is_probed.is_(True))
    if hosts is not None:
        query = query.where(Endpoint.host.in_(list(hosts)))
    out: list[_Row] = []
    for r in session.execute(query):
        sources = frozenset(r.sources or [])
        out.append(
            _Row(
                id=r.id,
                host=r.host,
                scheme=r.scheme,
                port=int(r.port or 0),
                path=r.path,
                status=r.status_code,
                content_hash=r.content_hash,
                words=r.words,
                lines=r.lines,
                title=(r.title or None),
                location=r.redirect_location,
                sources=sources,
                protected=r.path == "/" or bool(sources & _PROTECTED_SOURCES),
            )
        )
    return out


def _fingerprints(
    session: Session, scan_id: uuid.UUID
) -> dict[tuple[str, str, int], list[Fingerprint]]:
    rows = session.execute(
        select(
            HttpAsset.scheme, HttpAsset.host, HttpAsset.port, HttpAsset.not_found
        ).where(HttpAsset.scan_id == scan_id, HttpAsset.not_found.isnot(None))
    ).all()
    out: dict[tuple[str, str, int], list[Fingerprint]] = {}
    for scheme, host, port, stored in rows:
        key = (scheme, host.lower(), int(port or _DEFAULT_PORTS.get(scheme, 0)))
        usable = [
            Fingerprint.from_json(v) for v in (stored or []) if isinstance(v, dict)
        ]
        out[key] = [fp for fp in usable if fp.status in _CANARY_STATUSES]
    return out


def _scope(session: Session, scan_id: uuid.UUID) -> Callable[[str], bool]:
    known = {
        n.lower()
        for n in session.execute(
            select(Subdomain.name).where(Subdomain.scan_id == scan_id)
        ).scalars()
    }
    known |= {
        h.lower()
        for h in session.execute(
            select(HttpAsset.host).where(HttpAsset.scan_id == scan_id)
        ).scalars()
    }
    apexes = {registrable_domain(h) for h in known} - {""}

    def in_scope(host: str) -> bool:
        return host in known or registrable_domain(host) in apexes

    return in_scope
