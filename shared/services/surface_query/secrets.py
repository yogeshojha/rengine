"""Secret statement building, shared by the api's search and the worker's export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import case, select

from shared.definitions.asset_query import SECRET_QUERY
from shared.definitions.secrets import SecretState
from shared.models.secret import Secret
from shared.services.asset_query import (
    QueryScope,
    SecretQueryContext,
    compile_secret_query,
    parse_query,
)

if TYPE_CHECKING:
    from datetime import datetime

    from shared.models.secret import SecretFilter

_SORTS = {
    "kind": Secret.kind,
    "hosts": Secret.hosts,
    "sightings": Secret.sightings,
    "seen": Secret.discovered_at,
}

# exposed, expired, public
STATE_RANK = case(
    {
        SecretState.EXPOSED.value: 3,
        SecretState.EXPIRED.value: 2,
        SecretState.PUBLIC.value: 1,
    },
    value=Secret.state,
    else_=0,
)


def context(scope: QueryScope, now: datetime) -> SecretQueryContext:
    return SecretQueryContext(scope=scope, now=now)


def apply_filter(query, f: SecretFilter):
    if f.ids:
        query = query.where(Secret.id.in_(f.ids))
    return query


def order(query, f: SecretFilter):
    key = (f.sort or "state").lower()
    descending = (f.direction or "desc").lower() != "asc"
    if key == "state":
        rank = STATE_RANK.desc() if descending else STATE_RANK.asc()
        return query.order_by(
            rank, Secret.hosts.desc(), Secret.discovered_at.desc(), Secret.id
        )
    column = _SORTS.get(key)
    if column is None:
        return query.order_by(
            STATE_RANK.desc(),
            Secret.hosts.desc(),
            Secret.discovered_at.desc(),
            Secret.id,
        )
    ordered = column.desc() if descending else column.asc()
    return query.order_by(ordered, Secret.discovered_at.desc(), Secret.id)


def scoped(scope: QueryScope, f: SecretFilter, columns=None):
    base = select(Secret) if columns is None else select(*columns)
    return apply_filter(base.where(scope.match(Secret.scan_id)), f)


def compiled(scope: QueryScope, f: SecretFilter, now: datetime):
    return compile_secret_query(parse_query(f.q, SECRET_QUERY), context(scope, now))


__all__ = [
    "STATE_RANK",
    "apply_filter",
    "compiled",
    "context",
    "order",
    "scoped",
]
