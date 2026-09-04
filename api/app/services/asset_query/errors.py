from __future__ import annotations

from sqlalchemy.exc import DBAPIError

from shared.models.asset_query import QueryError

STATEMENT_TIMEOUT = "SET LOCAL statement_timeout = '20s'"
# a set-returning expansion is estimated at 100 rows a row, and the bogus cost buys 270ms of JIT
NO_JIT = "SET LOCAL jit = off"

QUERY_SQLSTATES = {
    "2201B": (
        "That regular expression is not valid here.",
        "PostgreSQL regular expressions differ slightly from PCRE.",
    ),
    "2201G": ("That regular expression is not valid here.", None),
    "57014": (
        "That search took too long to run.",
        "Add a field filter to narrow it down.",
    ),
    "22003": ("A number in that query is out of range.", None),
    "22P02": ("A value in that query has the wrong shape.", None),
    "54000": ("That search term is too large to index.", None),
}


def query_error_for(exc: DBAPIError) -> QueryError | None:
    sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    known = QUERY_SQLSTATES.get(str(sqlstate))
    if known is None:
        return None
    message, hint = known
    return QueryError(message=message, hint=hint)
