"""The api application imports, describes itself and answers its list routes.

Every other api test calls services directly, so a dependency upgrade that breaks the app
at import time (fastapi-pagination against a newer FastAPI, say) passed them all while the
server itself could not start.
"""

from __future__ import annotations

import httpx
import pytest

from app.api.deps import get_current_active_user, get_session
from app.config import settings
from app.main import app
from shared.models.user import User

pytestmark = pytest.mark.api


def test_the_app_builds_its_openapi_schema_with_every_router():
    paths = app.openapi()["paths"]
    assert any(path.startswith(settings.API_V1_PREFIX) for path in paths)
    assert len(paths) > 100


async def test_the_app_serves_its_schema_over_http():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == settings.APP_NAME


@pytest.fixture
async def client(estate):
    """The app over ASGI, on the test's session, signed in as the estate's superuser."""
    user = await estate.session.get(User, estate.user_id)

    async def session_override():
        yield estate.session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_active_user] = lambda: user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "path",
    [
        "/activity?project_id={project}",
        "/notifications?project_id={project}",
        "/scans?project_id={project}",
        "/notes?project_id={project}",
        "/targets/search?target_value=example&project_slug={slug}",
    ],
)
async def test_a_paginated_list_answers_a_page(client, estate, path):
    """Paginated routes run their query on the async session through fastapi-pagination."""
    url = settings.API_V1_PREFIX + path.format(
        project=estate.project_id, slug=f"test-{estate.project_id.hex[:8]}"
    )
    response = await client.get(url)
    assert response.status_code == 200, response.text
    assert {"items", "total"} <= response.json().keys()
