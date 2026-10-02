"""The AI tab's own service: connection, features, usage and the narrative cache."""

from __future__ import annotations

import time
import uuid
from urllib.parse import urlsplit

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.instance_settings import InstanceSettingsService
from shared.definitions.ai import (
    AI_FEATURES,
    BASE_URL_HINT,
    BASE_URL_PROVIDERS,
    DEFAULT_AI_FEATURES,
    FEATURE_LABELS,
    KEY_OPTIONAL_PROVIDERS,
    MODELS,
    PROVIDER_HELP,
    PROVIDER_KEY_HINT,
    PROVIDER_LABELS,
    AITask,
    model_for,
)
from shared.enums.instance import AIProvider
from shared.models.ai import (
    AiCall,
    AiCallRead,
    AiFeatureUsage,
    AiNarrative,
    AiSettingsUpdate,
    AiStatus,
    AiTestRequest,
    AiTestResult,
    AiUsageRead,
)
from shared.models.instance_settings import InstanceSettings
from shared.services.ai import ledger
from shared.services.ai.client import AIError, complete
from shared.services.ai.config import AIConfig
from shared.services.scan_resolve import MASK, mask_tail
from shared.utils.crypto import encrypt_secret, try_decrypt
from shared.utils.datetime import utc_now

_VALID_PROVIDERS = frozenset(PROVIDER_LABELS)
_TEST_PROMPT = "Reply with the single word: ready."


def _clean_base_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Server URL must start with http:// or https://.",
        )
    if "@" in parts.netloc or "?" in value:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Server URL cannot carry credentials or a query. Enter the key under API key.",
        )
    return value.rstrip("/")


def _stored_url(features: dict) -> str:
    return str(features.get("base_url") or "").strip().rstrip("/")


def _server(provider: str, base_url: str) -> tuple[str, str]:
    return provider, base_url if provider in BASE_URL_PROVIDERS else ""


def _fresh_key(api_key: str | None) -> bool:
    return api_key is not None and MASK not in api_key


class AiSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _row(self) -> InstanceSettings:
        return await InstanceSettingsService(self.session).get_or_create()

    async def status(self, *, full: bool = False) -> AiStatus:
        row = await self._row()
        key = try_decrypt(row.ai_api_key_encrypted)
        provider = row.ai_provider or AIProvider.ANTHROPIC.value
        stored = row.ai_features or {}
        return AiStatus(
            enabled=row.ai_enabled,
            configured=bool(row.ai_api_key_encrypted),
            provider=provider,
            model=model_for(provider, row.ai_model),
            fast_model=model_for(provider, stored.get("fast_model"), fast=True),
            workspace_id=str(stored.get("workspace_id") or "") if full else None,
            base_url=str(stored.get("base_url") or "") if full else None,
            key_masked=mask_tail(key) if key else None,
            features={
                **DEFAULT_AI_FEATURES,
                **{k: v for k, v in stored.items() if isinstance(v, bool)},
            },
            usage=await self.usage(),
            cached_narratives=int(
                await self.session.scalar(select(func.count(AiNarrative.id))) or 0
            ),
        )

    async def usage(self) -> AiUsageRead:
        rows = (
            await self.session.execute(
                select(
                    AiCall.feature,
                    func.count(AiCall.id),
                    func.count(AiCall.id).filter(AiCall.cached.is_(True)),
                    func.count(AiCall.id).filter(AiCall.ok.is_(False)),
                    func.coalesce(func.sum(AiCall.input_tokens), 0),
                    func.coalesce(func.sum(AiCall.output_tokens), 0),
                    func.sum(AiCall.cost_usd),
                    func.max(AiCall.at),
                    func.min(AiCall.at),
                ).group_by(AiCall.feature)
            )
        ).all()
        by_feature = [
            AiFeatureUsage(
                feature=feature,
                label=FEATURE_LABELS.get(feature, feature),
                calls=int(calls),
                cached=int(cached),
                failed=int(failed),
                input_tokens=int(tokens_in),
                output_tokens=int(tokens_out),
                cost_usd=round(float(cost), 4) if cost is not None else None,
                last_at=last,
            )
            for feature, calls, cached, failed, tokens_in, tokens_out, cost, last, _ in rows
        ]
        by_feature.sort(key=lambda f: (-(f.cost_usd or 0), -f.calls))
        costs = [f.cost_usd for f in by_feature if f.cost_usd is not None]
        return AiUsageRead(
            calls=sum(f.calls - f.cached for f in by_feature),
            failed=sum(f.failed for f in by_feature),
            cost_usd=round(sum(costs), 4) if costs else None,
            since=min((r[8] for r in rows if r[8] is not None), default=None),
            by_feature=by_feature,
        )

    async def calls(self, limit: int) -> list[AiCallRead]:
        rows = (
            await self.session.execute(
                select(AiCall).order_by(AiCall.at.desc()).limit(limit)
            )
        ).scalars()
        return [AiCallRead.model_validate(r, from_attributes=True) for r in rows]

    async def update(self, data: AiSettingsUpdate) -> AiStatus:
        row = await self._row()
        if data.provider is not None and data.provider not in _VALID_PROVIDERS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Unknown provider '{data.provider}'.",
            )
        features = dict(row.ai_features or {})
        stored_provider = row.ai_provider or AIProvider.ANTHROPIC.value
        new_provider = data.provider or stored_provider
        new_url = (
            _clean_base_url(data.base_url)
            if data.base_url is not None
            else _stored_url(features)
        )
        moved = _server(new_provider, new_url) != _server(
            stored_provider, _stored_url(features)
        )
        if moved and row.ai_api_key_encrypted and not _fresh_key(data.api_key):
            if new_provider not in KEY_OPTIONAL_PROVIDERS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Enter the API key for this server.",
                )
            row.ai_api_key_encrypted = None
        if data.provider is not None:
            row.ai_provider = data.provider
        if data.model is not None:
            row.ai_model = data.model.strip() or None
        if _fresh_key(data.api_key):
            row.ai_api_key_encrypted = (
                encrypt_secret(data.api_key) if data.api_key else None
            )
        if data.features is not None:
            features.update(
                {
                    k: bool(v)
                    for k, v in data.features.items()
                    if k in DEFAULT_AI_FEATURES
                }
            )
        if data.fast_model is not None:
            features["fast_model"] = data.fast_model.strip()
        if data.workspace_id is not None:
            features["workspace_id"] = data.workspace_id.strip()
        if data.base_url is not None:
            features["base_url"] = new_url
        row.ai_features = features
        if data.enabled is not None:
            provider = row.ai_provider or AIProvider.ANTHROPIC.value
            if (
                data.enabled
                and not row.ai_api_key_encrypted
                and provider not in KEY_OPTIONAL_PROVIDERS
            ):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Add an API key before turning AI on.",
                )
            if (
                data.enabled
                and provider in BASE_URL_PROVIDERS
                and not features.get("base_url")
            ):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Set the server URL before turning AI on.",
                )
            row.ai_enabled = data.enabled
        row.updated_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        return await self.status(full=True)

    async def test(
        self, data: AiTestRequest, user_id: uuid.UUID | None = None
    ) -> AiTestResult:
        row = await self._row()
        stored_provider = row.ai_provider or AIProvider.ANTHROPIC.value
        provider = (data.provider or stored_provider).strip()
        stored = row.ai_features or {}
        stored_url = _stored_url(stored)
        base_url = _clean_base_url(data.base_url or stored_url)
        same = _server(provider, base_url) == _server(stored_provider, stored_url)
        if data.api_key and _fresh_key(data.api_key):
            key = data.api_key
        else:
            key = try_decrypt(row.ai_api_key_encrypted) if same else None
        if not key and provider not in KEY_OPTIONAL_PROVIDERS:
            return AiTestResult(
                success=False,
                message=(
                    "No API key is configured."
                    if same
                    else "Enter the API key for this server."
                ),
            )
        if provider in BASE_URL_PROVIDERS and not base_url:
            return AiTestResult(success=False, message="No server URL is configured.")
        model = model_for(provider, data.model or row.ai_model)
        if not model:
            return AiTestResult(success=False, message="No model is configured.")
        cfg = AIConfig(
            provider=provider,
            api_key=key,
            model=model,
            fast_model=model,
            features=dict.fromkeys(DEFAULT_AI_FEATURES, True),
            enabled=True,
            workspace=(data.workspace_id or stored.get("workspace_id") or "").strip(),
            timeout=30.0,
            base_url=base_url,
        )
        started = time.monotonic()
        try:
            with ledger.source("user", user_id, user_id):
                result = await run_in_threadpool(
                    complete,
                    cfg,
                    system="Answer in one word.",
                    prompt=_TEST_PROMPT,
                    task=AITask.CONNECTION_TEST.value,
                    fast=False,
                )
        except AIError as exc:
            return AiTestResult(success=False, message=str(exc)[:300], model=model)
        except Exception as exc:
            return AiTestResult(
                success=False, message=f"{type(exc).__name__}: {exc}"[:300], model=model
            )
        return AiTestResult(
            success=True,
            message=f"{PROVIDER_LABELS.get(provider, provider)} answered in {int((time.monotonic() - started) * 1000)} ms.",
            model=result.model,
            latency_ms=result.latency_ms,
        )

    async def clear_cache(self) -> int:
        count = int(await self.session.scalar(select(func.count(AiNarrative.id))) or 0)
        await self.session.execute(delete(AiNarrative))
        await self.session.commit()
        return count

    @staticmethod
    def catalog() -> dict:
        return {
            "providers": [
                {
                    "key": key,
                    "label": label,
                    "key_hint": PROVIDER_KEY_HINT.get(key, ""),
                    "help": PROVIDER_HELP.get(key, ""),
                    "key_optional": key in KEY_OPTIONAL_PROVIDERS,
                    "needs_base_url": key in BASE_URL_PROVIDERS,
                    "base_url_hint": BASE_URL_HINT if key in BASE_URL_PROVIDERS else "",
                    "models": [
                        {
                            "id": m.id,
                            "label": m.label,
                            "note": m.note,
                            "input_per_mtok": m.input_per_mtok,
                            "output_per_mtok": m.output_per_mtok,
                            "context": m.context,
                        }
                        for m in MODELS
                        if m.provider == key
                    ],
                }
                for key, label in PROVIDER_LABELS.items()
            ],
            "features": [
                {"key": f.key, "label": f.label, "help": f.help, "default": f.default}
                for f in AI_FEATURES
            ],
        }
