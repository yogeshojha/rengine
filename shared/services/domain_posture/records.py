"""The DNS facts one zone is judged on."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Protocol

from shared.definitions.domain_posture import (
    SPF_INCLUDE_CAP,
    SPF_INCLUDE_DEPTH,
    DnssecState,
    SpfAll,
)
from shared.services.domain_posture import spf as spf_rules

NULL_MX = "."
APEX_TYPES: tuple[str, ...] = ("txt", "mx", "caa", "soa", "ns")
TXT: tuple[str, ...] = ("txt",)
_DMARC = "_dmarc"
_MTA_STS = "_mta-sts"
_TLS_RPT = "_smtp._tls"
_DOMAINKEY = "_domainkey"


@dataclass(frozen=True)
class PolicyFetch:
    """reached is False when the policy host could not be asked."""

    reached: bool
    body: str | None = None


class Lookup(Protocol):
    """Records keyed by name; a name absent from the answer was not resolved."""

    def records(
        self, names: list[str], types: tuple[str, ...]
    ) -> dict[str, dict[str, list[str]]]: ...
    def dnssec(self, zone: str) -> str: ...
    def policy(self, zone: str) -> PolicyFetch: ...


def dmarc_records(txt: Iterable[str]) -> list[str]:
    return [v for v in txt if v.strip().lower().startswith("v=dmarc1")]


def mx_host(value: str) -> str:
    """The exchange name without its preference."""
    parts = value.split()
    host = parts[-1] if parts else ""
    if len(parts) > 1 and not parts[0].isdigit():
        host = value.strip()
    return host.strip().rstrip(".") or NULL_MX


@dataclass
class ZoneRecords:
    zone: str
    parent: str | None = None
    answered: bool = False
    dmarc_inherited: bool = False
    dmarc_unknown: bool = False
    txt: list[str] = field(default_factory=list)
    mx: list[str] = field(default_factory=list)
    caa: list[str] = field(default_factory=list)
    dmarc: list[str] = field(default_factory=list)
    mta_sts: list[str] = field(default_factory=list)
    tls_rpt: list[str] = field(default_factory=list)
    dkim: dict[str, str] = field(default_factory=dict)
    spf_lookups: int | None = None
    spf_lookups_capped: bool = False
    spf_redirect_all: str | None = None
    dnssec: str = DnssecState.UNKNOWN.value
    policy: str | None = None
    policy_fetched: bool = False

    @property
    def null_mx(self) -> bool:
        return len(self.mx) == 1 and self.mx[0].strip() in (NULL_MX, "")

    @property
    def receives_mail(self) -> bool:
        return bool(self.mx) and not self.null_mx


def gather(
    zones: Iterable[str] | dict[str, str | None],
    lookup: Lookup,
    *,
    selectors: Iterable[str],
    fetch_policy: bool,
    on_progress: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    workers: int = 8,
) -> dict[str, ZoneRecords]:
    """Every record the checks read, for every zone."""
    parents = zones if isinstance(zones, dict) else dict.fromkeys(zones)
    out = {
        zone: ZoneRecords(zone=zone, parent=parent) for zone, parent in parents.items()
    }
    names = list(out)
    if not names:
        return out
    selectors = list(selectors)

    apex = lookup.records(names, APEX_TYPES)
    silent = [zone for zone in names if zone not in apex]
    if silent:
        apex.update(lookup.records(silent, APEX_TYPES))
    for zone, rec in out.items():
        found = apex.get(zone)
        rec.answered = found is not None
        if found is None:
            continue
        rec.txt = list(found.get("txt", []))
        rec.mx = [mx_host(v) for v in found.get("mx", [])]
        rec.caa = list(found.get("caa", []))

    live = [zone for zone, rec in out.items() if rec.answered]
    if not live:
        return out
    if on_progress:
        on_progress(f"{len(live)} zones answered, reading policy records")

    labels: dict[str, tuple[str, str]] = {}
    for zone in live:
        labels[f"{_DMARC}.{zone}"] = (zone, "dmarc")
        labels[f"{_MTA_STS}.{zone}"] = (zone, "mta_sts")
        labels[f"{_TLS_RPT}.{zone}"] = (zone, "tls_rpt")
    found = lookup.records(list(labels), TXT)
    for name, (zone, attr) in labels.items():
        setattr(out[zone], attr, list(found.get(name, {}).get("txt", [])))
    for zone in live:
        rec = out[zone]
        if rec.parent is None or dmarc_records(rec.dmarc):
            continue
        parent = out.get(rec.parent)
        if parent is None or not parent.answered:
            rec.dmarc_unknown = True
        elif dmarc_records(parent.dmarc):
            rec.dmarc = list(parent.dmarc)
            rec.dmarc_inherited = True

    _dkim(out, live, lookup, selectors)
    _spf_lookups(out, live, lookup)

    def _probe(zone: str) -> tuple[str, str, PolicyFetch | None]:
        rec = out[zone]
        state = lookup.dnssec(zone)
        fetched = lookup.policy(zone) if fetch_policy and rec.mta_sts else None
        return zone, state, fetched

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for zone, state, fetched in pool.map(_probe, live):
            if should_stop and should_stop():
                break
            rec = out[zone]
            rec.dnssec = state
            if fetched is not None:
                rec.policy_fetched = fetched.reached
                rec.policy = fetched.body
    return out


def _dkim(
    out: dict[str, ZoneRecords], live: list[str], lookup: Lookup, selectors: list[str]
) -> None:
    probes = {
        f"{selector}.{_DOMAINKEY}.{zone}": (zone, selector)
        for zone in live
        if spf_rules.spf_records(out[zone].txt) or out[zone].receives_mail
        for selector in selectors
    }
    if not probes:
        return
    found = lookup.records(list(probes), TXT)
    for name, (zone, selector) in probes.items():
        values = [v for v in found.get(name, {}).get("txt", []) if "p=" in v]
        if values:
            out[zone].dkim[selector] = values[0]


def _spf_lookups(out: dict[str, ZoneRecords], live: list[str], lookup: Lookup) -> None:
    """Resolve every include and redirect breadth-first, one batch per depth."""
    cache: dict[str, list[str] | None] = {}
    frontier: set[str] = set()
    for zone in live:
        records = spf_rules.spf_records(out[zone].txt)
        if records:
            cache[zone] = out[zone].txt
            frontier |= spf_rules.referenced_zones(records[0])
    for _ in range(SPF_INCLUDE_DEPTH):
        wanted = sorted(n for n in frontier if n not in cache)[:SPF_INCLUDE_CAP]
        if not wanted:
            break
        found = lookup.records(wanted, TXT)
        frontier = set()
        for name in wanted:
            txt = list(found[name].get("txt", [])) if name in found else None
            cache[name] = txt
            records = spf_rules.spf_records(txt or [])
            if records:
                frontier |= spf_rules.referenced_zones(records[0])

    for zone in live:
        rec = out[zone]
        records = spf_rules.spf_records(rec.txt)
        if not records:
            continue
        count = spf_rules.lookup_count(zone, records[0], cache.get)
        rec.spf_lookups = count.lookups
        rec.spf_lookups_capped = count.capped
        target = spf_rules.redirect_target(records[0])
        if target and spf_rules.all_qualifier(records[0]) == SpfAll.ABSENT.value:
            delegated = spf_rules.spf_records(cache.get(target) or [])
            if delegated:
                rec.spf_redirect_all = spf_rules.all_qualifier(delegated[0])
