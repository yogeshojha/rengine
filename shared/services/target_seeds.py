"""Assets an operator stored against a target, folded into every scan of it."""

from __future__ import annotations

import contextlib
import ipaddress
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select, union

from shared.definitions.endpoints import parse_url
from shared.definitions.rescan import ASSET_SEED_STAGE, MAX_RUN_ASSETS, SeedKind
from shared.enums.subdomain import SubdomainSource
from shared.enums.target import TargetType
from shared.models.ip_address import IpAddress
from shared.models.subdomain import Subdomain
from shared.models.target_seed import MAX_SEED_VALUE_LEN, TargetSeed
from shared.utils.validation import (
    normalize_domain,
    normalize_host,
    scannable_address,
)

if TYPE_CHECKING:
    from shared.models.target import Target

MAX_TARGET_SEEDS = MAX_RUN_ASSETS
SEED_SOURCE = SubdomainSource.IMPORTED.value

_TOO_LONG = "Longer than the {limit} character limit."
_UNRECOGNISED = "Not a host name, address or URL."
_OUT_OF_SCOPE = "Not under {target}."
_NOT_ADDRESS = "Only addresses can seed {target}."
_NOT_HOST = "Only host names and URLs can seed {target}."
_NOT_SCANNED = (
    "Loopback, link-local, multicast and reserved address space is not scanned."
)
_NOT_ACCEPTED = "Seed {value} not accepted. {reason}"


@dataclass(frozen=True)
class Seed:
    kind: str
    value: str


@dataclass(frozen=True)
class Rejected:
    value: str
    reason: str


def _in_apex(host: str, apex: str) -> bool:
    return host == apex or host.endswith("." + apex)


def _classify(raw: str) -> Seed | None:
    """A line is a URL, an address or a host name, read off its own shape."""
    value = raw.strip()
    if not value:
        return None
    if "://" in value:
        parsed = parse_url(value)
        return None if parsed is None else Seed(SeedKind.URL.value, parsed.url)
    try:
        return Seed(SeedKind.ADDRESS.value, str(ipaddress.ip_address(value)))
    except ValueError:
        pass
    host = normalize_host(value)
    return None if host is None else Seed(SeedKind.HOST.value, host)


def _host_of(seed: Seed) -> str | None:
    if seed.kind == SeedKind.HOST.value:
        return seed.value
    if seed.kind != SeedKind.URL.value:
        return None
    parsed = parse_url(seed.value)
    return None if parsed is None else parsed.host


def _named_scope(seed: Seed, target: Target) -> str | None:
    """A domain or URL target is seeded by names under it."""
    value = target.target_value
    host = _host_of(seed)
    if host is None:
        return _NOT_HOST.format(target=value)
    if target.target_type.value == TargetType.URL.value:
        parsed = parse_url(value)
        return (
            None
            if parsed and host == parsed.host
            else _OUT_OF_SCOPE.format(target=value)
        )
    return (
        None
        if _in_apex(host, normalize_domain(value))
        else _OUT_OF_SCOPE.format(target=value)
    )


def _address_scope(seed: Seed, target: Target) -> str | None:
    """An IP, range or ASN target is seeded by addresses it covers."""
    value = target.target_value
    if seed.kind != SeedKind.ADDRESS.value:
        return _NOT_ADDRESS.format(target=value)
    if not scannable_address(seed.value):
        return _NOT_SCANNED
    if target.target_type.value == TargetType.IP.value:
        return None if seed.value == value else _OUT_OF_SCOPE.format(target=value)
    if target.target_type.value != TargetType.IP_RANGE.value:
        return None
    try:
        inside = ipaddress.ip_address(seed.value) in ipaddress.ip_network(
            value, strict=False
        )
    except ValueError:
        return _OUT_OF_SCOPE.format(target=value)
    return None if inside else _OUT_OF_SCOPE.format(target=value)


_NAMED = frozenset({TargetType.DOMAIN.value, TargetType.URL.value})


def _scoped(seed: Seed, target: Target) -> str | None:
    """The reason a seed does not belong to this target, or None when it does."""
    if target.target_type.value in _NAMED:
        return _named_scope(seed, target)
    return _address_scope(seed, target)


def parse(values: list[str], target: Target) -> tuple[list[Seed], list[Rejected]]:
    """Classify pasted lines against the target. Every refusal names its own line."""
    seeds: dict[str, Seed] = {}
    rejected: list[Rejected] = []
    for raw in values:
        line = raw.strip()
        if not line:
            continue
        if len(line) > MAX_SEED_VALUE_LEN:
            rejected.append(
                Rejected(line[:120], _TOO_LONG.format(limit=MAX_SEED_VALUE_LEN))
            )
            continue
        seed = _classify(line)
        if seed is None:
            rejected.append(Rejected(line, _UNRECOGNISED))
            continue
        reason = _scoped(seed, target)
        if reason is not None:
            rejected.append(Rejected(line, reason))
            continue
        seeds.setdefault(seed.value, seed)
    return list(seeds.values()), rejected


