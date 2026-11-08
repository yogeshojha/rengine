from __future__ import annotations

import uuid
from datetime import date

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from app.api import scope
from app.api.deps import get_current_active_user
from app.api.v1 import cves
from app.api.v1.vulnerabilities import _check_state
from app.api.v1.whats_new import _check_range, _zone
from app.core.validation_errors import validation_detail
from app.services.ai_settings import call_cursor

pytestmark = pytest.mark.api


def _documented(detail) -> None:
    assert isinstance(detail, list)
    assert len(detail) == 1
    item = detail[0]
    assert set(item) == {"loc", "msg", "type"}
    assert isinstance(item["loc"], list)
    assert item["type"] == "value_error"
    assert item["msg"].endswith(".")


def test_helper_returns_the_validation_shape():
    assert validation_detail(["query", "x"], "Bad.") == [
        {"loc": ["query", "x"], "msg": "Bad.", "type": "value_error"}
    ]


@pytest.mark.parametrize(
    "call",
    [
        lambda: _zone("Mars/Olympus"),
        lambda: _check_range("1y", None, None),
        lambda: _check_range(None, None, date(2026, 1, 1)),
        lambda: _check_state("bogus"),
        lambda: call_cursor("not-a-cursor"),
    ],
)
def test_string_detail_422s_carry_the_list_shape(call):
    with pytest.raises(HTTPException) as caught:
        call()
    assert caught.value.status_code == 422
    _documented(caught.value.detail)


async def test_scope_without_a_project_answers_the_list_shape():
    with pytest.raises(HTTPException) as caught:
        await scope.resolve_scope(None, "web_assets", None, None)
    assert caught.value.status_code == 422
    _documented(caught.value.detail)


async def test_route_body_carries_the_list_shape():
    app = FastAPI()
    app.include_router(cves.router)
    app.dependency_overrides[get_current_active_user] = lambda: object()
    app.dependency_overrides[cves.get_service] = lambda: None
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/cves/not-a-cve", params={"project_id": str(uuid.uuid4())}
        )
    assert response.status_code == 422
    body = response.json()["detail"]
    _documented(body)
    assert body[0]["loc"] == ["path", "cve"]
