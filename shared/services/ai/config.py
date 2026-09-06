"""Resolve the instance's AI settings into something a client can use."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from shared.definitions.ai import (
    DEFAULT_AI_FEATURES,
    REQUEST_TIMEOUT,
    model_for,
)
from shared.enums.instance import AIProvider
from shared.models.instance_settings import InstanceSettings
from shared.utils.crypto import try_decrypt

VALID_PROVIDERS: frozenset[str] = frozenset(p.value for p in AIProvider)


@dataclass(frozen=True)
class AIConfig:
    provider: str
    api_key: str
    model: str
    fast_model: str
    features: dict[str, bool]
    enabled: bool = True
    workspace: str = ""
    timeout: float = REQUEST_TIMEOUT

    @property
    def available(self) -> bool:
        return bool(self.enabled and self.api_key and self.provider in VALID_PROVIDERS)

    def allows(self, feature: str) -> bool:
        return self.available and bool(self.features.get(feature, False))

    def model_for_task(self, *, fast: bool) -> str:
        return self.fast_model if fast else self.model


def _build(row: InstanceSettings | None) -> AIConfig | None:
    if row is None:
        return None
    provider = (row.ai_provider or AIProvider.ANTHROPIC.value).strip()
    key = try_decrypt(row.ai_api_key_encrypted) or ""
    stored = row.ai_features or {}
    features = {
        **DEFAULT_AI_FEATURES,
        **{k: v for k, v in stored.items() if isinstance(v, bool)},
    }
    return AIConfig(
        provider=provider,
        api_key=key,
        model=model_for(provider, row.ai_model),
        fast_model=model_for(provider, stored.get("fast_model"), fast=True),
        features=features,
        enabled=bool(row.ai_enabled),
        workspace=str(stored.get("workspace_id") or ""),
    )


def load_config(session) -> AIConfig | None:
    row = session.execute(select(InstanceSettings).limit(1)).scalars().first()
    return _build(row)


async def load_config_async(session) -> AIConfig | None:
    result = await session.execute(select(InstanceSettings).limit(1))
    return _build(result.scalars().first())