def _launch_seed(asset: dict) -> Seed:
    kind = asset.get("kind") or ""
    value = (asset.get("value") or "").strip()
    if kind == SeedKind.HOST.value:
        value = normalize_host(value) or value.lower()
    elif kind == SeedKind.ADDRESS.value:
        with contextlib.suppress(ValueError):
            value = str(ipaddress.ip_address(value))
    return Seed(kind, value)


def _launch_scope(seed: Seed, target: Target) -> str | None:
    """Stored-seed scope, narrowed for an ASN and widened for a URL on an address."""
    kind = target.target_type.value
    if kind == TargetType.ASN.value:
        return _OUT_OF_SCOPE.format(target=target.target_value)
    if seed.kind == SeedKind.URL.value and kind not in _NAMED:
        try:
            address = str(ipaddress.ip_address(_host_of(seed) or ""))
        except ValueError:
            return _NOT_ADDRESS.format(target=target.target_value)
        return _address_scope(Seed(SeedKind.ADDRESS.value, address), target)
    return _scoped(seed, target)


async def _recorded(session, target_id: uuid.UUID, keys: set[str]) -> set[str]:
    names = select(Subdomain.name.label("key")).where(
        Subdomain.target_id == target_id, Subdomain.name.in_(sorted(keys))
    )
    addresses = select(IpAddress.ip.label("key")).where(
        IpAddress.target_id == target_id, IpAddress.ip.in_(sorted(keys))
    )
    rows = await session.execute(union(names, addresses))
    return {row[0] for row in rows}


async def launch_refusal(session, assets: list[dict], target: Target) -> str | None:
    """A launch seed outside the target that no scan of it recorded, or None."""
    outside: dict[str, tuple[str, str]] = {}
    for asset in assets:
        seed = _launch_seed(asset)
        reason = _launch_scope(seed, target)
        if reason is None:
            continue
        key = seed.value if seed.kind == SeedKind.ADDRESS.value else _host_of(seed)
        if not key or target.id is None:
            return _NOT_ACCEPTED.format(value=seed.value, reason=reason)
        outside.setdefault(key, (seed.value, reason))
    if not outside:
        return None
    recorded = await _recorded(session, target.id, set(outside))
    for key, (value, reason) in outside.items():
        if key not in recorded:
            return _NOT_ACCEPTED.format(value=value, reason=reason)
    return None


def as_assets(rows: list[TargetSeed]) -> list[dict]:
    """The seed_assets shape a run carries, in a stable order."""
    return [
        {"kind": row.kind, "value": row.value, "source": SEED_SOURCE}
        for row in sorted(rows, key=lambda r: (r.kind, r.value))
    ]


def _statement(target_ids: list[uuid.UUID]):
    return select(TargetSeed).where(TargetSeed.target_id.in_(target_ids))


def _group(rows) -> dict[uuid.UUID, list[dict]]:
    grouped: dict[uuid.UUID, list[TargetSeed]] = {}
    for row in rows:
        grouped.setdefault(row.target_id, []).append(row)
    return {target_id: as_assets(rows) for target_id, rows in grouped.items()}


def load_sync(session, target_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[dict]]:
    if not target_ids:
        return {}
    return _group(session.execute(_statement(target_ids)).scalars().all())


async def load_async(
    session, target_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict]]:
    if not target_ids:
        return {}
    result = await session.execute(_statement(target_ids))
    return _group(result.scalars().all())


def apply(resolved, assets: list[dict], *, seed_only: bool) -> None:
    """Carry assets into a run and switch the seed stage on."""
    if not assets:
        return
    resolved.seed_assets = assets
    resolved.seed_only = seed_only
    resolved.stages[ASSET_SEED_STAGE] = {
        **(resolved.stages.get(ASSET_SEED_STAGE) or {}),
        "enabled": True,
    }


def seeded_hosts(seed_assets: list[dict] | None) -> list[str]:
    """The host names a run was seeded with, a URL seed counting for its host."""
    hosts: list[str] = []
    for seed in seed_assets or []:
        value = (seed.get("value") or "").strip()
        if not value:
            continue
        kind = seed.get("kind")
        if kind == SeedKind.URL.value:
            parsed = parse_url(value)
            if parsed is not None:
                hosts.append(parsed.host)
        elif kind != SeedKind.ADDRESS.value:
            hosts.append(value.lower())
    return list(dict.fromkeys(hosts))
