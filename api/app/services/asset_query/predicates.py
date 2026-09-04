from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Text, and_, cast, exists, false, func, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import aliased

from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.vulnerabilities import SUPPRESSED_STATES, VulnState
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage

HTTP_OK = 200
HTTP_REDIRECT = 300
HTTP_CLIENT = 400
HTTP_SERVER = 500
HTTP_MAX = 600
AUTH_STATUS = (401, 403)
STATUS_BUCKETS = {
    "2xx": (HTTP_OK, HTTP_REDIRECT),
    "3xx": (HTTP_REDIRECT, HTTP_CLIENT),
    "4xx": (HTTP_CLIENT, HTTP_SERVER),
    "5xx": (HTTP_SERVER, HTTP_MAX),
}
AUTH_RE = "login|sign ?in|log ?in|admin|dashboard|portal|console|authenticat"
EXPIRING_DAYS = 30


def status_class(name: str):
    if name == "none":
        return Subdomain.http_status.is_(None)
    bucket = STATUS_BUCKETS.get(name)
    if bucket is None:
        return false()
    return and_(Subdomain.http_status >= bucket[0], Subdomain.http_status < bucket[1])


def cert_state(name: str, now: datetime):
    if name == "self-signed":
        return Subdomain.tls_self_signed.is_(True)
    if name == "expired":
        return or_(
            Subdomain.tls_expired.is_(True),
            and_(Subdomain.tls_not_after.isnot(None), Subdomain.tls_not_after < now),
        )
    if name == "expiring":
        return and_(
            Subdomain.tls_not_after.isnot(None),
            Subdomain.tls_expired.isnot(True),
            Subdomain.tls_not_after >= now,
            Subdomain.tls_not_after < now + timedelta(days=EXPIRING_DAYS),
        )
    if name == "valid":
        return and_(
            Subdomain.tls_not_after.isnot(None),
            Subdomain.tls_not_after >= now + timedelta(days=EXPIRING_DAYS),
            Subdomain.tls_self_signed.isnot(True),
        )
    return false()


def port_match(condition):
    return exists().where(
        and_(
            Port.scan_id == Subdomain.scan_id,
            condition,
            func.jsonb_exists(cast(Subdomain.resolved_ips, JSONB), Port.ip),
        )
    )


def seen_earlier():
    earlier = aliased(Subdomain)
    return exists(
        select(1).where(
            earlier.target_id == Subdomain.target_id,
            earlier.name == Subdomain.name,
            earlier.scan_id != Subdomain.scan_id,
            earlier.discovered_at < Subdomain.discovered_at,
        )
    )


def has_baseline():
    earlier = aliased(Subdomain)
    return exists(
        select(1).where(
            earlier.target_id == Subdomain.target_id,
            earlier.scan_id != Subdomain.scan_id,
            earlier.discovered_at < Subdomain.discovered_at,
        )
    )


def is_new():
    return and_(has_baseline(), not_(seen_earlier()))


def service_seen_earlier(source, scan_id):
    earlier = aliased(Port)
    return exists(
        select(1).where(
            earlier.target_id == source.c.target_id,
            earlier.ip == source.c.ip,
            earlier.number == source.c.port,
            earlier.scan_id != scan_id,
            earlier.discovered_at < source.c.discovered_at,
        )
    )


def service_has_baseline(scan_id):
    """Whether an earlier scan of this target recorded any port at all.

    Scan-level, so it must not correlate with the row: joining every port of this
    scan against every port of the target on target_id alone is quadratic.
    """
    earlier = aliased(Port)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(Port.discovered_at))
        .where(Port.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def service_is_new(source, scan_id):
    return and_(
        service_has_baseline(scan_id),
        not_(service_seen_earlier(source, scan_id)),
    )


def live():
    return and_(Subdomain.http_status >= HTTP_OK, Subdomain.http_status < HTTP_CLIENT)


def auth():
    return or_(
        Subdomain.http_status.in_(AUTH_STATUS),
        Subdomain.page_title.op("~*")(AUTH_RE),
    )


def resolved():
    return func.jsonb_array_length(cast(Subdomain.resolved_ips, JSONB)) > 0


def sensitive():
    return port_match(Port.number.in_(SENSITIVE_PORTS))


def issues(now: datetime):
    return or_(
        cert_state("expired", now),
        cert_state("expiring", now),
        Subdomain.tls_self_signed.is_(True),
        Subdomain.http_status >= HTTP_SERVER,
        and_(
            live(),
            Subdomain.waf.is_(None),
            Subdomain.is_cdn.is_(False),
        ),
        sensitive(),
    )


def asset_match(scan_id, condition):
    return Subdomain.name.in_(
        select(HttpAsset.host).where(HttpAsset.scan_id == scan_id, condition)
    )


def ip_text():
    return cast(Subdomain.resolved_ips, Text)


def vuln_on(scan_id, *conditions):
    """A finding recorded by this scan, narrowed by the caller's asset join."""
    return exists(select(1).where(Vulnerability.scan_id == scan_id, *conditions))


def host_vuln(scan_id, condition=None):
    clauses = [Vulnerability.host == Subdomain.name]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scan_id, *clauses)


def address_vuln(scan_id, column, condition=None):
    clauses = [Vulnerability.ip == column]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scan_id, *clauses)


def service_vuln(scan_id, ip_column, port_column, condition=None):
    clauses = [Vulnerability.ip == ip_column, Vulnerability.port == port_column]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scan_id, *clauses)


def vuln_seen_earlier():
    earlier = aliased(Vulnerability)
    return exists(
        select(1).where(
            earlier.target_id == Vulnerability.target_id,
            earlier.fingerprint == Vulnerability.fingerprint,
            earlier.scan_id != Vulnerability.scan_id,
            earlier.discovered_at < Vulnerability.discovered_at,
        )
    )


def vuln_has_baseline(scan_id):
    """Whether an earlier scan of this target recorded any finding. Scan-level, never per row."""
    earlier = aliased(Vulnerability)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(Vulnerability.discovered_at))
        .where(Vulnerability.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def vuln_is_new(scan_id):
    return and_(vuln_has_baseline(scan_id), not_(vuln_seen_earlier()))


def vuln_suppressed(scan_id):
    """A reviewer set this finding aside. An EXISTS so Postgres can hash-join it, not probe per row."""
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    return exists(
        select(1).where(
            VulnerabilityTriage.target_id == target,
            VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
            VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
        )
    )


def vuln_state(scan_id):
    """The review decision for this finding, defaulting to open when nobody has decided."""
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    return func.coalesce(
        select(VulnerabilityTriage.state)
        .where(
            VulnerabilityTriage.target_id == target,
            VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
        )
        .limit(1)
        .scalar_subquery(),
        VulnState.OPEN.value,
    )
