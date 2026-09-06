from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import (
    Text,
    and_,
    cast,
    distinct,
    exists,
    false,
    func,
    literal,
    not_,
    or_,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import aliased

from shared.definitions.endpoints import ARCHIVE_SOURCES, LINKED_SOURCES
from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.vulnerabilities import SUPPRESSED_STATES, Severity, VulnState
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
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


def address_seen_earlier(ip_column, scan_id):
    earlier = aliased(IpAddress)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(IpAddress.discovered_at))
        .where(IpAddress.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.ip == ip_column,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def address_has_baseline(scan_id):
    """Whether an earlier scan of this target recorded any address. Scan-level, never per row."""
    earlier = aliased(IpAddress)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(IpAddress.discovered_at))
        .where(IpAddress.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def address_is_new(ip_column, scan_id):
    return and_(
        address_has_baseline(scan_id), not_(address_seen_earlier(ip_column, scan_id))
    )


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


def _vuln_eligible(scan_id):
    """Findings allowed to vouch: this scan, not informational, not set aside by a reviewer."""
    return (
        select(
            Vulnerability.id.label("id"),
            Vulnerability.matched_at.label("matched_at"),
            Vulnerability.template_id.label("template_id"),
            Vulnerability.cve_ids.label("cve_ids"),
            Vulnerability.cwe_ids.label("cwe_ids"),
        )
        .where(
            Vulnerability.scan_id == scan_id,
            Vulnerability.severity != Severity.INFO.value,
            not_(vuln_suppressed(scan_id)),
        )
        .cte("vuln_eligible")
    )


def _vuln_keys(source, column, prefix: str, name: str):
    value = func.jsonb_array_elements_text(cast(column, JSONB)).column_valued(name)
    return select(
        source.c.id.label("id"),
        source.c.matched_at.label("matched_at"),
        source.c.template_id.label("template_id"),
        (literal(prefix) + value).label("key"),
    ).select_from(source)


# cached so both the filter and the sort share one CTE object; two would collide by name
@lru_cache(maxsize=128)
def vuln_corroborated_ids(scan_id):
    """Findings a different check confirms at the same location by naming the same CVE or CWE."""
    eligible = _vuln_eligible(scan_id)
    signals = union_all(
        _vuln_keys(eligible, eligible.c.cve_ids, "cve:", "cve_key"),
        _vuln_keys(eligible, eligible.c.cwe_ids, "cwe:", "cwe_key"),
    ).cte("vuln_signal")
    agreed = (
        select(signals.c.matched_at, signals.c.key)
        .group_by(signals.c.matched_at, signals.c.key)
        .having(func.count(distinct(signals.c.template_id)) > 1)
        .cte("vuln_agreed")
    )
    return (
        select(signals.c.id)
        .select_from(signals)
        .join(
            agreed,
            and_(
                signals.c.matched_at == agreed.c.matched_at,
                signals.c.key == agreed.c.key,
            ),
        )
        .distinct()
    )


def vuln_corroborated(scan_id):
    return Vulnerability.id.in_(vuln_corroborated_ids(scan_id))


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


def endpoint_seen_earlier():
    earlier = aliased(Endpoint)
    return exists(
        select(1).where(
            earlier.target_id == Endpoint.target_id,
            earlier.signature == Endpoint.signature,
            earlier.scan_id != Endpoint.scan_id,
            earlier.discovered_at < Endpoint.discovered_at,
        )
    )


def endpoint_has_baseline(scan_id):
    """Whether an earlier scan of this target recorded any endpoint. Scan-level, never per row."""
    earlier = aliased(Endpoint)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(Endpoint.discovered_at))
        .where(Endpoint.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def endpoint_is_new(scan_id):
    return and_(endpoint_has_baseline(scan_id), not_(endpoint_seen_earlier()))


def endpoint_vuln(scan_id, condition=None):
    """A finding this scan reported at this endpoint's location or on its host."""
    clauses = [
        or_(
            Vulnerability.http_asset_id == Endpoint.http_asset_id,
            Vulnerability.host == Endpoint.host,
        )
    ]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scan_id, *clauses)


def endpoint_source(*names: str):
    """The endpoint carries at least one of these discovery sources."""
    return func.jsonb_exists_any(cast(Endpoint.sources, JSONB), pg_array(list(names)))


def endpoint_linked():
    return endpoint_source(*LINKED_SOURCES)


def endpoint_orphan():
    """Discovered, but nothing on the live site points at it."""
    return and_(not_(endpoint_linked()), Endpoint.found_on.is_(None))


def endpoint_archive_only():
    """An archive recorded it and this scan could not reach it."""
    return and_(
        endpoint_source(*ARCHIVE_SOURCES),
        not_(endpoint_linked()),
        or_(
            Endpoint.is_probed.is_(False),
            Endpoint.status_code.is_(None),
            Endpoint.status_code >= HTTP_CLIENT,
        ),
    )


def endpoint_status_class(name: str):
    if name == "none":
        return Endpoint.status_code.is_(None)
    bucket = STATUS_BUCKETS.get(name)
    if bucket is None:
        return false()
    return and_(Endpoint.status_code >= bucket[0], Endpoint.status_code < bucket[1])
