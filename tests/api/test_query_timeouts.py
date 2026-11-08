from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.sql.elements import TextClause

from app.services.subdomain import SubdomainService
from shared.models.subdomain import SubdomainFilter

pytestmark = pytest.mark.api

STATEMENT = "SELECT"


class _CancelledError(Exception):
    sqlstate = "57014"


class _Session:
    def __init__(self, cause: Exception):
        self.cause = cause
        self.rolled_back = False

    async def execute(self, statement, *_args, **_kwargs):
        if not isinstance(statement, TextClause):
            raise DBAPIError(STATEMENT, {}, self.cause)

    async def rollback(self):
        self.rolled_back = True


async def test_a_render_query_past_the_timeout_answers_with_an_error():
    session = _Session(_CancelledError())
    found = await SubdomainService(session).renders(
        uuid.uuid4(), uuid.uuid4(), SubdomainFilter(q="portal")
    )
    assert found.error is not None
    assert found.error.message == "The search timed out."
    assert session.rolled_back


async def test_a_render_query_failing_otherwise_still_raises():
    with pytest.raises(DBAPIError):
        await SubdomainService(_Session(RuntimeError())).renders(
            uuid.uuid4(), uuid.uuid4(), SubdomainFilter()
        )
