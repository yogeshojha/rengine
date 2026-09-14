"""Origin clusters: web assets that are one backend, on exact identity only."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from shared.definitions.scan_surface import BODY_IDENTITY_BYTES, ClusterSignal


@dataclass
class RootCandidate:
    """One web asset row, in the fields the cluster rule and the rank read."""

    asset_id: uuid.UUID
    value: str
    scheme: str
    host: str
    port: int
    status: int | None = None
    title: str | None = None
    content_hash: str | None = None
    content_length: int | None = None
    words: int | None = None
    lines: int | None = None
    webserver: str | None = None
    ip: str | None = None
    a_records: list[str] = field(default_factory=list)
    aaaa_records: list[str] = field(default_factory=list)
    is_cdn: bool = False
    waf: str | None = None
    tls_fingerprint: str | None = None
    favicon_hash: str | None = None
    not_found: list | None = None
    tech: list[str] = field(default_factory=list)
    cpe: list[str] = field(default_factory=list)
    software: list = field(default_factory=list)
    endpoints: int = 0
    covered_before: bool = False
    rank: float = 0.0
    tags: list[str] = field(default_factory=list)
    unmapped_tech: list[str] = field(default_factory=list)

    @property
    def guarded(self) -> bool:
        return bool(self.waf or self.is_cdn)

    @property
    def addresses(self) -> frozenset[str]:
        found = {str(a).lower() for a in (*self.a_records, *self.aaaa_records) if a}
        if not found and self.ip:
            found = {self.ip.lower()}
        return frozenset(found)

    @property
    def canary_key(self) -> str | None:
        if not self.not_found:
            return None
        return json.dumps(self.not_found, sort_keys=True, default=str)


@dataclass
class Cluster:
    id: uuid.UUID
    representative: RootCandidate
    members: list[RootCandidate] = field(default_factory=list)
    signals: dict[uuid.UUID, list[str]] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return 1 + len(self.members)


def body_key(candidate: RootCandidate) -> tuple:
    """The body hash when it is an identity, the response shape otherwise."""
    if (
        candidate.content_hash
        and (candidate.content_length or 0) >= BODY_IDENTITY_BYTES
    ):
        return ("hash", candidate.content_hash)
    return (
        "shape",
        candidate.words,
        candidate.lines,
        (candidate.webserver or "").lower(),
    )


def _mandatory_key(candidate: RootCandidate) -> tuple:
    return (
        candidate.scheme,
        candidate.port,
        candidate.status,
        (candidate.title or "").strip(),
        body_key(candidate),
    )


def _network_signals(rep: RootCandidate, other: RootCandidate) -> list[str] | None:
    """Address and certificate, with the certificate standing in for a CDN edge."""
    if rep.is_cdn or other.is_cdn:
        if not (rep.tls_fingerprint and other.tls_fingerprint):
            return None
        if rep.tls_fingerprint != other.tls_fingerprint:
            return None
        return [ClusterSignal.CERTIFICATE.value]
    if not (rep.addresses and other.addresses) or rep.addresses != other.addresses:
        return None
    signals = [ClusterSignal.ADDRESS.value]
    if rep.tls_fingerprint and other.tls_fingerprint:
        if rep.tls_fingerprint != other.tls_fingerprint:
            return None
        signals.append(ClusterSignal.CERTIFICATE.value)
    return signals


def _optional_signal(a: str | None, b: str | None, signal: str) -> list[str] | None:
    """Empty when either side is silent, the signal when both agree, None otherwise."""
    if not (a and b):
        return []
    return [signal] if a == b else None


def same_origin(rep: RootCandidate, other: RootCandidate) -> list[str] | None:
    """The signals two web assets agree on, or None when one disagrees."""
    if _mandatory_key(rep) != _mandatory_key(other):
        return None
    signals = [ClusterSignal.STATUS.value, ClusterSignal.TITLE.value]
    signals.append(
        ClusterSignal.BODY.value
        if body_key(rep)[0] == "hash"
        else ClusterSignal.SHAPE.value
    )
    for extra in (
        _network_signals(rep, other),
        _optional_signal(rep.canary_key, other.canary_key, ClusterSignal.CANARY.value),
        _optional_signal(
            rep.favicon_hash, other.favicon_hash, ClusterSignal.FAVICON.value
        ),
    ):
        if extra is None:
            return None
        signals.extend(extra)
    return signals


def _joins(cluster: Cluster, candidate: RootCandidate) -> list[str] | None:
    """A candidate joins only when every member agrees with it."""
    signals = same_origin(cluster.representative, candidate)
    if signals is None:
        return None
    for member in cluster.members:
        if same_origin(member, candidate) is None:
            return None
    return signals


def cluster_roots(candidates: list[RootCandidate]) -> list[Cluster]:
    """Group web assets into origins. The highest-ranked member represents each."""
    groups: dict[tuple, list[RootCandidate]] = {}
    for candidate in candidates:
        groups.setdefault(_mandatory_key(candidate), []).append(candidate)

    clusters: list[Cluster] = []
    for key in sorted(groups, key=repr):
        ordered = sorted(groups[key], key=lambda c: (-c.rank, c.value))
        local: list[Cluster] = []
        for candidate in ordered:
            for cluster in local:
                signals = _joins(cluster, candidate)
                if signals is not None:
                    cluster.members.append(candidate)
                    cluster.signals[candidate.asset_id] = signals
                    break
            else:
                local.append(Cluster(id=uuid.uuid4(), representative=candidate))
        clusters.extend(local)
    return clusters


__all__ = ["Cluster", "RootCandidate", "body_key", "cluster_roots", "same_origin"]
