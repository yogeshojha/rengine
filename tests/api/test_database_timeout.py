from __future__ import annotations

from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database

pytestmark = pytest.mark.api


async def test_every_api_connection_carries_a_client_timeout():
    async with database.engine.connect() as conn:
        raw = await conn.get_raw_connection()
        config = raw.driver_connection._config

    assert config.command_timeout == database.COMMAND_TIMEOUT_SECONDS


async def test_a_database_that_does_not_answer_is_a_503():
    app = FastAPI()

    @app.get("/hung")
    async def hung(session: Annotated[AsyncSession, Depends(database.get_session)]):
        raise TimeoutError

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        response = await client.get("/hung")

    assert response.status_code == 503
    assert response.json()["detail"] == database.DATABASE_UNAVAILABLE
