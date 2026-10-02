from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
import yaml

from shared.definitions.endpoints import EndpointSource
from shared.services.endpoint_inventory import EndpointObservation
from shared.utils.net import host_port
from shared.utils.yaml_safe import DocumentTooLargeError, load_document
from stages.url_discovery.config import MAX_API_SPEC_HOSTS
from stages.url_discovery.providers.base import ProviderResult, UrlProvider

_SPEC_PATHS = (
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/swagger.yaml",
    "/v2/api-docs",
    "/v3/api-docs",
    "/api-docs",
    "/api/swagger.json",
    "/swagger/v1/swagger.json",
    "/api/openapi.json",
    "/api/v1/openapi.json",
    "/.well-known/openapi.json",
    "/api-docs/swagger.json",
    "/api/docs/openapi.json",
)
_GRAPHQL_PATHS = ("/graphql", "/api/graphql", "/v1/graphql", "/graphql/v1", "/query")
_INTROSPECTION = (
    '{"query":"{__schema{queryType{name} mutationType{name} types{name kind}}}"}'
)
_HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")
_MAX_BYTES = 5 * 1024 * 1024
_MAX_ENDPOINTS_PER_SPEC = 3000
_MAX_QUERY_PARAMS = 60
_MAX_REF_DEPTH = 6
_MAX_WORKERS = 12
_CLIENT_ERROR = 400
_PATH_SAMPLE = "1"
_PATH_TEMPLATE = re.compile(r"\{[^{}/]+\}")


class ApiSpecProvider(UrlProvider):
    """Endpoints declared by the service's own OpenAPI, Swagger or GraphQL schema."""

    source = EndpointSource.API_SPEC.value
    tool = None
    binary = None
    touches_target = True

    def discover(self, result: ProviderResult) -> None:
        roots = _roots(self.ctx.hosts)
        if not roots:
            return
        selected = roots[:MAX_API_SPEC_HOSTS]
        client = self.http_client()
        state = _State()
        try:
            workers = min(self.workers(_MAX_WORKERS), len(selected))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for found in pool.map(lambda root: self._mine(client, root), selected):
                    if found is None:
                        result.capped = True
                        result.cap_reason = "The scan was cancelled."
                        continue
                    state.merge(found)
        finally:
            client.close()

        result.observations = [o for o in state.observations if self.in_scope(o.url)]
        offsite = len(state.observations) - len(result.observations)
        result.urls_found = len(state.observations)
        result.pages_fetched = state.fetched
        result.errors = state.errors
        result.hosts_scanned = min(len(roots), MAX_API_SPEC_HOSTS)
        if offsite and not result.cap_reason:
            result.cap_reason = (
                f"{offsite} declared urls pointed outside scope and were not stored."
            )
        self.progress(
            f"{len(result.observations)} endpoints from {state.specs} "
            f"{'schema' if state.specs == 1 else 'schemas'} and "
            f"{state.graphql} graphql {'endpoint' if state.graphql == 1 else 'endpoints'}"
        )

    def _mine(self, client: httpx.Client, root: str) -> _State | None:
        if self.aborted():
            return None
        state = _State()
        for path in _SPEC_PATHS:
            if self.aborted():
                return None
            url = urljoin(root, path)
            body = self.fetch_text(client, url, _MAX_BYTES, state)
            if body is None:
                continue
            document = _load(body)
            if not _is_spec(document):
                continue
            state.specs += 1
            for obs in parse_openapi(document, url):
                state.add(obs)
        for path in _GRAPHQL_PATHS:
            if self.aborted():
                return None
            url = urljoin(root, path)
            obs = self._graphql(client, url, state)
            if obs is not None:
                state.graphql += 1
                state.add(obs)
        return state

    def _graphql(
        self, client: httpx.Client, url: str, state: _State
    ) -> EndpointObservation | None:
        if self.path_excluded(url):
            return None
        self.throttle()
        state.fetched += 1
        host = urlsplit(url).hostname or ""
        try:
            with self.host_slot(host):
                response = client.post(
                    url,
                    content=_INTROSPECTION,
                    headers={"Content-Type": "application/json"},
                )
            self.host_observed(host, status=response.status_code)
        except (httpx.HTTPError, ValueError):
            self.host_observed(host, transport_error=True)
            state.errors += 1
            return None
        if response.status_code >= _CLIENT_ERROR:
            return None
        try:
            schema = response.json().get("data", {}).get("__schema")
        except (ValueError, AttributeError, RecursionError):
            return None
        if not isinstance(schema, dict):
            return None
        types = [t for t in schema.get("types") or [] if isinstance(t, dict)]
        return EndpointObservation(
            url=url,
            found_on=url,
            methods=["POST"],
            detail=(f"GraphQL endpoint, introspection enabled, {len(types)} types"),
        )


