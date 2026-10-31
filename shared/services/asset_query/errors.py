from __future__ import annotations

from sqlalchemy.exc import DBAPIError

from shared.models.asset_query import QueryError

from .ast import QuerySyntaxError

STATEMENT_TIMEOUT = "SET LOCAL statement_timeout = '20s'"
NO_JIT = "SET LOCAL jit = off"

TIMEOUT_SQLSTATE = "57014"

QUERY_SQLSTATES = {
    "2201B": (
        "Invalid regular expression.",
        "PostgreSQL regular expression syntax applies.",
    ),
    "2201G": ("Invalid regular expression.", None),
    TIMEOUT_SQLSTATE: ("The search timed out.", "Add a field filter."),
    "22003": ("A number is out of range.", None),
    "22P02": ("A value has the wrong type.", None),
    "54000": ("A search term is too long to index.", None),
}


def query_error_for(exc: DBAPIError) -> QueryError | None:
    sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    known = QUERY_SQLSTATES.get(str(sqlstate))
    if known is None:
        return None
    message, hint = known
    return QueryError(message=message, hint=hint)


def syntax_error(exc: QuerySyntaxError) -> QueryError:
    """What the UI underlines in place of the query it could not parse."""
    return QueryError(message=exc.message, hint=exc.hint, start=exc.start, end=exc.end)
