"""Fold a batch of proxy traffic into request shapes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from connectors.shape import templatize
from shared.definitions.connectors import (
    INGESTED_TOOLS,
    MAX_BODY_SAMPLE,
    SourceTool,
)
from shared.definitions.endpoints import (
    MAX_PARAMS,
    STATIC_CLASSES,
    EndpointClass,
    ParsedUrl,
    classify,
    interests_for,
    is_static,
    parse_url,
    signature_for,
)
from shared.utils.text import strip_control

NOISE_CLASSES = STATIC_CLASSES | {EndpointClass.SCRIPT.value, EndpointClass.STYLE.value}


def _is_noise(endpoint_class: str | None, extension: str | None) -> bool:
    return endpoint_class in NOISE_CLASSES or is_static(endpoint_class, extension)


@dataclass
class Prepared:
    """One request shape, folded from every item in the batch sharing it."""

    parsed: ParsedUrl
    signature: str
    params: tuple[str, ...]
    shape: str = "/"
    collapsed: int = 0
    methods: list[str] = field(default_factory=list)
    status_code: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    title: str | None = None
    authenticated: bool = False
    source_tool: str = SourceTool.PROXY.value
    endpoint_class: str | None = None
    interests: list[str] = field(default_factory=list)
    request_sample: str | None = None
    observed_at: datetime | None = None
    hits: int = 1


@dataclass
class Batch:
    prepared: list[Prepared] = field(default_factory=list)
    seen: int = 0
    rejected: int = 0
    hosts: set[str] = field(default_factory=set)
    hosts_seen: dict[str, int] = field(default_factory=dict)


def _merge(into: Prepared, item) -> None:
    into.hits += 1
    method = strip_control(item.method or "GET").upper()[:16]
    if method not in into.methods:
        into.methods.append(method)
    if item.status_code is not None:
        into.status_code = item.status_code
    if item.content_type and not into.content_type:
        into.content_type = item.content_type[:120]
    if item.content_length is not None:
        into.content_length = item.content_length
    if item.title and not into.title:
        into.title = strip_control(item.title)[:500]
    into.authenticated = into.authenticated or bool(item.authenticated)
    if item.source_tool == SourceTool.REPEATER.value:
        into.source_tool = SourceTool.REPEATER.value
    if item.request_sample and not into.request_sample:
        into.request_sample = strip_control(item.request_sample)[:MAX_BODY_SAMPLE]
    if item.observed_at and (
        into.observed_at is None or item.observed_at > into.observed_at
    ):
        into.observed_at = item.observed_at


def prepare(items, *, include_static: bool, ingest_tools: list[str]) -> Batch:
    """Fold a batch onto its request shapes: a path shape plus its parameter names."""
    allowed = {t for t in (ingest_tools or []) if t in INGESTED_TOOLS} or set(
        INGESTED_TOOLS
    )
    batch = Batch()
    folded: dict[str, Prepared] = {}
    for item in items:
        batch.seen += 1
        tool = item.source_tool if item.source_tool in INGESTED_TOOLS else None
        if tool is None or tool not in allowed:
            batch.rejected += 1
            continue
        parsed = parse_url(strip_control(item.url or ""))
        if parsed is None:
            batch.rejected += 1
            continue
        batch.hosts_seen[parsed.host] = batch.hosts_seen.get(parsed.host, 0) + 1
        # a form post names parameters the URL does not carry
        params = parsed.params
        if item.body_params:
            extra = [
                strip_control(p).strip()[:100]
                for p in item.body_params
                if p and strip_control(p).strip()
            ]
            params = tuple(sorted({*params, *extra})[:MAX_PARAMS])
        shape, collapsed = templatize(parsed.path)
        endpoint_class = classify(parsed.path, parsed.extension, item.content_type)
        if not include_static and _is_noise(endpoint_class, parsed.extension):
            batch.rejected += 1
            continue
        signature = signature_for(
            parsed.scheme, parsed.host, parsed.port, shape, params
        )
        existing = folded.get(signature)
        if existing is not None:
            _merge(existing, item)
            continue
        folded[signature] = Prepared(
            parsed=parsed,
            signature=signature,
            params=params,
            shape=shape,
            collapsed=collapsed,
            methods=[strip_control(item.method or "GET").upper()[:16]],
            status_code=item.status_code,
            content_type=(
                strip_control(item.content_type)[:120] if item.content_type else None
            ),
            content_length=item.content_length,
            title=strip_control(item.title)[:500] if item.title else None,
            authenticated=bool(item.authenticated),
            source_tool=tool,
            endpoint_class=endpoint_class,
            interests=interests_for(
                shape,
                params,
                endpoint_class=endpoint_class,
                extension=parsed.extension,
            ),
            request_sample=(
                strip_control(item.request_sample)[:MAX_BODY_SAMPLE]
                if item.request_sample
                else None
            ),
            observed_at=item.observed_at,
        )
        batch.hosts.add(parsed.host)
    batch.prepared = list(folded.values())
    return batch
