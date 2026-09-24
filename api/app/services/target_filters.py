from datetime import timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import Select, and_, case, exists, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from shared.definitions.vulnerabilities import SUPPRESSED_STATES, Severity
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.models import Target
from shared.models.scan import Scan
from shared.models.tag import TargetTag
from shared.models.target import TargetOrganization
from shared.models.vulnerability import Vulnerability, VulnerabilityTriage
from shared.models.whois import WhoisRecord
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now

SignalName = Literal[
    "expiring",
    "attention",
    "awaiting",
    "enriched",
    "monitored",
    "unscanned",
    "stale",
    "critical",
    "high",
]
SortKey = Literal["updated", "created", "name", "type", "expiry", "enrichment"]
SortDir = Literal["asc", "desc"]

EXPIRY_WINDOW_DAYS = 30
STALE_DAYS = 30

_DNS_TYPES = (TargetType.DOMAIN, TargetType.URL)
_BGP_TYPES = (TargetType.IP, TargetType.IP_RANGE, TargetType.ASN)
_AWAITING_STATUSES = (TaskStatus.PENDING, TaskStatus.QUERYING)


def with_whois_join(query: Select) -> Select:
    return query.join(
        WhoisRecord, Target.whois_record_id == WhoisRecord.id, isouter=True
    )


def _dns_applies() -> ColumnElement[bool]:
    return Target.target_type.in_(_DNS_TYPES)


def _bgp_applies() -> ColumnElement[bool]:
    return Target.target_type.in_(_BGP_TYPES)


def expiring_expr() -> ColumnElement[bool]:
    cutoff = utc_now() + timedelta(days=EXPIRY_WINDOW_DAYS)
    return and_(
        WhoisRecord.expiration_date.is_not(None),
        WhoisRecord.expiration_date <= cutoff,
    )


def failed_expr() -> ColumnElement[bool]:
    return or_(
        Target.whois_status == TaskStatus.FAILED,
        and_(_dns_applies(), Target.dns_status == TaskStatus.FAILED),
        and_(_bgp_applies(), Target.bgp_status == TaskStatus.FAILED),
    )


def awaiting_expr() -> ColumnElement[bool]:
    return or_(
        Target.whois_status.in_(_AWAITING_STATUSES),
        and_(_dns_applies(), Target.dns_status.in_(_AWAITING_STATUSES)),
        and_(_bgp_applies(), Target.bgp_status.in_(_AWAITING_STATUSES)),
    )


def enriched_expr() -> ColumnElement[bool]:
    return and_(
        Target.whois_status == TaskStatus.SUCCESS,
        or_(~_dns_applies(), Target.dns_status == TaskStatus.SUCCESS),
        or_(~_bgp_applies(), Target.bgp_status == TaskStatus.SUCCESS),
    )


def attention_expr() -> ColumnElement[bool]:
    return or_(failed_expr(), expiring_expr())


def monitored_expr() -> ColumnElement[bool]:
    return Target.new_checks.is_(True)


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


def unscanned_expr() -> ColumnElement[bool]:
    return ~exists(select(1).where(Scan.target_id == Target.id, census_only()))


def stale_expr() -> ColumnElement[bool]:
    last = (
        select(func.max(_started()))
        .where(Scan.target_id == Target.id, census_only())
        .scalar_subquery()
    )
    return last < utc_now() - timedelta(days=STALE_DAYS)


def _latest_run():
    return (
        select(Scan.id)
        .where(Scan.target_id == Target.id, census_only())
        .order_by(_started().desc())
        .limit(1)
        .correlate(Target)
        .scalar_subquery()
    )


def severity_expr(severity: str) -> ColumnElement[bool]:
    suppressed = exists(
        select(1).where(
            VulnerabilityTriage.target_id == Vulnerability.target_id,
            VulnerabilityTriage.fingerprint == Vulnerability.fingerprint,
            VulnerabilityTriage.state.in_(SUPPRESSED_STATES),
        )
    )
    return exists(
        select(1).where(
            Vulnerability.scan_id == _latest_run(),
            Vulnerability.severity == severity,
            ~suppressed,
        )
    )


