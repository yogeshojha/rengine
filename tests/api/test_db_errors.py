from __future__ import annotations

import json

import pytest
from sqlalchemy.exc import DBAPIError
from starlette.requests import Request

from app.core.db_errors import data_exception_handler

pytestmark = pytest.mark.api


class _PgError(Exception):
    def __init__(self, sqlstate: str):
        super().__init__("canceling statement due to statement timeout")
        self.sqlstate = sqlstate


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/x", "headers": []})


def _error(sqlstate: str) -> DBAPIError:
    return DBAPIError("SELECT 1", {}, _PgError(sqlstate))


async def test_a_statement_timeout_is_a_503_without_the_statement():
    out = await data_exception_handler(_request(), _error("57014"))

    assert out.status_code == 503
    body = json.loads(out.body)
    assert body == {"detail": "The query timed out. Narrow the filter and try again."}


async def test_a_data_exception_is_still_a_400():
    out = await data_exception_handler(_request(), _error("22001"))

    assert out.status_code == 400


async def test_any_other_database_error_is_raised():
    exc = _error("40P01")
    with pytest.raises(DBAPIError):
        await data_exception_handler(_request(), exc)
