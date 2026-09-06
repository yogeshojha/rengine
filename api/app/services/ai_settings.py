"""The AI tab's own service: connection, features, usage and the narrative cache."""

from __future__ import annotations

import time

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_secret, try_decrypt
from shared.definitions.ai import (
    AI_FEATURES,
    DEFAULT_AI_FEATURES,
    MODELS,
    PROVIDER_KEY_HINT,
    PROVIDER_LABELS,
    model_for,
    price,
)
from shared.enums.instance import AIProvider
from shared.models.ai import (
    AiNarrative,
    AiSettingsUpdate,
    AiStatus,
    AiTestRequest,
    AiTestResult,
    AiUsageRead,
)
from shared.models.instance_settings import InstanceSettings
from shared.models.report import Report
from shared.services.ai.client import AIError, complete
from shared.services.ai.config import AIConfig
from shared.utils.datetime import utc_now

MASK = "••••••••"
_VALID_PROVIDERS = frozenset(p.value for p in AIProvider)
_TEST_PROMPT = "Reply with the single word: ready."
_TAIL = 4


def _mask(key: str | None) -> str | None:
    if not key:
        return None
    return f"{MASK}{key[-4:]}" if len(key) > _TAIL else MASK


class AiSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _row(self) -> InstanceSettings:
        row = (
            (await self.session.execute(select(InstanceSettings).limit(1)))
            .scalars()
            .first()
        )
        if row is None:
            row = InstanceSettings()
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
        return row

    async def status(self) -> AiStatus:
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
            workspace_id=str(stored.get("workspace_id") or ""),
            key_masked=_mask(key),
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
        row = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(Report.ai_calls), 0),
                    func.coalesce(func.sum(Report.ai_cached_calls), 0),
                    func.coalesce(func.sum(Report.ai_input_tokens), 0),
                    func.coalesce(func.sum(Report.ai_output_tokens), 0),
                    func.count(Report.id),
                    func.min(Report.created_at),
                ).where(Report.ai_used.is_(True))
            )
        ).first()
        settings_row = await self._row()
        model = model_for(
            settings_row.ai_provider or AIProvider.ANTHROPIC.value,
            settings_row.ai_model,
        )
        cost = price(model, int(row[2]), int(row[3])) if row else None
        return AiUsageRead(
            calls=int(row[0]) if row else 0,
            cached=int(row[1]) if row else 0,
            input_tokens=int(row[2]) if row else 0,
            output_tokens=int(row[3]) if row else 0,
            cost_usd=round(cost, 4) if cost else None,
            reports=int(row[4]) if row else 0,
            since=row[5] if row else None,
        )

    async def update(self, data: AiSettingsUpdate) -> AiStatus:
        row = await self._row()
        if data.provider is not None:
            if data.provider not in _VALID_PROVIDERS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Unknown provider '{data.provider}'.",
                )
            row.ai_provider = data.provider
        if data.model is not None:
            row.ai_model = data.model.strip() or None
        if data.api_key is not None and MASK not in data.api_key:
            row.ai_api_key_encrypted = (
                encrypt_secret(data.api_key) if data.api_key else None
            )
        features = dict(row.ai_features or {})
        if data.features is not None:
            features.update({k: bool(v) for k, v in data.features.items()})
        if data.fast_model is not None:
            features["fast_model"] = data.fast_model.strip()
        if data.workspace_id is not None:
            features["workspace_id"] = data.workspace_id.strip()
        row.ai_features = features
        if data.enabled is not None:
            if data.enabled and not row.ai_api_key_encrypted:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Add an API key before turning AI on.",
                )
            row.ai_enabled = data.enabled
        row.updated_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        return await self.status()

    async def test(self, data: AiTestRequest) -> AiTestResult:
        row = await self._row()
        provider = (
            data.provider or row.ai_provider or AIProvider.ANTHROPIC.value
        ).strip()
        key = (
            data.api_key
            if data.api_key and MASK not in data.api_key
            else try_decrypt(row.ai_api_key_encrypted)
        )
        if not key:
            return AiTestResult(success=False, message="No API key is configured.")
        model = model_for(provider, data.model or row.ai_model)
        stored = row.ai_features or {}
        cfg = AIConfig(
            provider=provider,
            api_key=key,
            model=model,
            fast_model=model,
            features=dict.fromkeys(DEFAULT_AI_FEATURES, True),
            enabled=True,
            workspace=(data.workspace_id or stored.get("workspace_id") or "").strip(),
            timeout=30.0,
        )
        started = time.monotonic()
        try:
            result = await run_in_threadpool(
                complete,
                cfg,
                system="Answer in one word.",
                prompt=_TEST_PROMPT,
                task="risk_narrative",
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
