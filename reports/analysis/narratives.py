"""Chained observations."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable, Iterable

from reports.analysis.brief import AttackPath
from reports.data.models import Issue
from reports.data.source import ReportSource
from shared.definitions.ports import ServiceClass
from shared.definitions.vulnerabilities import Severity

_OK = 2


def _internal(values: Iterable[str]) -> bool:
    """Every value is a private address."""
    seen = [v for v in values if v]
    if not seen:
        return False
    try:
        return all(not ipaddress.ip_address(v).is_global for v in seen)
    except ValueError:
        return False


def _tagged(issues: list[Issue], *tags: str) -> list[Issue]:
    wanted = {t.lower() for t in tags}
    return [i for i in issues if wanted & {t.lower() for t in i.tags}]


def _assets(issues: list[Issue], limit: int = 8) -> list[str]:
    out: list[str] = []
    for issue in issues:
        for host in issue.hosts:
            if host not in out:
                out.append(host)
            if len(out) >= limit:
                return out
    return out


def _kev_live(source: ReportSource, issues: list[Issue]) -> AttackPath | None:
    live = {h.name for h in source.host_rows if h.status}
    hits = [
        i for i in issues if i.is_kev and (not live or any(h in live for h in i.hosts))
    ]
    if not hits:
        return None
    total = sum(i.count for i in hits)
    return AttackPath(
        key="kev_live",
        title="Known exploited weaknesses are reachable",
        detail=(
            f"{total} observation{'s' if total != 1 else ''} across "
            f"{len(_assets(hits, 200))} assets match checks on the CISA Known Exploited "
            "Vulnerabilities catalogue."
        ),
        severity=Severity.CRITICAL.value,
        evidence=[i.name for i in hits[:5]],
        assets=_assets(hits),
        count=total,
    )


def _default_credentials(
    _source: ReportSource, issues: list[Issue]
) -> AttackPath | None:
    hits = _tagged(issues, "default-login", "weak-password")
    if not hits:
        return None
    total = sum(i.count for i in hits)
    return AttackPath(
        key="default_credentials",
        title="Services accept default credentials",
        detail=(
            f"{total} service{'s' if total != 1 else ''} accepted a documented default "
            "account."
        ),
        severity=Severity.CRITICAL.value,
        evidence=[i.name for i in hits[:5]],
        assets=_assets(hits),
        count=total,
    )


def _takeover(_source: ReportSource, issues: list[Issue]) -> AttackPath | None:
    hits = _tagged(issues, "takeover")
    if not hits:
        return None
    total = sum(i.count for i in hits)
    return AttackPath(
        key="takeover",
        title="Hostnames point at unclaimed provider resources",
        detail=(
            f"{total} name{'s' if total != 1 else ''} resolve to a provider where the "
            "backing resource no longer exists. Registering the resource serves content "
            "under the subject's domain."
        ),
        severity=Severity.HIGH.value,
        evidence=[i.name for i in hits[:5]],
        assets=_assets(hits),
        count=total,
    )


def _exposed_data(_source: ReportSource, issues: list[Issue]) -> AttackPath | None:
    hits = _tagged(issues, "exposure", "backup", "config", "disclosure", "debug")
    if not hits:
        return None
    total = sum(i.count for i in hits)
    return AttackPath(
        key="exposed_data",
        title="Source, configuration or backup files are served",
        detail=(
            f"{total} location{'s' if total != 1 else ''} return source, configuration "
            "or backup content."
        ),
        severity=Severity.HIGH.value,
        evidence=[i.name for i in hits[:5]],
        assets=_assets(hits),
        count=total,
    )


def _injection(_source: ReportSource, issues: list[Issue]) -> AttackPath | None:
    hits = _tagged(
        issues, "sqli", "rce", "ssti", "lfi", "ssrf", "injection", "traversal"
    )
    if not hits:
        return None
    total = sum(i.count for i in hits)
    worst = min(hits, key=lambda i: 0 if i.severity == Severity.CRITICAL.value else 1)
    return AttackPath(
        key="injection",
        title="Untrusted input reaches an interpreter",
        detail=(
            f"{total} observation{'s' if total != 1 else ''} of input reaching a query, "
            f"template or the filesystem. The most severe is {worst.name}."
        ),
        severity=worst.severity,
        evidence=[i.name for i in hits[:5]],
        assets=_assets(hits),
        count=total,
    )


def _admin_open(source: ReportSource, issues: list[Issue]) -> AttackPath | None:
    panels = _tagged(issues, "panel", "login", "admin")
    endpoints = [
        e
        for e in source.endpoint_rows
        if "admin" in (e.interest or []) and (e.status or 0) // 100 == _OK
    ]
    if not panels and not endpoints:
        return None
    total = sum(i.count for i in panels) + len(endpoints)
    assets = _assets(panels, 5) + [e.host for e in endpoints[:5]]
    internal = _internal(assets)
    return AttackPath(
        key="admin_open",
        title=(
            "Management interfaces answer across the internal network"
            if internal
            else "Management interfaces answer from the public internet"
        ),
        detail=(
            f"{total} administrative interface{'s' if total != 1 else ''} responded "
            "with no gateway in front."
        ),
        severity=Severity.MEDIUM.value if not panels else Severity.HIGH.value,
        evidence=[i.name for i in panels[:4]] + [e.path for e in endpoints[:3]],
        assets=list(dict.fromkeys(assets))[:8],
        count=total,
    )


def _origin_exposed(source: ReportSource, _issues: list[Issue]) -> AttackPath | None:
    candidates = source.origin_candidates
    if not candidates:
        return None
    return AttackPath(
        key="origin_exposed",
        title="Origin servers answer outside the CDN",
        detail=(
            f"{len(candidates)} address{'es' if len(candidates) != 1 else ''} serve the "
            "same content as a hostname behind a CDN or WAF. Requests to the address "
            "bypass the edge."
        ),
        severity=Severity.HIGH.value,
        evidence=[
            f"{ip} matches {hosts[0]} on {kind}"
            for ip, kind, _digest, hosts in candidates[:4]
            if hosts
        ],
        assets=[ip for ip, _kind, _digest, _hosts in candidates[:8]],
        count=len(candidates),
    )


def _sensitive_services(
    source: ReportSource, _issues: list[Issue]
) -> AttackPath | None:
    exposed = [s for s in source.sensitive_services if not s.is_http]
    if not exposed:
        return None
    names = sorted({s.service_name or str(s.port) for s in exposed})
    internal = source.internal_estate
    where = "on the internal network" if internal else "from the internet"
    return AttackPath(
        key="sensitive_services",
        title=f"Administrative and data services are reachable {where}",
        detail=(
            f"{len(exposed)} administrative or data service{'s' if len(exposed) != 1 else ''} "
            f"answered a connection {where}: {', '.join(names[:6])}."
        ),
        severity=Severity.HIGH.value,
        evidence=[
            f"{s.ip}:{s.port} {s.service_name or ''}".strip() for s in exposed[:5]
        ],
        assets=[f"{s.ip}:{s.port}" for s in exposed[:8]],
        count=len(exposed),
    )


def _database_exposed(source: ReportSource, _issues: list[Issue]) -> AttackPath | None:
    rows = [
        s for s in source.service_rows if s.service_class == ServiceClass.DATABASE.value
    ]
    if not rows:
        return None
    internal = source.internal_estate
    return AttackPath(
        key="database_exposed",
        title=(
            "Database ports answer across the internal network"
            if internal
            else "Database ports answer from outside the network"
        ),
        detail=(
            f"{len(rows)} database service{'s' if len(rows) != 1 else ''} accepted a "
            f"connection {'from the internal network' if internal else 'from the internet'}."
        ),
        severity=Severity.HIGH.value,
        evidence=[f"{s.ip}:{s.port} {s.service_name or ''}".strip() for s in rows[:5]],
        assets=[f"{s.ip}:{s.port}" for s in rows[:8]],
        count=len(rows),
    )


def _expired_certificates(
    source: ReportSource, _issues: list[Issue]
) -> AttackPath | None:
    live = {h.name for h in source.host_rows if h.status}
    expired = [
        c for c in source.certificates if c.expired and (not live or c.host in live)
    ]
    if not expired:
        return None
    return AttackPath(
        key="expired_certificates",
        title="Web assets serve an expired certificate",
        detail=(
            f"{len(expired)} web asset{'s' if len(expired) != 1 else ''} answered over TLS "
            "with an expired certificate."
        ),
        severity=Severity.MEDIUM.value,
        evidence=[
            f"{c.host} expired {c.not_after:%d %b %Y}"
            for c in expired[:5]
            if c.not_after
        ],
        assets=[c.host for c in expired[:8]],
        count=len(expired),
    )


_RULES: tuple[Callable[[ReportSource, list[Issue]], AttackPath | None], ...] = (
    _kev_live,
    _default_credentials,
    _injection,
    _origin_exposed,
    _takeover,
    _exposed_data,
    _database_exposed,
    _sensitive_services,
    _admin_open,
    _expired_certificates,
)

_ORDER = {
    Severity.CRITICAL.value: 0,
    Severity.HIGH.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.LOW.value: 3,
}


def attack_paths(source: ReportSource, issues: list[Issue]) -> list[AttackPath]:
    found = [path for rule in _RULES if (path := rule(source, issues))]
    found.sort(key=lambda p: (_ORDER.get(p.severity, 4), -p.count))
    return found
