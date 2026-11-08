from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi import FastAPI

from app.api.deps import get_current_active_user
from app.api.v1 import notes
from shared.definitions.notes import (
    MAX_ASSET_KEY,
    MAX_NOTE_FACET_VALUES,
    MAX_NOTE_TAG_CHARS,
    MAX_NOTE_TAGS,
)
from shared.models.note import NoteFacets

pytestmark = pytest.mark.api

PROJECT = str(uuid.uuid4())
ID = str(uuid.uuid4())


class _Service:
    async def facets(self, *_args, **_kwargs):
        return NoteFacets()


def _client() -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(notes.router)
    app.dependency_overrides[get_current_active_user] = lambda: object()
    app.dependency_overrides[notes.get_service] = lambda: _Service()
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def _facets(params: list[tuple[str, str]]) -> int:
    async with _client() as client:
        response = await client.get(
            "/notes/facets", params=[("project_id", PROJECT), *params]
        )
    return response.status_code


@pytest.mark.parametrize(
    "params",
    [
        [("asset_q", "x" * MAX_ASSET_KEY)],
        [("asset_key", "x" * MAX_ASSET_KEY)],
        [("asset", "web_assets:" + "x" * MAX_ASSET_KEY)],
        [("tag", "#" + "x" * MAX_NOTE_TAG_CHARS)],
        [("dimension", "web_assets"), ("dimension", "target")],
        [("status", "resolved")],
        [("triage", "false_positive")],
        [("tag", "t")] * MAX_NOTE_TAGS,
        [("asset", "ips:192.0.2.1")] * MAX_NOTE_FACET_VALUES,
        [("target_id", ID)] * MAX_NOTE_FACET_VALUES,
        [("scan", ID)] * MAX_NOTE_FACET_VALUES,
        [("author", ID)] * MAX_NOTE_FACET_VALUES,
    ],
)
async def test_bounded_values_pass(params):
    assert await _facets(params) == 200


@pytest.mark.parametrize(
    "params",
    [
        [("asset_q", "x" * (MAX_ASSET_KEY + 1))],
        [("asset_key", "x" * (MAX_ASSET_KEY + 1))],
        [("asset", "web_assets:" + "x" * (MAX_ASSET_KEY + 20))],
        [("tag", "x" * (MAX_NOTE_TAG_CHARS + 2))],
        [("dimension", "x" * 100)],
        [("status", "x" * 100)],
        [("triage", "x" * 100)],
        [("tag", "t")] * (MAX_NOTE_TAGS + 1),
        [("asset", "ips:192.0.2.1")] * (MAX_NOTE_FACET_VALUES + 1),
        [("status", "open")] * 3,
        [("target_id", ID)] * (MAX_NOTE_FACET_VALUES + 1),
        [("scan", ID)] * (MAX_NOTE_FACET_VALUES + 1),
        [("author", ID)] * (MAX_NOTE_FACET_VALUES + 1),
    ],
)
async def test_values_past_their_bound_are_refused(params):
    assert await _facets(params) == 422
