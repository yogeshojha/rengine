from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import (
    Text,
    and_,
    any_,
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
from shared.models.interest import InterestSignal
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage

from .scope import QueryScope, ScopeLike, scope_of

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


def _one_target(scope: QueryScope, column):
    """The target these scans belong to."""
    single = scope.single
    if single is None:
        return column
    return select(Scan.target_id).where(Scan.id == single).scalar_subquery()


def _per_scan(scope: QueryScope, column, build):
    """A scan-level fact evaluated against each row's own scan."""
    single = scope.single
    if single is not None:
        return build(single)
    if not scope.ids:
        return false()
    return or_(*[and_(column == sid, build(sid)) for sid in scope.ids])


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


def port_match(condition, scope: ScopeLike):
    def build(scan_id):
        addresses = (
            select(
                func.coalesce(
                    func.array_agg(distinct(Port.ip)), pg_array([], type_=Text)
                )
            )
            .where(Port.scan_id == scan_id, condition)
            .scalar_subquery()
        )
        return func.jsonb_exists_any(cast(Subdomain.resolved_ips, JSONB), addresses)

    return _per_scan(scope_of(scope), Subdomain.scan_id, build)


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


def _host_baseline(scan_id):
    """Whether an earlier scan of this target recorded any host."""
    earlier = aliased(Subdomain)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(Subdomain.discovered_at))
        .where(Subdomain.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def has_baseline(scope: ScopeLike):
    scope = scope_of(scope)
    if not scope.ids:
        return false()
    return or_(*[_host_baseline(sid) for sid in scope.ids])


def is_new(scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, Subdomain.scan_id, _host_baseline),
        not_(seen_earlier()),
    )


def _address_cutoff(scan_id):
    return (
        select(func.min(IpAddress.discovered_at))
        .where(IpAddress.scan_id == scan_id)
        .scalar_subquery()
    )


def _address_baseline(scan_id):
    """Whether an earlier scan of this target recorded any address."""
    earlier = aliased(IpAddress)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < _address_cutoff(scan_id),
        )
    )


def _address_seen_earlier(source, scan_id):
    earlier = aliased(IpAddress)
    return exists(
        select(1).where(
            earlier.target_id
            == select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery(),
            earlier.ip == source.c.ip,
            earlier.scan_id != scan_id,
            earlier.discovered_at < _address_cutoff(scan_id),
        )
    )


def _address_history(source, scope: QueryScope, *conditions):
    """History for an address is every target it serves, since the view folds them into one row."""
    earlier = aliased(IpAddress)
    return exists(
        select(1).where(
            earlier.target_id == any_(source.c.target_ids),
            not_(scope.match(earlier.scan_id)),
            earlier.discovered_at < source.c.first_seen,
            *[c(earlier) for c in conditions],
        )
    )


def address_is_new(source, scope: ScopeLike):
    scope = scope_of(scope)
    single = scope.single
    if single is not None:
        return and_(
            _address_baseline(single),
            not_(_address_seen_earlier(source, single)),
        )
    return and_(
        _address_history(source, scope),
        not_(_address_history(source, scope, lambda e: e.ip == source.c.ip)),
    )


def service_seen_earlier(source, scope: ScopeLike):
    scope = scope_of(scope)
    earlier = aliased(Port)
    return exists(
        select(1).where(
            earlier.target_id == source.c.target_id,
            earlier.ip == source.c.ip,
            earlier.number == source.c.port,
            not_(scope.match(earlier.scan_id)),
            earlier.discovered_at < source.c.discovered_at,
        )
    )


def _service_baseline(scan_id):
    """Whether an earlier scan of this target recorded any port at all."""
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


def service_has_baseline(scope: ScopeLike):
    scope = scope_of(scope)
    if not scope.ids:
        return false()
    return or_(*[_service_baseline(sid) for sid in scope.ids])


def service_is_new(source, scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, source.c.scan_id, _service_baseline),
        not_(service_seen_earlier(source, scope)),
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


def sensitive(scope: ScopeLike):
    return port_match(Port.number.in_(SENSITIVE_PORTS), scope)


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


