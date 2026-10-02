from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI, Request

from app.core import body_limit
from app.core.body_limit import BodySizeLimitMiddleware
from app.main import app as main_app

pytestmark = pytest.mark.api

CAP = 64


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware)

    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    @app.post("/json")
    async def json_body(payload: dict[str, str]) -> dict[str, int]:
        return {"keys": len(payload)}

    return app


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()), base_url="http://test"
    )


@pytest.fixture(autouse=True)
def small_cap(monkeypatch):
    monkeypatch.setattr(body_limit, "MAX_REQUEST_BYTES", CAP)


async def test_a_body_under_the_cap_passes():
    async with _client() as client:
        response = await client.post("/echo", content=b"x" * CAP)
    assert response.status_code == 200
    assert response.json() == {"size": CAP}


async def test_a_declared_length_over_the_cap_is_refused():
    async with _client() as client:
        response = await client.post("/echo", content=b"x" * (CAP + 1))
    assert response.status_code == 413


async def test_a_streamed_body_over_the_cap_is_refused():
    async def chunks():
        for _ in range(4):
            yield b"x" * CAP

    async with _client() as client:
        response = await client.post("/echo", content=chunks())
    assert response.status_code == 413


async def test_a_validated_json_body_over_the_cap_is_refused():
    async def chunks():
        yield b'{"a": "'
        yield b"x" * CAP
        yield b'"}'

    async with _client() as client:
        response = await client.post(
            "/json", content=chunks(), headers={"content-type": "application/json"}
        )
    assert response.status_code == 413


def test_the_api_carries_the_cap_innermost():
    assert main_app.user_middleware[-1].cls is BodySizeLimitMiddleware


async def test_the_api_refuses_a_streamed_json_body_with_413():
    async def chunks():
        yield b'{"username": "'
        for _ in range(4):
            yield b"x" * CAP
        yield b'", "password": "x"}'

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main_app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            content=chunks(),
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 413
