"""The API reference, built from the app's OpenAPI document."""

from __future__ import annotations

from typing import Any

from app.api.deps import route_facts, served_routes
from app.config import API_V1_PREFIX
from shared.definitions.access_keys import AccessKeyLevel, KeyRule, key_rule
from shared.definitions.api_reference import (
    EXAMPLE_FIELDS,
    EXAMPLE_VALUE,
    GROUP_ORDER,
    METHOD_ORDER,
    curl,
    placement,
    variable,
)
from shared.models.reference import (
    ReferenceGroup,
    ReferenceOperation,
    ReferenceParameter,
)

LEVELS = {KeyRule.READ: AccessKeyLevel.READ, KeyRule.WRITE: AccessKeyLevel.WRITE}
LISTED_LOCATIONS = ("path", "query")
MAX_REF_HOPS = 8
MAX_EXAMPLE_DEPTH = 3
SCALAR_EXAMPLES: dict[str, Any] = {"integer": 1, "number": 1, "boolean": True}

_built: dict[int, list[ReferenceGroup]] = {}


class _Schemas:
    def __init__(self, document: dict[str, Any]) -> None:
        self.components = document.get("components", {}).get("schemas", {})

    def resolve(self, schema: dict[str, Any] | None) -> dict[str, Any]:
        schema = schema or {}
        seen = 0
        while "$ref" in schema and seen < MAX_REF_HOPS:
            schema = self.components.get(schema["$ref"].rsplit("/", 1)[-1], {})
            seen += 1
        return schema

    def present(self, schema: dict[str, Any] | None) -> dict[str, Any]:
        schema = self.resolve(schema)
        options = [
            self.resolve(s)
            for s in schema.get("anyOf", ())
            if self.resolve(s).get("type") != "null"
        ]
        return options[0] if len(options) == 1 else schema

    def type_of(self, schema: dict[str, Any] | None) -> str:
        schema = self.resolve(schema)
        if "anyOf" in schema:
            names = [
                self.type_of(s)
                for s in schema["anyOf"]
                if self.resolve(s).get("type") != "null"
            ]
            return " or ".join(dict.fromkeys(names)) or "string"
        kind = schema.get("type")
        if kind == "array":
            return f"array of {self.type_of(schema.get('items'))}"
        if kind == "string" and schema.get("format") in ("uuid", "date-time", "date"):
            return schema["format"]
        if kind:
            return kind
        return "object" if "properties" in schema else "string"

    def value(self, schema: dict[str, Any] | None, depth: int = 0) -> Any:
        schema = self.present(schema)
        for given in (schema.get("examples"), schema.get("enum")):
            if given:
                return given[0]
        if schema.get("default") is not None:
            return schema["default"]
        kind = schema.get("type")
        if kind == "array":
            return [self.value(schema.get("items"), depth + 1)]
        if kind in SCALAR_EXAMPLES:
            return schema.get("minimum", SCALAR_EXAMPLES[kind])
        if kind == "object" or "properties" in schema:
            return self.body(schema, depth + 1) if depth < MAX_EXAMPLE_DEPTH else {}
        return EXAMPLE_VALUE

    def body(self, schema: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        properties = schema.get("properties", {})
        required = set(schema.get("required", ()))
        chosen = [
            name
            for name, prop in properties.items()
            if name in required or self.resolve(prop).get("examples")
        ]
        if not chosen and properties and depth == 0:
            preferred = [name for name in EXAMPLE_FIELDS if name in properties]
            chosen = preferred[:1] or [next(iter(properties))]
        return {name: self.value(properties[name], depth) for name in chosen}


def _operation(
    schemas: _Schemas,
    group: str,
    rule: KeyRule,
    method: str,
    path: str,
    summary: str,
    op: dict,
) -> ReferenceOperation | None:
    parameters: list[ReferenceParameter] = []
    query: list[str] = []
    for param in op.get("parameters", ()):
        if param.get("in") not in LISTED_LOCATIONS:
            continue
        schema = param.get("schema")
        parameters.append(
            ReferenceParameter(
                name=param["name"],
                location=param["in"],
                required=bool(param.get("required")),
                type=schemas.type_of(schema),
                description=param.get("description"),
            )
        )
        if param["in"] == "query" and param.get("required"):
            shown = schemas.present(schema)
            if shown.get("type") == "array":
                shown = schemas.present(shown.get("items"))
            value = shown.get("enum", [None])[0] or variable(param["name"])
            query.append(f"{param['name']}={value}")
    body = None
    content = op.get("requestBody", {}).get("content", {})
    if "application/json" in content:
        schema = schemas.resolve(content["application/json"].get("schema"))
        required = set(schema.get("required", ()))
        for name, prop in schema.get("properties", {}).items():
            parameters.append(
                ReferenceParameter(
                    name=name,
                    location="body",
                    required=name in required,
                    type=schemas.type_of(prop),
                    description=schemas.resolve(prop).get("description"),
                )
            )
        body = schemas.body(schema)
    elif content:
        return None
    return ReferenceOperation(
        group=group,
        method=method,
        path=path,
        summary=summary,
        access=LEVELS[rule],
        parameters=parameters,
        example=body,
        curl=curl(method, path, query, body),
    )


def build(app: Any) -> list[ReferenceGroup]:
    """Operations an access key can call that carry a written summary, by group."""
    document = app.openapi()
    schemas = _Schemas(document)
    grouped: dict[str, list[tuple[tuple, ReferenceOperation]]] = {
        name: [] for name in GROUP_ORDER
    }
    for route in served_routes(app):
        summary = getattr(route, "summary", None)
        if not summary or not getattr(route, "include_in_schema", True):
            continue
        facts = route_facts(route, API_V1_PREFIX)
        placed = placement(facts.path)
        if placed is None:
            continue
        group, rank = placed
        for method in sorted((route.methods or set()) - {"HEAD"}):
            rule = key_rule(method, facts.path, gated=facts.gated)
            if rule is KeyRule.REFUSED:
                continue
            op = document["paths"].get(route.path_format, {}).get(method.lower())
            if op is None:
                continue
            found = _operation(
                schemas, group, rule, method, route.path_format, summary, op
            )
            if found is not None:
                order = (rank, facts.path, METHOD_ORDER.index(method))
                grouped[group].append((order, found))
    return [
        ReferenceGroup(
            name=name, operations=[op for _, op in sorted(ops, key=lambda o: o[0])]
        )
        for name, ops in grouped.items()
        if ops
    ]


def reference(app: Any) -> list[ReferenceGroup]:
    """The reference for this process, built once."""
    if id(app) not in _built:
        _built[id(app)] = build(app)
    return _built[id(app)]
