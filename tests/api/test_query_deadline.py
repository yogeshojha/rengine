from __future__ import annotations

import asyncio
import time

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.main import app as rengine
from shared.services.asset_query import errors
from shared.services.asset_query.errors import STATEMENT_TIMEOUT, query_deadline

pytestmark = pytest.mark.api

TIMED_OUT = errors.QUERY_SQLSTATES[errors.TIMEOUT_SQLSTATE][0]

_SEARCH_PATHS = (
    "/api/v1/subdomains/search/leads",
    "/api/v1/ips/search/groups",
    "/api/v1/ports/search/counts",
    "/api/v1/vulnerabilities/search/groups",
)


async def _run(engine, steps: list[str | float]) -> list[str]:
    outcomes = []
    async with engine.connect() as conn:
        await conn.execute(text(STATEMENT_TIMEOUT))
        for step in steps:
            if isinstance(step, float):
                await asyncio.sleep(step)
                continue
            try:
                async with conn.begin_nested():
                    await conn.execute(text(step))
                outcomes.append("ok")
            except DBAPIError as exc:
                outcomes.append(errors.query_error_for(exc).message)
    return outcomes


async def _within_deadline(engine, steps: list[str | float]) -> list[str]:
    holder = query_deadline()
    await holder.__anext__()
    try:
        return await _run(engine, steps)
    finally:
        await holder.aclose()


async def test_statements_of_one_request_share_one_budget(engine, monkeypatch):
    monkeypatch.setattr(errors, "STATEMENT_SECONDS", 2)
    started = time.monotonic()

    outcomes = await _within_deadline(
        engine, ["SELECT pg_sleep(1.4)", "SELECT pg_sleep(1.4)"]
    )

    assert outcomes == ["ok", TIMED_OUT]
    assert time.monotonic() - started < 3.5


async def test_a_statement_past_the_deadline_gets_the_floor(engine, monkeypatch):
    monkeypatch.setattr(errors, "STATEMENT_SECONDS", 1)

    outcomes = await _within_deadline(
        engine, [1.2, "SELECT pg_sleep(0.2)", "SELECT pg_sleep(1.5)"]
    )

    assert outcomes == ["ok", TIMED_OUT]


async def test_without_a_deadline_each_statement_keeps_its_own_timeout(engine):
    outcomes = await _run(engine, ["SELECT pg_sleep(1.2)", "SELECT pg_sleep(1.2)"])

    assert outcomes == ["ok", "ok"]


async def test_the_deadline_reaches_the_route():
    probe = FastAPI(dependencies=[Depends(query_deadline)])

    @probe.get("/probe")
    async def _probe() -> dict[str, bool]:
        return {"set": errors._DEADLINE.get() is not None}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=probe), base_url="http://test"
    ) as client:
        answer = (await client.get("/probe")).json()

    assert answer == {"set": True}
    assert errors._DEADLINE.get() is None


@pytest.mark.parametrize("path", _SEARCH_PATHS)
def test_search_routes_carry_the_deadline(path):
    route = next(r for r in rengine.routes if getattr(r, "path", None) == path)

    assert query_deadline in [d.call for d in route.dependant.dependencies]
