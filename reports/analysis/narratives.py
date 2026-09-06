"""Chained observations. A list of findings is not a story; these are the stories."""

from __future__ import annotations

from collections.abc import Callable

from reports.analysis.brief import AttackPath
from reports.data.models import Issue
from reports.data.source import ReportSource
from shared.definitions.ports import ServiceClass
from shared.definitions.vulnerabilities import Severity

_OK = 2


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
        title="Weaknesses with confirmed exploitation are reachable",
        detail=(
            f"{total} observation{'s' if total != 1 else ''} across "
            f"{len(_assets(hits, 200))} hosts match checks on the Known Exploited "
            "Vulnerabilities catalogue. These are being used against real targets now, "
            "so exposure time is the whole risk."
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
        title="Services still answer to the credentials they shipped with",
        detail=(
            f"{total} service{'s' if total != 1 else ''} accepted a documented default "
            "account. No exploitation is required: the credentials are public."
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
        title="Hostnames point at infrastructure someone else can claim",
        detail=(
            f"{total} name{'s' if total != 1 else ''} resolve to a provider where the "
            "backing resource no longer exists. Anyone who registers it serves content "
            "on your domain, which defeats cookie scoping and certificate trust."
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
        title="Source, configuration or backups are served to the internet",
        detail=(
            f"{total} location{'s' if total != 1 else ''} return content that was not "
            "meant to be public. Files of this kind usually carry credentials or internal "
            "hostnames, which turns a single request into a foothold."
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
            f"{total} observation{'s' if total != 1 else ''} indicate input crossing into "
            f"a query, template or the filesystem. {worst.name} is the strongest of them."
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
    return AttackPath(
        key="admin_open",
        title="Management interfaces answer from the public internet",
        detail=(
            f"{total} administrative interface{'s' if total != 1 else ''} responded "
            "without a gateway in front. Each one is a credential-stuffing target and a "
            "published-exploit target at the same time."
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
        title="Origin servers answer directly, outside the CDN",
        detail=(
            f"{len(candidates)} address{'es' if len(candidates) != 1 else ''} serve the "
            "same content as a hostname that sits behind a CDN or WAF. Requesting the "
            "address directly bypasses every rule the edge enforces."
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
    return AttackPath(
        key="sensitive_services",
        title="Administrative and data services are reachable from the internet",
        detail=(
            f"{len(exposed)} service{'s' if len(exposed) != 1 else ''} of a kind that "
            "normally sits on a private network answered a connection: "
            f"{', '.join(names[:6])}. Each is an authentication surface with no web "
            "application firewall in front of it."
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
    return AttackPath(
        key="database_exposed",
        title="Database ports answer from outside the network",
        detail=(
            f"{len(rows)} database service{'s' if len(rows) != 1 else ''} accepted a "
            "connection from the internet. A database should not be addressable outside "
            "its own subnet even when authentication is enabled."
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
        title="Live hosts serve an expired certificate",
        detail=(
            f"{len(expired)} host{'s' if len(expired) != 1 else ''} answered over TLS "
            "with a certificate past its validity date. Users are trained through the "
            "resulting warning, which is the same warning an interception attack produces."
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
