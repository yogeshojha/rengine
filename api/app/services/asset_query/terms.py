from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Text, and_, cast, exists, false, func, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array

from shared.definitions.asset_query import FieldType, Op

from .ast import Compare
from .values import is_relative, like, moment, scaled_number, split_range

_ONE_DAY = timedelta(days=1)
_FLIPPED = {Op.GT: Op.LT, Op.GTE: Op.LTE, Op.LT: Op.GT, Op.LTE: Op.GTE}
_TRUTHY = {"yes", "true", "1", "any", "present"}
_FALSY = {"no", "false", "0", "none", "absent"}


def negate(expr):
    return not_(func.coalesce(expr, false()))


def threshold(col, op: Op, value):
    if op is Op.GT:
        return col > value
    if op is Op.GTE:
        return col >= value
    if op is Op.LT:
        return col < value
    if op is Op.LTE:
        return col <= value
    if op is Op.NE:
        return or_(col.is_(None), col != value)
    return col == value


def string_match(col, cmp: Compare):
    if cmp.op is Op.MATCH:
        return or_(*[col.ilike(like(v), escape="\\") for v in cmp.values])
    lowered = [v.lower() for v in cmp.values]
    if cmp.op is Op.EQ:
        return func.lower(col).in_(lowered)
    if cmp.op is Op.NE:
        return or_(col.is_(None), negate(func.lower(col).in_(lowered)))
    matched = or_(*[col.op("~*")(v) for v in cmp.values])
    if cmp.op is Op.RE:
        return matched
    return or_(col.is_(None), negate(matched))


def number_match(col, cmp: Compare, coerce):
    if cmp.op in (Op.MATCH, Op.EQ, Op.NE):
        branches = []
        for raw in cmp.values:
            bounds = split_range(raw)
            if bounds is None:
                branches.append(col == coerce(raw))
            else:
                branches.append(
                    and_(col >= coerce(bounds[0]), col <= coerce(bounds[1]))
                )
        matched = or_(*branches)
        return or_(col.is_(None), negate(matched)) if cmp.op is Op.NE else matched
    return threshold(col, cmp.op, coerce(cmp.values[0]))


def date_match(col, cmp: Compare, now: datetime, *, future: bool):
    raw = cmp.values[0]
    instant = moment(raw, cmp.start, cmp.end)
    if not is_relative(raw):
        if cmp.op in (Op.MATCH, Op.EQ):
            return and_(col >= instant, col < instant + _ONE_DAY)
        return threshold(col, cmp.op, instant)
    span = now - instant
    boundary = now + span if future else now - span
    if cmp.op in (Op.MATCH, Op.EQ):
        return col <= boundary if future else col >= boundary
    op = cmp.op if future else _FLIPPED.get(cmp.op, cmp.op)
    return threshold(col, op, boundary)


def json_array_match(col, cmp: Compare):
    if cmp.op is Op.EQ:
        return func.jsonb_exists_any(cast(col, JSONB), pg_array(list(cmp.values)))
    if cmp.op in (Op.RE, Op.NRE):
        element = (
            func.jsonb_array_elements_text(cast(col, JSONB))
            .table_valued("value")
            .alias("element")
        )
        found = exists(
            select(1)
            .select_from(element)
            .where(or_(*[element.c.value.op("~*")(v) for v in cmp.values]))
        )
        return negate(found) if cmp.op is Op.NRE else found
    matched = or_(*[cast(col, Text).ilike(like(v), escape="\\") for v in cmp.values])
    return negate(matched) if cmp.op is Op.NE else matched


def tri_state(cmp: Compare) -> bool | None:
    if len(cmp.values) != 1:
        return None
    value = cmp.values[0].lower()
    if value in _TRUTHY:
        return True
    return False if value in _FALSY else None


def int_coerce(cmp: Compare):
    def coerce(raw: str) -> int:
        return int(scaled_number(raw, FieldType.NUMBER, cmp.start, cmp.end))

    return coerce


def scaled_coerce(cmp: Compare, kind: FieldType):
    def coerce(raw: str) -> float:
        return scaled_number(raw, kind, cmp.start, cmp.end)

    return coerce
