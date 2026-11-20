"""The API reference lists what an access key can call, as the gate classifies it."""

from __future__ import annotations

import json
import re
import shlex
import uuid

import pytest
from fastapi import FastAPI

from app.api.deps import route_facts, served_routes
from app.api.router import router as api_router
from app.config import API_V1_PREFIX
from app.main import app
from app.services import api_reference
from shared.definitions.access_keys import (
    READ_ONLY_DETAIL,
    REFUSED_DETAIL,
    AccessKeyLevel,
    KeyRule,
    key_rule,
)
from shared.definitions.api_reference import (
    EXAMPLE_BASE_URL,
    EXAMPLE_KEY_VARIABLE,
    FIRST_REQUEST,
    GROUP_ORDER,
    PROJECT_PARAMETER,
    PROJECT_VARIABLE,
    first_request,
)
from shared.models.reference import ReferenceOperation
from tests.api.test_access_keys import (  # noqa: F401
    _bearer,
    _cookie,
    _key,
    _url,
    _user,
    api,
    redis,
)

pytestmark = pytest.mark.api

MIN_OPERATIONS = 50
MAX_OPERATIONS = 80
LEVEL_OF = {KeyRule.READ: AccessKeyLevel.READ, KeyRule.WRITE: AccessKeyLevel.WRITE}


@pytest.fixture(scope="module")
def groups():
    return api_reference.reference(app)


@pytest.fixture(scope="module")
def operations(groups) -> list[ReferenceOperation]:
    return [op for group in groups for op in group.operations]


def _rules() -> dict[tuple[str, str], KeyRule]:
    found = {}
    for route in served_routes(app):
        facts = route_facts(route, API_V1_PREFIX)
        for method in route.methods or ():
            found[(method, route.path_format)] = key_rule(
                method, facts.path, gated=facts.gated
            )
    return found


# ---------- what is listed ----------


def test_every_listed_operation_carries_the_gates_answer(operations):
    rules = _rules()
    assert MIN_OPERATIONS <= len(operations) <= MAX_OPERATIONS
    assert len({(op.method, op.path) for op in operations}) == len(operations)
    for op in operations:
        rule = rules[(op.method, op.path)]
        assert rule is not KeyRule.REFUSED, (op.method, op.path)
        assert op.access is LEVEL_OF[rule], (op.method, op.path)


def test_no_refused_route_is_listed(operations):
    refused = {pair for pair, rule in _rules().items() if rule is KeyRule.REFUSED}
    assert not refused & {(op.method, op.path) for op in operations}


def test_only_written_summaries_are_listed(operations):
    written = {
        (method, route.path_format): route.summary
        for route in served_routes(app)
        if route.summary
        for method in route.methods or ()
    }
    for op in operations:
        assert op.summary == written[(op.method, op.path)]
        assert op.summary[0].isupper(), op.summary
        assert not re.search(r"\byou\b|\byour\b|[()!?;—]|\.$", op.summary), op.summary


def test_groups_come_in_the_products_order(groups):
    names = [group.name for group in groups]
    assert names == [name for name in GROUP_ORDER if name in names]
    assert names == list(GROUP_ORDER)
    for group in groups:
        assert group.operations
        assert {op.group for op in group.operations} == {group.name}


def test_every_example_is_a_curl_request(operations):
    for op in operations:
        tokens = shlex.split(op.curl.replace("\\\n", " "))
        assert tokens[0] == "curl"
        if op.method == "GET":
            assert "-X" not in tokens
        else:
            assert tokens[tokens.index("-X") + 1] == op.method
        url = next(t for t in tokens if t.startswith(EXAMPLE_BASE_URL))
        path = re.escape(op.path)
        pattern = re.sub(r"\\\{[^}]+\\\}", r"\\$[A-Z_]+", path)
        assert re.fullmatch(re.escape(EXAMPLE_BASE_URL) + pattern + r"(\?.*)?", url)
        required = [
            p.name for p in op.parameters if p.location == "query" and p.required
        ]
        query = url.partition("?")[2]
        assert [pair.split("=")[0] for pair in query.split("&") if pair] == required
        assert f"Authorization: Bearer ${EXAMPLE_KEY_VARIABLE}" in tokens
        if op.example is None:
            assert "-d" not in tokens
        else:
            assert json.loads(tokens[tokens.index("-d") + 1]) == op.example


