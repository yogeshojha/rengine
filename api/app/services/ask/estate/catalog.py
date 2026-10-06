"""The query grammar as the model reads it, generated from the registries."""

from __future__ import annotations

from functools import lru_cache

from app.services.ask.estate.dimensions import DIMENSIONS, groupable
from shared.definitions.surface import SurfaceDimension
from shared.services.asset_query import build_schema

MAX_MEANING = 110
MAX_EXAMPLES = 10
# fields left out of the catalog
HIDDEN_FIELDS: dict[str, frozenset[str]] = {
    SurfaceDimension.SECRETS.value: frozenset({"value"}),
}


def _clip(text: str | None) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= MAX_MEANING else f"{text[: MAX_MEANING - 1]}…"


def _dimension(key: str) -> str:
    dim = DIMENSIONS[key]
    schema = build_schema(dim.registry)
    hidden = HIDDEN_FIELDS.get(key, frozenset())
    lines = [f"### {key} ({schema.noun_plural})", "Fields:"]
    for f in schema.fields:
        if f.name in hidden:
            continue
        extra = f" values: {', '.join(f.values[:12])}." if f.values else ""
        alias = f" aliases: {', '.join(f.aliases)}." if f.aliases else ""
        lines.append(
            f"- {f.name} {f.type}: {_clip(f.description)} e.g. {f.example}.{extra}{alias}"
        )
    if schema.flags:
        lines.append(
            "Flags: "
            + "; ".join(f"is:{f.value} {_clip(f.description)}" for f in schema.flags)
        )
    if groupable(key):
        keys = [g.key for g in schema.group_dimensions if g.key not in hidden]
        if keys:
            lines.append(f"Group keys: {', '.join(keys)}")
    examples = [e for e in schema.examples if e.query][:MAX_EXAMPLES]
    if examples:
        lines.append("Examples:")
        lines.extend(f"- {e.description}: {e.query}" for e in examples)
    return "\n".join(lines)


@lru_cache(maxsize=1)
def catalog() -> str:
    """Every dimension the estate answers from, with its fields, flags and keys."""
    first = build_schema(DIMENSIONS[next(iter(DIMENSIONS))].registry)
    header = [
        "QUERY LANGUAGE",
        "Operators: "
        + "; ".join(f"{o.symbol} {_clip(o.description)}" for o in first.operators),
        "Connectors: "
        + "; ".join(f"{c.symbol} {_clip(c.description)}" for c in first.connectors),
        "Quote a value with spaces. A list is field:[a,b,c]. Durations read 24h, 7d.",
    ]
    return "\n\n".join(["\n".join(header), *(_dimension(k) for k in DIMENSIONS)])