def asset_match(scope: ScopeLike, condition):
    return Subdomain.name.in_(
        select(HttpAsset.host).where(
            scope_of(scope).match(HttpAsset.scan_id), condition
        )
    )


def ip_text():
    return cast(Subdomain.resolved_ips, Text)


def vuln_on(scope: ScopeLike, *conditions):
    """A finding recorded by these scans, narrowed by the caller's asset join."""
    return exists(
        select(1).where(scope_of(scope).match(Vulnerability.scan_id), *conditions)
    )


def host_vuln(scope: ScopeLike, condition=None):
    clauses = [Vulnerability.host == Subdomain.name]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scope, *clauses)


def address_vuln(scope: ScopeLike, column, condition=None):
    clauses = [Vulnerability.ip == column]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scope, *clauses)


def service_vuln(scope: ScopeLike, ip_column, port_column, condition=None):
    clauses = [Vulnerability.ip == ip_column, Vulnerability.port == port_column]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scope, *clauses)


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


def _vuln_baseline(scan_id):
    """Whether an earlier scan of this target recorded any finding."""
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


def vuln_has_baseline(scope: ScopeLike):
    scope = scope_of(scope)
    if not scope.ids:
        return false()
    return or_(*[_vuln_baseline(sid) for sid in scope.ids])


def vuln_is_new(scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, Vulnerability.scan_id, _vuln_baseline),
        not_(vuln_seen_earlier()),
    )


def vuln_suppressed(scope: ScopeLike):
    """A reviewer set this finding aside."""
    scope = scope_of(scope)
    return exists(
        select(1).where(
            VulnerabilityTriage.target_id
            == _one_target(scope, Vulnerability.target_id),
            VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
            VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
        )
    )


def _vuln_eligible(scope: QueryScope):
    """Findings allowed to vouch: these scans, not informational, not set aside by a reviewer."""
    return (
        select(
            Vulnerability.id.label("id"),
            Vulnerability.matched_at.label("matched_at"),
            Vulnerability.template_id.label("template_id"),
            Vulnerability.cve_ids.label("cve_ids"),
            Vulnerability.cwe_ids.label("cwe_ids"),
        )
        .where(
            scope.match(Vulnerability.scan_id),
            Vulnerability.severity != Severity.INFO.value,
            not_(vuln_suppressed(scope)),
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


@lru_cache(maxsize=128)
def _corroborated_ids(scope: QueryScope):
    """Findings a different check confirms at the same location by naming the same CVE or CWE."""
    eligible = _vuln_eligible(scope)
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


def vuln_corroborated_ids(scope: ScopeLike):
    return _corroborated_ids(scope_of(scope))


def vuln_corroborated(scope: ScopeLike):
    return Vulnerability.id.in_(vuln_corroborated_ids(scope))


def vuln_state(scope: ScopeLike):
    """The review decision for this finding, defaulting to open when nobody has decided."""
    scope = scope_of(scope)
    return func.coalesce(
        select(VulnerabilityTriage.state)
        .where(
            VulnerabilityTriage.target_id
            == _one_target(scope, Vulnerability.target_id),
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


def _endpoint_baseline(scan_id):
    """Whether an earlier scan of this target recorded any endpoint."""
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


def endpoint_has_baseline(scope: ScopeLike):
    scope = scope_of(scope)
    if not scope.ids:
        return false()
    return or_(*[_endpoint_baseline(sid) for sid in scope.ids])


def endpoint_is_new(scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, Endpoint.scan_id, _endpoint_baseline),
        not_(endpoint_seen_earlier()),
    )


def endpoint_vuln(scope: ScopeLike, condition=None):
    """A finding this scan reported at this endpoint's location or on its host."""
    clauses = [
        or_(
            Vulnerability.http_asset_id == Endpoint.http_asset_id,
            Vulnerability.host == Endpoint.host,
        )
    ]
    if condition is not None:
        clauses.append(condition)
    return vuln_on(scope, *clauses)


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


def interest_signal(condition=None):
    stmt = select(1).where(
        InterestSignal.subdomain_id == Subdomain.id,
        InterestSignal.scan_id == Subdomain.scan_id,
    )
    if condition is not None:
        stmt = stmt.where(condition)
    return exists(stmt)


def interesting():
    return Subdomain.interest_score > 0