_SIGNAL_EXPR = {
    "expiring": expiring_expr,
    "attention": attention_expr,
    "awaiting": awaiting_expr,
    "enriched": enriched_expr,
    "monitored": monitored_expr,
    "unscanned": unscanned_expr,
    "stale": stale_expr,
    "critical": lambda: severity_expr(Severity.CRITICAL.value),
    "high": lambda: severity_expr(Severity.HIGH.value),
}


def signal_expr(signal: SignalName) -> ColumnElement[bool]:
    return _SIGNAL_EXPR[signal]()


def _type_order_expr() -> ColumnElement[int]:
    return case(
        (Target.target_type == TargetType.DOMAIN, 0),
        (Target.target_type == TargetType.URL, 1),
        (Target.target_type == TargetType.IP, 2),
        (Target.target_type == TargetType.IP_RANGE, 3),
        (Target.target_type == TargetType.ASN, 4),
        else_=99,
    )


def _enrichment_ratio_expr() -> ColumnElement[float]:
    done = (
        case((Target.whois_status == TaskStatus.SUCCESS, 1), else_=0)
        + case(
            (and_(_dns_applies(), Target.dns_status == TaskStatus.SUCCESS), 1), else_=0
        )
        + case(
            (and_(_bgp_applies(), Target.bgp_status == TaskStatus.SUCCESS), 1), else_=0
        )
    )
    total = 1 + case((_dns_applies(), 1), else_=0) + case((_bgp_applies(), 1), else_=0)
    return (done * 1.0) / total


def _sort_column(sort_by: SortKey):
    match sort_by:
        case "name":
            return func.lower(func.coalesce(Target.display_name, Target.target_value))
        case "type":
            return _type_order_expr()
        case "expiry":
            return WhoisRecord.expiration_date
        case "enrichment":
            return _enrichment_ratio_expr()
        case "created":
            return Target.created_at
        case _:
            return Target.updated_at


def apply_sort(query: Select, sort_by: SortKey, sort_dir: SortDir) -> Select:
    column = _sort_column(sort_by)
    ordering = column.desc() if sort_dir == "desc" else column.asc()
    return query.order_by(ordering.nulls_last(), Target.id)


def apply_filters(
    query: Select,
    *,
    search: str | None = None,
    organization_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
    target_type: TargetType | None = None,
    signal: SignalName | None = None,
) -> Select:
    if target_type:
        query = query.where(Target.target_type == target_type)

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Target.target_value.ilike(pattern),
                Target.display_name.ilike(pattern),
            )
        )

    if organization_ids:
        query = query.where(
            exists().where(
                and_(
                    TargetOrganization.target_id == Target.id,
                    TargetOrganization.organization_id.in_(organization_ids),
                )
            )
        )

    if tag_ids:
        query = query.where(
            exists().where(
                and_(
                    TargetTag.target_id == Target.id,
                    TargetTag.tag_id.in_(tag_ids),
                )
            )
        )

    if signal:
        query = query.where(signal_expr(signal))

    return query


def signal_count_columns() -> list:
    return [
        func.count().label("total"),
        func.coalesce(func.sum(case((expiring_expr(), 1), else_=0)), 0).label(
            "expiring"
        ),
        func.coalesce(func.sum(case((attention_expr(), 1), else_=0)), 0).label(
            "attention"
        ),
        func.coalesce(func.sum(case((awaiting_expr(), 1), else_=0)), 0).label(
            "awaiting"
        ),
        func.coalesce(func.sum(case((enriched_expr(), 1), else_=0)), 0).label(
            "enriched"
        ),
        func.coalesce(func.sum(case((monitored_expr(), 1), else_=0)), 0).label(
            "monitored"
        ),
        func.coalesce(func.sum(case((unscanned_expr(), 1), else_=0)), 0).label(
            "unscanned"
        ),
        func.coalesce(func.sum(case((stale_expr(), 1), else_=0)), 0).label("stale"),
        func.coalesce(
            func.sum(case((severity_expr(Severity.CRITICAL.value), 1), else_=0)), 0
        ).label("critical"),
        func.coalesce(
            func.sum(case((severity_expr(Severity.HIGH.value), 1), else_=0)), 0
        ).label("high"),
    ]
