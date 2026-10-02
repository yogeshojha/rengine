"""Resolve the provider in use into something a client can use."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from shared.definitions.ai import (
    BASE_URL_PROVIDERS,
    KEY_OPTIONAL_PROVIDERS,
    REQUEST_TIMEOUT,
    WORKSPACE_PROVIDERS,
    Rate,
    feature_switches,
    price,
)
from shared.enums.instance import AIProvider
from shared.models.ai import AiConnection
from shared.models.instance_settings import InstanceSettings
from shared.utils.crypto import try_decrypt

VALID_PROVIDERS: frozenset[str] = frozenset(p.value for p in AIProvider)


@dataclass(frozen=True)
class AIConfig:
    provider: str
    api_key: str
    model: str
    features: dict[str, bool]
    enabled: bool = True
    workspace: str = ""
    timeout: float = REQUEST_TIMEOUT
    base_url: str = ""
    input_per_mtok: float | None = None
    output_per_mtok: float | None = None

    @property
    def available(self) -> bool:
        if not self.enabled or self.provider not in VALID_PROVIDERS or not self.model:
            return False
        if not self.api_key and self.provider not in KEY_OPTIONAL_PROVIDERS:
            return False
        return bool(self.base_url) or self.provider not in BASE_URL_PROVIDERS

    def allows(self, feature: str) -> bool:
        return self.available and bool(self.features.get(feature, False))

    def listed_price(self, model: str) -> Rate | None:
        """The price the provider listed for its model, for a call on that model."""
        if model != self.model:
            return None
        if self.input_per_mtok is None or self.output_per_mtok is None:
            return None
        return (self.input_per_mtok, self.output_per_mtok)

    def cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        return price(model, input_tokens, output_tokens, self.listed_price(model))


def connection_config(
    row: AiConnection,
    *,
    features: dict[str, bool] | None = None,
    enabled: bool = True,
    timeout: float = REQUEST_TIMEOUT,
) -> AIConfig:
    """A client config for one saved provider."""
    workspace = row.workspace_id if row.provider in WORKSPACE_PROVIDERS else None
    base_url = row.base_url if row.provider in BASE_URL_PROVIDERS else None
    return AIConfig(
        provider=row.provider,
        api_key=try_decrypt(row.api_key_encrypted) or "",
        model=row.model,
        features=features if features is not None else feature_switches(None),
        enabled=enabled,
        workspace=workspace or "",
        timeout=timeout,
        base_url=(base_url or "").strip(),
        input_per_mtok=row.input_per_mtok,
        output_per_mtok=row.output_per_mtok,
    )


_IN_USE = (
    select(InstanceSettings.ai_enabled, InstanceSettings.ai_features, AiConnection)
    .outerjoin(AiConnection, AiConnection.id == InstanceSettings.ai_connection_id)
    .limit(1)
)


def _build(row) -> AIConfig | None:
    if row is None:
        return None
    enabled, stored, connection = row
    features = feature_switches(stored)
    if connection is None:
        return AIConfig(
            provider="",
            api_key="",
            model="",
            features=features,
            enabled=bool(enabled),
        )
    return connection_config(connection, features=features, enabled=bool(enabled))


def load_config(session) -> AIConfig | None:
    return _build(session.execute(_IN_USE).first())


async def load_config_async(session) -> AIConfig | None:
    return _build((await session.execute(_IN_USE)).first())
