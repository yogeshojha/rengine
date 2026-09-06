from __future__ import annotations

from shared.definitions.asset_query import (
    CONNECTORS,
    HOST_QUERY,
    MAX_FREE_TERMS,
    MAX_QUERY_LENGTH,
    OP_HELP,
    OPS_BY_TYPE,
    QueryRegistry,
)
from shared.models.asset_query import (
    QueryExampleSpec,
    QueryFieldSpec,
    QueryFlagSpec,
    QueryGroupSpec,
    QueryOperatorSpec,
    QuerySchema,
)


def build_schema(registry: QueryRegistry = HOST_QUERY) -> QuerySchema:
    return QuerySchema(
        max_length=MAX_QUERY_LENGTH,
        max_terms=MAX_FREE_TERMS,
        noun=registry.noun,
        noun_plural=registry.noun_plural,
        groups=list(registry.groups),
        example_groups=list(registry.example_groups),
        group_dimensions=[
            QueryGroupSpec(key=d.key, label=d.label, description=d.description)
            for d in registry.dimensions
        ],
        fields=[
            QueryFieldSpec(
                name=spec.name,
                type=spec.type.value,
                group=spec.group,
                description=spec.description,
                example=spec.example,
                aliases=list(spec.aliases),
                values=list(spec.values),
                facet=spec.facet,
                operators=[op.value for op in OPS_BY_TYPE[spec.type]],
                free_text=spec.free_text,
                unit=spec.unit,
                dynamic_sub=spec.dynamic_sub,
            )
            for spec in registry.fields
        ],
        operators=[
            QueryOperatorSpec(symbol=symbol, description=description)
            for symbol, description in OP_HELP.items()
        ],
        connectors=[
            QueryOperatorSpec(symbol=symbol, description=description)
            for symbol, description in CONNECTORS.items()
        ],
        flags=[
            QueryFlagSpec(value=value, description=description)
            for value, description in registry.flags.items()
        ],
        examples=[
            QueryExampleSpec(
                query=item.query,
                description=item.description,
                group=item.group,
                generic=item.generic,
            )
            for item in registry.examples
        ],
    )
