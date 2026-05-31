"""Server-side filtering, signal predicates and sorting for the targets list."""

from datetime import timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import Select, and_, case, exists, func, or_
from sqlalchemy.sql.elements import ColumnElement

from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.models import Target
from shared.models.tag import TargetTag
from shared.models.target import TargetOrganization
from shared.models.whois import WhoisRecord
from shared.utils.datetime import utc_now

SignalName = Literal["expiring", "attention", "awaiting", "enriched"]
SortKey = Literal["updated", "created", "name", "type", "expiry", "enrichment"]
SortDir = Literal["asc", "desc"]

EXPIRY_WINDOW_DAYS = 30

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


_SIGNAL_EXPR = {
    "expiring": expiring_expr,
    "attention": attention_expr,
    "awaiting": awaiting_expr,
    "enriched": enriched_expr,
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
    # id tiebreaker keeps pagination deterministic
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
    ]
