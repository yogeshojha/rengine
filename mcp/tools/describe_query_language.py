"""The grammar, on demand. Too large for a tool description, exact when fetched."""

from __future__ import annotations

from pydantic import Field

from mcp.context import ToolContext
from mcp.dimensions import DIMENSION_KEYS, dimension
from mcp.result import ToolResult
from mcp.tools.base import Tool, ToolGroup, ToolInput


class Input(ToolInput):
    dimension: str = Field(
        default=DIMENSION_KEYS[0],
        description=f"Which grammar to describe. One of: {', '.join(DIMENSION_KEYS)}.",
    )
    fields_only: bool = Field(
        default=False,
        description="Return just the field names, for a quick check.",
    )


class DescribeQueryLanguage(Tool):
    name = "describe_query_language"
    title = "Describe query language"
    group = ToolGroup.ORIENT.value
    description = (
        "The exact query grammar for one dimension: every field with its type and "
        "operators, every is:/has: flag, the group keys, and worked examples. "
        "Fetch this before writing a query you are unsure about — a rejected query "
        "costs a round trip, and the fields differ per dimension."
    )
    Input = Input
    examples = ("describe_query_language dimension=services",)

    async def run(self, ctx: ToolContext, args: Input) -> ToolResult:  # noqa: ARG002
        from app.services.asset_query import build_schema  # noqa: PLC0415

        dim = dimension(args.dimension)
        schema = build_schema(dim.registry)

        if args.fields_only:
            names = sorted(f.name for f in schema.fields)
            return ToolResult(
                summary=f"{len(names)} fields on the {schema.noun} grammar",
                data={"dimension": dim.key, "fields": names},
            )

        fields = [
            {
                "name": f.name,
                "type": f.type,
                "operators": f.operators,
                "means": f.description,
                "example": f.example,
                **({"values": f.values} if f.values else {}),
                **({"aliases": f.aliases} if f.aliases else {}),
            }
            for f in schema.fields
        ]

        return ToolResult(
            summary=(
                f"{len(fields)} fields, {len(schema.flags)} flags and "
                f"{len(schema.group_dimensions)} group keys for {dim.label}"
            ),
            data={
                "dimension": dim.key,
                "noun": schema.noun,
                "max_query_length": schema.max_length,
                "connectors": [
                    {"symbol": c.symbol, "means": c.description}
                    for c in schema.connectors
                ],
                "operators": [
                    {"symbol": o.symbol, "means": o.description}
                    for o in schema.operators
                ],
                "flags": [
                    {"flag": f.value, "means": f.description} for f in schema.flags
                ],
                "fields": fields,
                "group_keys": [
                    {"key": g.key, "label": g.label, "means": g.description}
                    for g in schema.group_dimensions
                ],
                "examples": [
                    {"query": e.query, "means": e.description}
                    for e in schema.examples[:20]
                ],
            },
        )
