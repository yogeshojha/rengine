"""Diff a focused scan against the run it was seeded from, one row per asset."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from shared.definitions.rescan import SeedKind
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import ScanActivityStatus, ScanScope
from shared.logging import get_logger
from shared.models.endpoint import Endpoint
from shared.models.port import Port
from shared.models.recheck import AssetRecheck
from shared.models.scan_activity import ScanActivity
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from shared.models.scan import Scan

logger = get_logger(__name__)

_RAN = (ScanActivityStatus.SUCCESS.value, ScanActivityStatus.PARTIAL.value)

# scalar host fields worth reporting, in the order a person reads them
_HOST_FIELDS: tuple[tuple[str, str], ...] = (
    ("http_status", "Status"),
    ("page_title", "Title"),
    ("webserver", "Server"),
    ("waf", "WAF"),
    ("cdn_name", "CDN"),
    ("tls_expired", "Certificate expired"),
)


def _text(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _change(field: str, label: str, before, after, tone: str = "neutral") -> dict:
    return {
        "field": field,
        "label": label,
        "before": _text(before),
        "after": _text(after),
        "tone": tone,
    }


def _set_change(field: str, label: str, before: set, after: set) -> dict | None:
    gained = sorted(after - before)
    lost = sorted(before - after)
    if not gained and not lost:
        return None
    parts = []
    if gained:
        parts.append(f"+{len(gained)} {', '.join(str(g) for g in gained[:4])}")
    if lost:
        parts.append(f"-{len(lost)} {', '.join(str(g) for g in lost[:4])}")
    return _change(
        field,
        label,
        None,
        " · ".join(parts),
        "up" if gained and not lost else "down" if lost and not gained else "neutral",
    )


def _count_change(field: str, label: str, before: int, after: int) -> dict | None:
    if before == after:
        return None
    return _change(field, label, before, after, "up" if after > before else "down")


class _Differ:
    def __init__(self, session: Session, scan_id: uuid.UUID, parent_id: uuid.UUID):
        self.session = session
        self.scan_id = scan_id
        self.parent_id = parent_id

    def hosts(self, names: list[str]) -> dict[str, dict]:
        rows = self.session.execute(
            select(Subdomain).where(
                Subdomain.scan_id.in_([self.scan_id, self.parent_id]),
                Subdomain.name.in_(names),
            )
        ).scalars()
        out: dict[str, dict] = {}
        for row in rows:
            side = "now" if row.scan_id == self.scan_id else "before"
            out.setdefault(row.name, {})[side] = row
        return out

    def ports(self, ips: list[str]) -> dict[str, dict[str, set]]:
        if not ips:
            return {}
        rows = self.session.execute(
            select(Port.scan_id, Port.ip, Port.number, Port.protocol).where(
                Port.scan_id.in_([self.scan_id, self.parent_id]), Port.ip.in_(ips)
            )
        ).all()
        out: dict[str, dict[str, set]] = {}
        for scan_id, ip, number, protocol in rows:
            side = "now" if scan_id == self.scan_id else "before"
            out.setdefault(ip, {"now": set(), "before": set()})[side].add(
                f"{number}/{protocol}"
            )
        return out

    def vulns(self, column, values: list[str]) -> dict[str, dict[str, set]]:
        if not values:
            return {}
        rows = self.session.execute(
            select(Vulnerability.scan_id, column, Vulnerability.fingerprint).where(
                Vulnerability.scan_id.in_([self.scan_id, self.parent_id]),
                column.in_(values),
            )
        ).all()
        out: dict[str, dict[str, set]] = {}
        for scan_id, key, fingerprint in rows:
            side = "now" if scan_id == self.scan_id else "before"
            out.setdefault(key, {"now": set(), "before": set()})[side].add(fingerprint)
        return out

    def endpoints(self, hosts: list[str]) -> dict[str, dict[str, int]]:
        if not hosts:
            return {}
        rows = self.session.execute(
            select(Endpoint.scan_id, Endpoint.host, func.count())
            .where(
                Endpoint.scan_id.in_([self.scan_id, self.parent_id]),
                Endpoint.host.in_(hosts),
            )
            .group_by(Endpoint.scan_id, Endpoint.host)
        ).all()
        out: dict[str, dict[str, int]] = {}
        for scan_id, host, count in rows:
            side = "now" if scan_id == self.scan_id else "before"
            out.setdefault(host, {"now": 0, "before": 0})[side] = int(count)
        return out


def _host_changes(pair: dict, ran: set[str]) -> list[dict]:
    now = pair.get("now")
    before = pair.get("before")
    if now is None:
        return []
    changes: list[dict] = []
    if "http_probe" in ran:
        for field, label in _HOST_FIELDS:
            new = getattr(now, field, None)
            old = getattr(before, field, None) if before is not None else None
            if _text(new) != _text(old):
                tone = "down" if new is None and old is not None else "neutral"
                changes.append(_change(field, label, old, new, tone))
        tech = _set_change(
            "tech",
            "Technology",
            set(getattr(before, "tech", None) or []) if before is not None else set(),
            set(now.tech or []),
        )
        if tech:
            changes.append(tech)
        ips = _set_change(
            "resolved_ips",
            "Addresses",
            set(getattr(before, "resolved_ips", None) or [])
            if before is not None
            else set(),
            set(now.resolved_ips or []),
        )
        if ips:
            changes.append(ips)
    return changes


def _ports_change(sides: dict[str, set] | None) -> dict | None:
    if not sides:
        return None
    return _set_change("ports", "Open ports", sides["before"], sides["now"])


def _findings_change(sides: dict[str, set] | None) -> dict | None:
    if not sides:
        return None
    entry = _set_change("findings", "Findings", sides["before"], sides["now"])
    if entry is not None:
        entry["after"] = _finding_summary(sides)
    return entry


def _finding_summary(sides: dict[str, set]) -> str:
    gained = len(sides["now"] - sides["before"])
    lost = len(sides["before"] - sides["now"])
    parts = []
    if gained:
        parts.append(f"+{gained} new")
    if lost:
        parts.append(f"{lost} gone")
    return " · ".join(parts)


class _Lookups:
    def __init__(
        self, differ: _Differ, hosts: list[str], addresses: list[str], ran: set[str]
    ):
        self.ran = ran
        self.host_rows = differ.hosts(hosts) if hosts else {}
        self.host_ips: dict[str, list[str]] = {}
        for name, pair in self.host_rows.items():
            ips: set[str] = set()
            for side in ("now", "before"):
                row = pair.get(side)
                if row is not None:
                    ips.update(row.resolved_ips or [])
            self.host_ips[name] = sorted(ips)
        scanned = sorted(
            {ip for ips in self.host_ips.values() for ip in ips} | set(addresses)
        )
        self.ports = differ.ports(scanned) if "port_scan" in ran else {}
        vulns_ran = "vulnerability_scan" in ran
        self.host_vulns = (
            differ.vulns(Vulnerability.host, hosts) if hosts and vulns_ran else {}
        )
        self.ip_vulns = (
            differ.vulns(Vulnerability.ip, addresses) if addresses and vulns_ran else {}
        )
        self.endpoints = (
            differ.endpoints(hosts) if hosts and "url_discovery" in ran else {}
        )

    def for_host(self, name: str) -> list[dict]:
        changes = _host_changes(self.host_rows.get(name, {}), self.ran)
        for ip in self.host_ips.get(name, []):
            entry = _ports_change(self.ports.get(ip))
            if entry:
                changes.append(entry)
        entry = _findings_change(self.host_vulns.get(name))
        if entry:
            changes.append(entry)
        counts = self.endpoints.get(name)
        if counts:
            entry = _count_change(
                "endpoints", "Endpoints", counts["before"], counts["now"]
            )
            if entry:
                changes.append(entry)
        return changes

    def for_address(self, address: str) -> list[dict]:
        changes: list[dict] = []
        for entry in (
            _ports_change(self.ports.get(address)),
            _findings_change(self.ip_vulns.get(address)),
        ):
            if entry:
                changes.append(entry)
        return changes


def _ran_stages(session: Session, scan_id: uuid.UUID) -> set[str]:
    return {
        name
        for name, status in session.execute(
            select(ScanActivity.name, ScanActivity.status).where(
                ScanActivity.scan_id == scan_id
            )
        ).all()
        if status in _RAN
    }


def compute_rechecks(session: Session, scan: Scan) -> int:
    """Write one AssetRecheck per seeded asset. Returns how many changed."""
    if scan.scope != ScanScope.FOCUSED.value or scan.parent_scan_id is None:
        return 0
    config = scan.execution_config or {}
    seeds = config.get("seed_assets") or []
    if not seeds:
        return 0
    dimension = config.get("_dimension") or SurfaceDimension.WEB_ASSETS.value

    hosts = [s["value"] for s in seeds if s.get("kind") == SeedKind.HOST.value]
    addresses = [s["value"] for s in seeds if s.get("kind") == SeedKind.ADDRESS.value]
    lookups = _Lookups(
        _Differ(session, scan.id, scan.parent_scan_id),
        hosts,
        addresses,
        _ran_stages(session, scan.id),
    )

    now = utc_now()
    records = [
        AssetRecheck(
            project_id=scan.project_id,
            target_id=scan.target_id,
            scan_id=scan.id,
            parent_scan_id=scan.parent_scan_id,
            dimension=dimension,
            asset_kind=kind,
            asset_key=key,
            changed=bool(changes),
            changes=changes,
            created_at=now,
        )
        for kind, key, changes in (
            [(SeedKind.HOST.value, name, lookups.for_host(name)) for name in hosts]
            + [
                (SeedKind.ADDRESS.value, addr, lookups.for_address(addr))
                for addr in addresses
            ]
        )
    ]
    session.add_all(records)
    session.commit()
    changed = sum(1 for r in records if r.changed)
    logger.info(
        "recheck: scan %s wrote %d asset row(s), %d changed",
        scan.id,
        len(records),
        changed,
    )
    return changed
