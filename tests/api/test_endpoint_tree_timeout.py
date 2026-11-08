from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.sql.elements import TextClause

from app.services.endpoint import EndpointService
from shared.models.endpoint import EndpointFilter, EndpointTree

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

    async def scalar(self, *_args, **_kwargs):
        raise DBAPIError(STATEMENT, {}, self.cause)

    async def rollback(self):
        self.rolled_back = True


async def _timing_out():
    raise DBAPIError(STATEMENT, {}, _CancelledError())


async def test_a_tree_read_past_the_timeout_answers_with_an_error():
    session = _Session(_CancelledError())
    found = await EndpointService(session)._guarded(
        _timing_out(), lambda e: EndpointTree(mode="host", error=e)
    )
    assert found.error is not None
    assert found.error.message == "The search timed out."
    assert session.rolled_back


@pytest.mark.parametrize("read", ["merged_leaves", "gone"])
async def test_leaves_and_gone_past_the_timeout_answer_with_an_error(read):
    session = _Session(_CancelledError())
    found = await getattr(EndpointService(session), read)(
        uuid.uuid4(), EndpointFilter(q="portal")
    )
    assert found.error is not None
    assert found.error.message == "The search timed out."


async def test_a_tree_read_failing_otherwise_still_raises():
    with pytest.raises(DBAPIError):
        await EndpointService(_Session(RuntimeError())).merged_leaves(
            uuid.uuid4(), EndpointFilter()
        )
