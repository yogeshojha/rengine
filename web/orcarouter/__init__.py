"""OrcaRouter provider for reNgine.

This package is the single place that knows how to talk to OrcaRouter. It has
no Django imports so the catalog/discovery logic can be exercised directly by
unit tests, while the Django views load and persist the API key.

Public surface:

- :mod:`orcarouter.config` -- public origins, limits and capability vocabulary.
- :mod:`orcarouter.catalog` -- bounded ``GET /v1/models`` discovery, capability
  filtering and the verified cold-start seed.
- :mod:`orcarouter.client` -- OpenAI-compatible chat completions and the small
  credential helpers shared by the views and the LLM generators.
"""

from .catalog import (  # noqa: F401
    CatalogResult,
    OrcaRouterCatalogError,
    fetch_chat_catalog,
    filter_models,
    model_ids,
    parse_catalog_payload,
    reconcile_selection,
    seed_catalog,
)
from .client import (  # noqa: F401
    OrcaRouterError,
    chat_completion,
    mask_key,
    resolve_api_key,
)

__all__ = [
    'CatalogResult',
    'OrcaRouterCatalogError',
    'OrcaRouterError',
    'chat_completion',
    'fetch_chat_catalog',
    'filter_models',
    'mask_key',
    'model_ids',
    'parse_catalog_payload',
    'reconcile_selection',
    'resolve_api_key',
    'seed_catalog',
]
