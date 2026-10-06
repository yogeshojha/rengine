from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import (
    Text,
    and_,
    any_,
    case,
    cast,
    distinct,
    exists,
    false,
    func,
    literal,
    not_,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import BIT, INET, JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import aliased

from shared.definitions import domain_posture as posture_defs
from shared.definitions import hygiene as hygiene_defs
from shared.definitions.compare import AUTH_STATUS
from shared.definitions.correlation import SCREENSHOT_DISTANCE
from shared.definitions.dashboard import EXPIRING_DAYS
from shared.definitions.endpoints import ARCHIVE_SOURCES, LINKED_SOURCES
from shared.definitions.evidence import Evidence
from shared.definitions.issue_trackers import TICKETED_STATES, FilingState
from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.vulnerabilities import SUPPRESSED_STATES, Severity, VulnState
from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.interest import InterestSignal
from shared.models.ip_address import IpAddress
from shared.models.issue_tracker import TrackedIssue, TrackedIssueFinding
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.secret import Secret
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage

from .scope import QueryScope, ScopeLike, scope_of
from .terms import array_elements

HTTP_OK = 200
HTTP_REDIRECT = 300
HTTP_CLIENT = 400
HTTP_SERVER = 500
HTTP_MAX = 600
STATUS_BUCKETS = {
    "2xx": (HTTP_OK, HTTP_REDIRECT),
    "3xx": (HTTP_REDIRECT, HTTP_CLIENT),
    "4xx": (HTTP_CLIENT, HTTP_SERVER),
    "5xx": (HTTP_SERVER, HTTP_MAX),
}
STATUS_LABELS = {
    "2xx": "2xx OK",
    "3xx": "3xx Redirect",
    "4xx": "4xx Client",
    "5xx": "5xx Server",
    "none": "No HTTP",
}
AUTH_RE = "login|sign ?in|log ?in|admin|dashboard|portal|console|authenticat"


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
    """Earlier rows of any target the address serves."""
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


def service_is_new(source, scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, source.c.scan_id, _service_baseline),
        not_(service_seen_earlier(source, scope)),
    )


def live():
    return and_(Subdomain.http_status >= HTTP_OK, Subdomain.http_status < HTTP_CLIENT)


def answered():
    return Subdomain.http_status.isnot(None)


IP_CHARS_RE = r"^[0-9a-fA-F:.]+$"


def inet_of(column):
    """A stored address as INET, NULL for non-address text."""
    return cast(case((column.op("~")(IP_CHARS_RE), column), else_=None), INET)


def auth():
    return or_(
        Subdomain.http_status.in_(AUTH_STATUS),
        Subdomain.page_title.op("~*")(AUTH_RE),
    )


def resolved():
    return func.json_array_length(Subdomain.resolved_ips) > 0


def render_distance(column, value: int):
    return func.bit_count(cast(column.op("#")(literal(value)), BIT(64)))


def renders_like(column, value: int):
    return render_distance(column, value) <= SCREENSHOT_DISTANCE


def sensitive(scope: ScopeLike):
    return port_match(Port.number.in_(SENSITIVE_PORTS), scope)


def issues(now: datetime, scope: ScopeLike):
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
        sensitive(scope),
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


def software_seen_earlier():
    earlier = aliased(SoftwareCve)
    return exists(
        select(1).where(
            earlier.target_id == SoftwareCve.target_id,
            earlier.fingerprint == SoftwareCve.fingerprint,
            earlier.scan_id != SoftwareCve.scan_id,
            earlier.discovered_at < SoftwareCve.discovered_at,
        )
    )


def _software_baseline(scan_id):
    earlier = aliased(SoftwareCve)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(SoftwareCve.discovered_at))
        .where(SoftwareCve.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def software_is_new(scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, SoftwareCve.scan_id, _software_baseline),
        not_(software_seen_earlier()),
    )


def secret_seen_earlier():
    earlier = aliased(Secret)
    return exists(
        select(1).where(
            earlier.target_id == Secret.target_id,
            earlier.fingerprint == Secret.fingerprint,
            earlier.scan_id != Secret.scan_id,
            earlier.discovered_at < Secret.discovered_at,
        )
    )


