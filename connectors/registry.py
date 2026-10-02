"""Every connector under connectors/, discovered by module."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from connectors.base import ProxyConnector
from shared.definitions.connectors import ConnectorKind
from shared.plugins import classes_in_packages


class ConnectorRegistrationError(RuntimeError):
    """A connector module declares an invalid connector."""


def _validate(instance: ProxyConnector) -> None:
    for attribute in ("kind", "title"):
        if not getattr(instance, attribute, None):
            msg = f"{type(instance).__qualname__} must set `{attribute}`."
            raise ConnectorRegistrationError(msg)
    if instance.kind not in {k.value for k in ConnectorKind}:
        msg = f"{type(instance).__qualname__} declares unknown kind {instance.kind!r}."
        raise ConnectorRegistrationError(msg)


@lru_cache(maxsize=1)
def connectors() -> dict[str, ProxyConnector]:
    found: dict[str, ProxyConnector] = {}
    for root in sys.modules[__package__].__path__:
        for cls in classes_in_packages(
            __package__, Path(root), ProxyConnector, submodules=("connector",)
        ):
            instance = cls()
            _validate(instance)
            found[instance.kind] = instance
    return dict(sorted(found.items()))


def connector(kind: str) -> ProxyConnector | None:
    return connectors().get(kind)
