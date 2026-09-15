"""What each dimension's export writes, resolved against the rows the query returns."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shared.definitions.surface import (
    SURFACE_COLUMNS,
    SURFACE_TEXT_VALUE,
    SurfaceDimension,
)
from shared.models.endpoint import Endpoint
from shared.models.secret import Secret
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import (
    endpoint_is_new,
    service_is_new,
    vuln_is_new,
    vuln_state,
)
from shared.utils.net import host_port

if TYPE_CHECKING:
    from collections.abc import Sequence

    from shared.services.asset_query import QueryScope

# a display column the api computes per page and a worker cannot reach
UNAVAILABLE: dict[str, frozenset[str]] = {
    SurfaceDimension.WEB_ASSETS.value: frozenset(
        {"endpoint_count", "vuln_count", "vuln_severity", "vuln_kev"}
    ),
    SurfaceDimension.ENDPOINTS.value: frozenset(),
    SurfaceDimension.SERVICES.value: frozenset(),
    SurfaceDimension.IPS.value: frozenset(),
    SurfaceDimension.VULNERABILITIES.value: frozenset(),
    SurfaceDimension.SOFTWARE.value: frozenset(),
    SurfaceDimension.SECRETS.value: frozenset(),
}

# a display column the row carries under another name
RENAMED: dict[str, dict[str, str]] = {
    SurfaceDimension.SERVICES.value: {
        "is_sensitive": "sensitive",
        "version": "version_text",
    },
    SurfaceDimension.IPS.value: {"has_sensitive": "sensitive"},
}

# a display column filled per chunk rather than by the row's own statement
JOINED: dict[str, frozenset[str]] = {
    SurfaceDimension.WEB_ASSETS.value: frozenset({"ports"}),
    SurfaceDimension.SERVICES.value: frozenset({"hosts"}),
    SurfaceDimension.IPS.value: frozenset({"ports", "hosts"}),
    SurfaceDimension.ENDPOINTS.value: frozenset(),
    SurfaceDimension.VULNERABILITIES.value: frozenset(),
    SurfaceDimension.SOFTWARE.value: frozenset(),
    SurfaceDimension.SECRETS.value: frozenset(),
}

# the stored proof a scanner captured, written only when the export asks for it
EVIDENCE: dict[str, tuple[str, ...]] = {
    SurfaceDimension.VULNERABILITIES.value: ("curl_command", "request", "response"),
}

_MODELS = {
    SurfaceDimension.WEB_ASSETS.value: Subdomain,
    SurfaceDimension.ENDPOINTS.value: Endpoint,
    SurfaceDimension.VULNERABILITIES.value: Vulnerability,
    SurfaceDimension.SOFTWARE.value: SoftwareCve,
    SurfaceDimension.SECRETS.value: Secret,
}


def _expressions(
    dimension: str, scope: QueryScope, source: Any = None
) -> dict[str, Any]:
    """Columns the statement computes, not ones the table stores."""
    if dimension == SurfaceDimension.SERVICES.value and source is not None:
        return {"is_new": service_is_new(source, scope)}
    if dimension == SurfaceDimension.ENDPOINTS.value:
        return {"is_new": endpoint_is_new(scope)}
    if dimension == SurfaceDimension.VULNERABILITIES.value:
        return {"is_new": vuln_is_new(scope), "state": vuln_state(scope)}
    return {}


def headers(dimension: str, *, evidence: bool = False) -> list[str]:
    """The export's columns, in the order a person reads them."""
    skip = UNAVAILABLE.get(dimension, frozenset())
    names = [name for name in SURFACE_COLUMNS[dimension] if name not in skip]
    if evidence:
        names.extend(EVIDENCE.get(dimension, ()))
    return names


def offers_evidence(dimension: str) -> bool:
    return bool(EVIDENCE.get(dimension))


def source_key(dimension: str, header: str) -> str:
    return RENAMED.get(dimension, {}).get(header, header)


def selectables(
    dimension: str,
    scope: QueryScope,
    source: Any = None,
    *,
    evidence: bool = False,
) -> list[Any]:
    """Exactly the columns the file needs, so no row carries a body it will not write."""
    joined = JOINED.get(dimension, frozenset())
    computed = _expressions(dimension, scope, source)
    model = _MODELS.get(dimension)
    picked: list[Any] = []
    for name in headers(dimension, evidence=evidence):
        if name in joined:
            continue
        if name in computed:
            picked.append(computed[name].label(name))
            continue
        key = source_key(dimension, name)
        element = getattr(model, key) if model is not None else source.c[key]
        picked.append(element.label(name))
    return picked


def columns_for(dimension: str, scope: QueryScope, *, evidence: bool = False):
    """The CTE dimensions only know their columns once built, so they come as a callable."""
    if dimension in _MODELS:
        return selectables(dimension, scope, evidence=evidence)
    return lambda d: selectables(dimension, scope, d, evidence=evidence)


# the only two-part text value is an authority
_AUTHORITY_PARTS = 2


def text_values(dimension: str, row: dict) -> str:
    """The single value a plain text export writes for this row."""
    parts = [
        str(row[key])
        for key in SURFACE_TEXT_VALUE[dimension]
        if row.get(key) not in (None, "")
    ]
    if len(parts) == _AUTHORITY_PARTS:
        return host_port(*parts)
    return ":".join(parts)


def project(row: Any, names: Sequence[str]) -> dict:
    """One row as a flat dict, whatever shape it came back in."""
    getter = row.get if hasattr(row, "get") else lambda key: getattr(row, key, None)
    return {name: getter(name) for name in names}
