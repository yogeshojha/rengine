from __future__ import annotations

import math
import time
from collections.abc import AsyncIterator
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from shared.models.asset_query import QueryError

from .ast import QuerySyntaxError

STATEMENT_SECONDS = 20
MIN_STATEMENT_SECONDS = 1
STATEMENT_TIMEOUT = f"SET LOCAL statement_timeout = '{STATEMENT_SECONDS}s'"
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


_DEADLINE: ContextVar[float | None] = ContextVar("query_deadline", default=None)
_TIMED = "query_deadline_transaction"
_CONTROL = ("SAVEPOINT", "RELEASE", "ROLLBACK")


def start_deadline() -> None:
    """Statements from here on share one `STATEMENT_SECONDS` budget."""
    _DEADLINE.set(time.monotonic() + STATEMENT_SECONDS)


async def query_deadline() -> AsyncIterator[None]:
    """One `STATEMENT_SECONDS` budget for every statement of a request."""
    token = _DEADLINE.set(time.monotonic() + STATEMENT_SECONDS)
    try:
        yield
    finally:
        _DEADLINE.reset(token)


def _timeout_left(deadline: float) -> str:
    seconds = max(MIN_STATEMENT_SECONDS, math.ceil(deadline - time.monotonic()))
    return f"SET LOCAL statement_timeout = '{min(seconds, STATEMENT_SECONDS)}s'"


@event.listens_for(Engine, "before_cursor_execute", retval=True)
def _apply_deadline(conn, cursor, statement, parameters, *_):
    deadline = _DEADLINE.get()
    if deadline is None:
        return statement, parameters
    transaction = conn.get_transaction()
    if statement == STATEMENT_TIMEOUT:
        conn.info[_TIMED] = transaction
        return _timeout_left(deadline), parameters
    if (
        transaction is not None
        and conn.info.get(_TIMED) is transaction
        and not statement.lstrip().upper().startswith(_CONTROL)
    ):
        cursor.execute(_timeout_left(deadline), ())
    return statement, parameters
