"""The api application imports, describes itself and answers its list routes."""

from __future__ import annotations

import httpx
import pytest

from app.api.deps import get_current_active_user
from app.config import API_V1_PREFIX
from app.core.database import get_session
from app.main import app
from shared.models.user import User

pytestmark = pytest.mark.api

LIST_ROUTES = (
    "/activity?project_id={project}",
    "/notifications?project_id={project}",
    "/scans?project_id={project}",
    "/notes?project_id={project}",
    "/targets?project_slug={slug}",
    "/targets/search?target_value=example&project_slug={slug}",
)


def test_the_app_describes_every_router():
    paths = app.openapi()["paths"]

    assert len(paths) > 100
    assert all(path == "/" or path.startswith(API_V1_PREFIX) for path in paths)


@pytest.fixture
async def client(estate):
    """The app over ASGI on the test session, signed in as the estate's superuser."""
    user = await estate.session.get(User, estate.user_id)

    async def session():
        yield estate.session

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_current_active_user] = lambda: user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


@pytest.mark.parametrize("path", LIST_ROUTES)
async def test_a_paginated_list_answers_a_page(client, estate, path: str):
    url = API_V1_PREFIX + path.format(
        project=estate.project_id, slug=f"test-{estate.project_id.hex[:8]}"
    )

    response = await client.get(url)

    assert response.status_code == 200, response.text
    assert {"items", "total"} <= response.json().keys()