def _secret_baseline(scan_id):
    earlier = aliased(Secret)
    target = select(Scan.target_id).where(Scan.id == scan_id).scalar_subquery()
    cutoff = (
        select(func.min(Secret.discovered_at))
        .where(Secret.scan_id == scan_id)
        .scalar_subquery()
    )
    return exists(
        select(1).where(
            earlier.target_id == target,
            earlier.scan_id != scan_id,
            earlier.discovered_at < cutoff,
        )
    )


def secret_is_new(scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, Secret.scan_id, _secret_baseline),
        not_(secret_seen_earlier()),
    )


def vuln_suppressed(scope: ScopeLike):
    """A reviewer set this finding aside, or the finding it confirms."""
    scope = scope_of(scope)
    source = aliased(Vulnerability)
    return exists(
        select(1)
        .select_from(VulnerabilityTriage)
        .outerjoin(source, source.id == Vulnerability.replayed_from_id)
        .where(
            VulnerabilityTriage.target_id
            == _one_target(scope, Vulnerability.target_id),
            VulnerabilityTriage.fingerprint.in_(
                [Vulnerability.fingerprint, func.coalesce(source.fingerprint, "")]
            ),
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
            Vulnerability.host.label("host"),
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
    element = array_elements(column, name)
    return (
        select(
            source.c.id.label("id"),
            source.c.matched_at.label("matched_at"),
            source.c.template_id.label("template_id"),
            (literal(prefix) + element.c.value).label("key"),
        )
        .select_from(source)
        .join(element, true())
    )


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
    by_check = (
        select(signals.c.id)
        .select_from(signals)
        .join(
            agreed,
            and_(
                signals.c.matched_at == agreed.c.matched_at,
                signals.c.key == agreed.c.key,
            ),
        )
    )
    by_software = (
        select(eligible.c.id)
        .select_from(eligible)
        .join(
            SoftwareCve,
            and_(
                scope.match(SoftwareCve.scan_id),
                SoftwareCve.host.isnot(None),
                SoftwareCve.host == eligible.c.host,
                func.jsonb_exists(cast(eligible.c.cve_ids, JSONB), SoftwareCve.cve),
            ),
        )
    )
    agreeing = union_all(by_check, by_software).subquery("vuln_agreeing")
    return select(agreeing.c.id).distinct()


def vuln_corroborated_ids(scope: ScopeLike):
    return _corroborated_ids(scope_of(scope))


def vuln_corroborated(scope: ScopeLike):
    return Vulnerability.id.in_(vuln_corroborated_ids(scope))


def vuln_evidence(scope: ScopeLike, value: str):
    """One rung of the ladder. A proven finding is not also counted as cross-checked."""
    corroborated = Vulnerability.id.in_(vuln_corroborated_ids(scope))
    if value == Evidence.PROVEN.value:
        return Vulnerability.evidence == Evidence.PROVEN.value
    if value == Evidence.CROSS_CHECKED.value:
        return and_(Vulnerability.evidence != Evidence.PROVEN.value, corroborated)
    if value == Evidence.OBSERVED.value:
        return and_(
            Vulnerability.evidence == Evidence.OBSERVED.value, not_(corroborated)
        )
    return false()


def vuln_ticketed(scope: ScopeLike, categories: list[str] | None = None):
    """A tracker issue holds this finding, in one of the named remote categories."""
    scope = scope_of(scope)
    conditions = [
        TrackedIssueFinding.target_id == _one_target(scope, Vulnerability.target_id),
        TrackedIssueFinding.fingerprint == Vulnerability.fingerprint,
    ]
    if categories is None:
        conditions.append(TrackedIssue.state.in_(TICKETED_STATES))
    else:
        conditions.append(TrackedIssue.state == FilingState.FILED.value)
        conditions.append(TrackedIssue.remote_category.in_(categories))
    return exists(
        select(1)
        .select_from(TrackedIssueFinding)
        .join(TrackedIssue, TrackedIssue.id == TrackedIssueFinding.issue_id)
        .where(*conditions)
    )


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


def endpoint_baseline(scan_id):
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


def endpoint_is_new(scope: ScopeLike):
    scope = scope_of(scope)
    return and_(
        _per_scan(scope, Endpoint.scan_id, endpoint_baseline),
        not_(endpoint_seen_earlier()),
    )


def endpoint_vuln(scope: ScopeLike, condition=None):
    """A finding this scan reported at this endpoint's location or on its host."""
    found = [scope_of(scope).match(Vulnerability.scan_id)]
    if condition is not None:
        found.append(condition)

    def carried(own, column):
        reported = select(column).where(*found, column.isnot(None)).correlate(None)
        return and_(own.isnot(None), own.in_(reported))

    return or_(
        carried(Endpoint.http_asset_id, Vulnerability.http_asset_id),
        carried(Endpoint.host, Vulnerability.host),
    )


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


# ---------- hygiene ----------


def hygiene_length(column):
    """Length of a JSON list column, 0 for NULL or a stray scalar."""
    value = cast(column, JSONB)
    return case(
        (func.jsonb_typeof(value) == "array", func.jsonb_array_length(value)),
        else_=0,
    )


def hygiene_clean():
    return and_(
        hygiene_length(Subdomain.hygiene_checked) > 0,
        hygiene_length(Subdomain.hygiene_issues) == 0,
    )


def hygiene(values: list[str]):
    """Hosts failing any of the checks."""
    keys: set[str] = set()
    parts = []
    issues = cast(Subdomain.hygiene_issues, JSONB)
    for raw in values:
        value = raw.lower()
        if value == hygiene_defs.ANY:
            parts.append(hygiene_length(Subdomain.hygiene_issues) > 0)
        elif value == hygiene_defs.NONE:
            parts.append(hygiene_clean())
        elif value in hygiene_defs.KEYS_BY_TONE:
            keys.update(hygiene_defs.KEYS_BY_TONE[value])
        else:
            keys.add(value)
    if keys:
        parts.append(func.jsonb_exists_any(issues, pg_array(sorted(keys))))
    return or_(*parts) if parts else false()


def hygiene_check(key: str):
    return func.jsonb_exists(cast(Subdomain.hygiene_issues, JSONB), key)


def hygiene_applies(key: str):
    return func.jsonb_exists(cast(Subdomain.hygiene_checked, JSONB), key)


# ---------- domain posture ----------


def posture_clean():
    return and_(
        hygiene_length(Subdomain.posture_checked) > 0,
        hygiene_length(Subdomain.posture_issues) == 0,
    )


def posture(values: list[str]):
    """Hosts whose zone fails any of the checks."""
    keys: set[str] = set()
    parts = []
    issues = cast(Subdomain.posture_issues, JSONB)
    for raw in values:
        value = raw.lower()
        if value == posture_defs.ANY:
            parts.append(hygiene_length(Subdomain.posture_issues) > 0)
        elif value == posture_defs.NONE:
            parts.append(posture_clean())
        elif value in posture_defs.KEYS_BY_TONE:
            keys.update(posture_defs.KEYS_BY_TONE[value])
        else:
            keys.add(value)
    if keys:
        parts.append(func.jsonb_exists_any(issues, pg_array(sorted(keys))))
    return or_(*parts) if parts else false()


def posture_check(key: str):
    return func.jsonb_exists(cast(Subdomain.posture_issues, JSONB), key)


def posture_applies(key: str):
    return func.jsonb_exists(cast(Subdomain.posture_checked, JSONB), key)


def resolved_by(scope: QueryScope, ip, condition):
    """The address is one that a host matching `condition` resolves to."""
    ips = array_elements(Subdomain.resolved_ips, "resolved")
    return ip.in_(
        select(ips.c.value)
        .select_from(Subdomain)
        .join(ips, true())
        .where(scope.match(Subdomain.scan_id), condition)
    )