class _State:
    def __init__(self) -> None:
        self.observations: list[EndpointObservation] = []
        self.seen: set[str] = set()
        self.fetched = 0
        self.errors = 0
        self.specs = 0
        self.graphql = 0

    def merge(self, other: _State) -> None:
        self.fetched += other.fetched
        self.errors += other.errors
        self.specs += other.specs
        self.graphql += other.graphql
        for obs in other.observations:
            self.add(obs)

    def add(self, obs: EndpointObservation) -> None:
        key = obs.url + "|" + ",".join(obs.methods)
        if key in self.seen:
            return
        self.seen.add(key)
        self.observations.append(obs)


# ---------- parsing (pure) ----------


def _load(body: str) -> Any:
    text = body.lstrip()
    if text[:1] in "{[":
        try:
            return json.loads(body)
        except (ValueError, RecursionError):
            return None
    try:
        return load_document(body)
    except (DocumentTooLargeError, yaml.YAMLError, RecursionError):
        return None


def _is_spec(document: Any) -> bool:
    return (
        isinstance(document, dict)
        and ("openapi" in document or "swagger" in document)
        and isinstance(document.get("paths"), dict)
    )


def parse_openapi(document: dict, spec_url: str) -> list[EndpointObservation]:
    """One observation per (path, method) the schema declares, with its query params."""
    bases = _bases(document, spec_url)
    label = _label(document)
    out: list[EndpointObservation] = []
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return out
    for template, item in paths.items():
        if not isinstance(item, dict) or not isinstance(template, str):
            continue
        shared = _parameters(item.get("parameters"), document)
        for method in _HTTP_METHODS:
            operation = item.get(method)
            if not isinstance(operation, dict):
                continue
            params = shared + _parameters(operation.get("parameters"), document)
            query = _names(params, "query")
            body = _body_fields(operation.get("requestBody"), document)
            detail = f"Declared by {label}"
            if body:
                detail += f", body: {', '.join(body[:_MAX_QUERY_PARAMS])}"
            for base in bases:
                out.append(
                    EndpointObservation(
                        url=_build_url(base, template, query),
                        found_on=spec_url,
                        methods=[method.upper()],
                        detail=detail,
                    )
                )
            if len(out) >= _MAX_ENDPOINTS_PER_SPEC:
                return out
    return out


def _label(document: dict) -> str:
    if document.get("openapi"):
        return "an OpenAPI schema"
    return "a Swagger schema"


def _bases(document: dict, spec_url: str) -> list[str]:
    parts = urlsplit(spec_url)
    root = f"{parts.scheme}://{parts.netloc}"
    servers = document.get("servers")
    if isinstance(servers, list) and servers:
        bases = []
        for server in servers:
            url = server.get("url") if isinstance(server, dict) else None
            if isinstance(url, str) and url:
                bases.append(url if "://" in url else urljoin(root + "/", url))
        if bases:
            return list(dict.fromkeys(bases))
    base_path = document.get("basePath")
    if isinstance(base_path, str) and base_path.strip("/"):
        return [urljoin(root + "/", base_path)]
    return [root]


def _deref(node: Any, document: dict, depth: int = 0) -> Any:
    if depth >= _MAX_REF_DEPTH or not isinstance(node, dict):
        return node if isinstance(node, dict) else {}
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    if not ref.startswith("#/"):
        return {}
    target: Any = document
    for raw_token in ref[2:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(target, dict) or token not in target:
            return {}
        target = target[token]
    return _deref(target, document, depth + 1)


def _parameters(raw: Any, document: dict) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out = []
    for entry in raw:
        resolved = _deref(entry, document)
        if isinstance(resolved, dict) and resolved.get("name"):
            out.append(resolved)
    return out


def _names(params: list[dict], location: str) -> list[str]:
    seen: dict[str, None] = {}
    for param in params:
        if param.get("in") == location and isinstance(param.get("name"), str):
            seen.setdefault(param["name"], None)
    return list(seen)[:_MAX_QUERY_PARAMS]


def _body_fields(raw: Any, document: dict) -> list[str]:
    body = _deref(raw, document)
    content = body.get("content") if isinstance(body, dict) else None
    if not isinstance(content, dict):
        return []
    for media in content.values():
        schema = (
            _deref(media.get("schema"), document) if isinstance(media, dict) else {}
        )
        props = schema.get("properties") if isinstance(schema, dict) else None
        if isinstance(props, dict):
            return [name for name in props if isinstance(name, str)]
    return []


def _build_url(base: str, template: str, query: list[str]) -> str:
    filled = _PATH_TEMPLATE.sub(_PATH_SAMPLE, template)
    joined = base.rstrip("/") + "/" + filled.lstrip("/")
    if not query:
        return joined
    return joined + "?" + "&".join(f"{name}=" for name in query)


def _roots(hosts) -> list[str]:
    seen: dict[str, None] = {}
    for host in hosts:
        seen.setdefault(f"{host.scheme}://{host_port(host.host, host.port)}", None)
    return list(seen)
