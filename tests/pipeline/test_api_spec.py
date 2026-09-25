from __future__ import annotations

import pytest

from stages.url_discovery.providers.api_spec import (
    _bases,
    _is_spec,
    _load,
    parse_openapi,
)

pytestmark = pytest.mark.pipeline

_V3 = {
    "openapi": "3.0.0",
    "servers": [{"url": "/api/v1"}],
    "paths": {
        "/users/{id}": {
            "parameters": [
                {"name": "id", "in": "path", "required": True},
                {"name": "fields", "in": "query"},
            ],
            "get": {"parameters": [{"name": "expand", "in": "query"}]},
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {"email": {}, "role": {}},
                            }
                        }
                    }
                }
            },
        },
        "/search": {
            "get": {
                "parameters": [
                    {"$ref": "#/components/parameters/Query"},
                ]
            }
        },
    },
    "components": {"parameters": {"Query": {"name": "q", "in": "query"}}},
}


def _by_method(obs, method):
    return next(o for o in obs if o.methods == [method])


def test_a_spec_is_recognised() -> None:
    assert _is_spec(_V3)
    assert _is_spec({"swagger": "2.0", "paths": {}})
    assert not _is_spec({"paths": {}})
    assert not _is_spec({"openapi": "3.0.0"})
    assert not _is_spec("just text")


def test_query_and_path_params_become_a_concrete_url() -> None:
    obs = parse_openapi(_V3, "https://api.example.com/openapi.json")
    get = _by_method([o for o in obs if "/users/" in o.url], "GET")
    # the {id} template is filled and folds to a dynamic segment.
    assert "/api/v1/users/1?" in get.url
    assert "fields=" in get.url
    assert "expand=" in get.url
    assert get.methods == ["GET"]


def test_a_local_ref_parameter_is_resolved() -> None:
    obs = parse_openapi(_V3, "https://api.example.com/openapi.json")
    search = _by_method([o for o in obs if "/search" in o.url], "GET")
    assert "q=" in search.url


def test_request_body_fields_are_named_in_the_detail() -> None:
    obs = parse_openapi(_V3, "https://api.example.com/openapi.json")
    post = _by_method([o for o in obs if "/users/" in o.url], "POST")
    assert "email" in post.detail
    assert "role" in post.detail


def test_a_relative_server_resolves_against_the_spec_host() -> None:
    assert _bases(_V3, "https://api.example.com/openapi.json") == [
        "https://api.example.com/api/v1"
    ]


def test_swagger_v2_basepath_is_the_base() -> None:
    v2 = {"swagger": "2.0", "basePath": "/v2", "paths": {"/ping": {"get": {}}}}
    obs = parse_openapi(v2, "https://h.example/swagger.json")
    assert obs[0].url == "https://h.example/v2/ping"


def test_a_remote_ref_is_not_followed() -> None:
    doc = {
        "openapi": "3.0.0",
        "paths": {
            "/x": {"get": {"parameters": [{"$ref": "https://evil.example/p.json"}]}}
        },
    }
    obs = parse_openapi(doc, "https://h.example/openapi.json")
    assert obs[0].url == "https://h.example/x"


def test_yaml_specs_load() -> None:
    doc = _load("openapi: 3.0.0\npaths:\n  /ping:\n    get: {}\n")
    assert _is_spec(doc)