@pytest.mark.parametrize(
    ("method", "path", "url"),
    [
        ("POST", "/scans/{id}/cancel", "/scans/$SCAN_ID/cancel"),
        ("POST", "/scans/{id}/pause", "/scans/$SCAN_ID/pause"),
        ("GET", "/scans/{id}/activities", "/scans/$SCAN_ID/activities"),
        ("GET", "/scans/{id}/comparable", "/scans/$SCAN_ID/comparable"),
        ("GET", "/targets/{target_id}", "/targets/$TARGET_ID"),
    ],
)
def test_a_path_variable_is_named_after_its_collection(operations, method, path, url):
    op = next(
        o for o in operations if (o.method, o.path) == (method, API_V1_PREFIX + path)
    )
    assert f"{EXAMPLE_BASE_URL}{API_V1_PREFIX}{url}" in op.curl


def test_the_first_request_is_the_references_request(operations):
    method, path, body = FIRST_REQUEST
    op = next(
        o for o in operations if (o.method, o.path) == (method, API_V1_PREFIX + path)
    )
    first = first_request(API_V1_PREFIX)
    assert first.split(" \\\n  ")[:-1] == op.curl.split(" \\\n  ")[:-1]
    tokens = shlex.split(first.replace("\\\n", " "))
    assert json.loads(tokens[-1]) == body
    assert f'?{PROJECT_PARAMETER}={PROJECT_VARIABLE}"' in first


def test_the_reference_builds_without_the_openapi_route():
    bare = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    bare.include_router(api_router, prefix=API_V1_PREFIX)
    built = api_reference.build(bare)
    assert [g.name for g in built] == list(GROUP_ORDER)


# ---------- over the wire ----------


def _request(op: ReferenceOperation) -> tuple[str, dict, object]:
    path = re.sub(r"\{[^}]+\}", lambda _m: str(uuid.uuid4()), op.path)
    params = {
        p.name: str(uuid.uuid4()) if "uuid" in p.type else "x"
        for p in op.parameters
        if p.location == "query" and p.required
    }
    return path, params, op.example


async def test_a_read_key_calls_what_the_reference_says(
    api,  # noqa: F811
    flush_only,
    operations,
):
    user = await _user(flush_only)
    secret = await _key(flush_only, user, AccessKeyLevel.READ)
    for op in operations:
        path, params, body = _request(op)
        response = await api.request(
            op.method, path, params=params, json=body, headers=_bearer(secret)
        )
        detail = (
            response.json().get("detail")
            if response.headers.get("content-type", "").startswith("application/json")
            and isinstance(response.json(), dict)
            else None
        )
        if op.access is AccessKeyLevel.WRITE:
            assert (response.status_code, detail) == (403, READ_ONLY_DETAIL), op.path
        else:
            assert response.status_code != 401, op.path
            assert detail not in (REFUSED_DETAIL, READ_ONLY_DETAIL), op.path


async def test_the_reference_needs_a_session(api):  # noqa: F811
    assert (await api.get(_url("/reference"))).status_code == 401


async def test_the_reference_answers_signed_in_users_and_keys(
    api,  # noqa: F811
    flush_only,
):
    user = await _user(flush_only)
    by_session = await api.get(_url("/reference"), headers=_cookie(user))
    assert by_session.status_code == 200
    assert [g["name"] for g in by_session.json()] == list(GROUP_ORDER)
    secret = await _key(flush_only, user, AccessKeyLevel.READ)
    by_key = await api.get(_url("/reference"), headers=_bearer(secret))
    assert by_key.json() == by_session.json()
