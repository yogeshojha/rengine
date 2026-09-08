"""Every connector under connectors/, discovered by module. No registry edit."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from functools import lru_cache

from connectors.base import ProxyConnector
from shared.definitions.connectors import ConnectorKind
from shared.logging import get_logger

logger = get_logger(__name__)


class ConnectorRegistrationError(RuntimeError):
    """A connector module declares an invalid connector."""


def _validate(instance: ProxyConnector) -> None:
    for attribute in ("kind", "title", "description"):
        if not getattr(instance, attribute, None):
            msg = f"{type(instance).__qualname__} must set `{attribute}`."
            raise ConnectorRegistrationError(msg)
    if instance.kind not in {k.value for k in ConnectorKind}:
        msg = f"{type(instance).__qualname__} declares unknown kind {instance.kind!r}."
        raise ConnectorRegistrationError(msg)


@lru_cache(maxsize=1)
def connectors() -> dict[str, ProxyConnector]:
    package = sys.modules[__package__]
    found: dict[str, ProxyConnector] = {}
    for module in pkgutil.iter_modules(package.__path__):
        if not module.ispkg:
            continue
        try:
            loaded = importlib.import_module(f"connectors.{module.name}.connector")
        except Exception as exc:  # a broken module must not break discovery
            logger.warning(
                "connector module failed to import", module=module.name, error=str(exc)
            )
            continue
        for value in vars(loaded).values():
            if (
                isinstance(value, type)
                and issubclass(value, ProxyConnector)
                and value is not ProxyConnector
            ):
                instance = value()
                _validate(instance)
                found[instance.kind] = instance
    return dict(sorted(found.items()))


def connector(kind: str) -> ProxyConnector | None:
    return connectors().get(kind)


def kinds() -> list[str]:
    return list(connectors())
