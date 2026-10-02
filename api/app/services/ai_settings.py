"""The AI tab's own service: providers, features, usage and the narrative cache."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.instance_settings import InstanceSettingsService
from shared.definitions.ai import (
    AI_FEATURES,
    BASE_URL_HINT,
    BASE_URL_PROVIDERS,
    DEFAULT_AI_FEATURES,
    DEFAULT_MODEL,
    FEATURE_LABELS,
    KEY_OPTIONAL_PROVIDERS,
    MAX_CONNECTION_NAME,
    MAX_TEST_MESSAGE,
    MODEL_LIST_TIMEOUT,
    MODELS,
    PROVIDER_HELP,
    PROVIDER_KEY_HINT,
    PROVIDER_LABELS,
    WORKSPACE_PROVIDERS,
    AITask,
    Rates,
    connection_name,
    curated_rates,
    feature_switches,
    model_for,
)
from shared.models.ai import (
    AiCall,
    AiCallPage,
    AiCallRead,
    AiConnection,
    AiConnectionCreate,
    AiConnectionRead,
    AiConnectionUpdate,
    AiFeatureUsage,
    AiModelList,
    AiModelsRequest,
    AiNarrative,
    AiOnboarding,
    AiOnboardingRead,
    AiSettingsUpdate,
    AiStatus,
    AiTestRequest,
    AiTestResult,
    AiUsageRead,
)
from shared.models.instance_settings import InstanceSettings
from shared.services.ai import ledger, prices, rates
from shared.services.ai.client import AIError, complete, list_models, scrub_error
from shared.services.ai.config import AIConfig, connection_config
from shared.services.scan_resolve import MASK, mask_tail
from shared.utils.crypto import encrypt_secret, try_decrypt
from shared.utils.datetime import utc_now

_VALID_PROVIDERS = frozenset(PROVIDER_LABELS)
_TEST_PROMPT = "Reply with the single word: ready."
_TEST_TIMEOUT = 30.0
_NOT_FOUND = "Provider not found."
_NO_PROVIDER = "Choose a provider."
_NO_KEY = "Enter the API key for this server."
_NO_URL = "Enter the server URL."
_NO_MODEL = "Choose a model."
_NO_PRICE = "Enter an input and an output price."
_BAD_CURSOR = "Cursor not read. Pass the at and id of the last row, joined by a comma."
_PRICE_FIELDS = frozenset(
    {"input_per_mtok", "output_per_mtok", "cache_read_per_mtok", "cache_write_per_mtok"}
)
ONBOARDING_KEY = "ai_connection_id"
_ONBOARDING_FIELDS = {"api_key", "base_url", "workspace_id", "model", *_PRICE_FIELDS}


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


def _server(provider: str, base_url: str | None) -> tuple[str, str]:
    return provider, (base_url or "") if provider in BASE_URL_PROVIDERS else ""


def _fresh(api_key: str | None) -> bool:
    return api_key is not None and MASK not in api_key


def _optional(value: str | None) -> str | None:
    return (value or "").strip() or None


def _sent_rates(data: AiConnectionCreate | AiConnectionUpdate) -> Rates | None:
    """The price sent with a model, an input and an output rate or none."""
    if data.input_per_mtok is None or data.output_per_mtok is None:
        return None
    return Rates(
        data.input_per_mtok,
        data.output_per_mtok,
        data.cache_read_per_mtok,
        data.cache_write_per_mtok,
    )


async def _model_rates(provider: str, model: str, base_url: str) -> Rates | None:
    """A model's price from the curated catalog, then the live catalog."""
    return curated_rates(model) or await run_in_threadpool(
        prices.lookup, provider, model, base_url=base_url
    )


async def _price(
    row: AiConnection,
    data: AiConnectionCreate | AiConnectionUpdate,
    provider: str,
    model: str,
    base_url: str,
    *,
    fresh: bool,
) -> None:
    """Store the row's price: the user's own when set, else the listed one."""
    sent = _sent_rates(data)
    if data.custom_price:
        if sent is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_PRICE)
        rates.store(row, sent)
        row.custom_price = True
        return
    cleared = sent is None and bool(_PRICE_FIELDS & data.model_fields_set)
    dropped = data.custom_price is False and row.custom_price
    if sent is not None:
        rates.store(row, sent)
    elif fresh or cleared or dropped:
        rates.store(row, await _model_rates(provider, model, base_url))
    if sent is not None or fresh or cleared or data.custom_price is False:
        row.custom_price = False


def call_cursor(before: str | None) -> tuple[datetime, uuid.UUID] | None:
    """The `at` and `id` of the last row a page of calls ended on."""
    if not before:
        return None
    at_text, _, id_text = before.rpartition(",")
    try:
        at = datetime.fromisoformat(at_text)
        row_id = uuid.UUID(id_text)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, _BAD_CURSOR
        ) from None
    return (at if at.tzinfo else at.replace(tzinfo=UTC)), row_id


def _unusable(row: AiConnection, key: str) -> str | None:
    """Why a saved provider cannot answer, or None."""
    if row.provider in BASE_URL_PROVIDERS and not row.base_url:
        return f"{row.name} has no server URL. Edit the provider and enter it."
    if not key and row.provider not in KEY_OPTIONAL_PROVIDERS:
        return f"{row.name} has no API key. Edit the provider and enter it."
    if not row.model:
        return f"{row.name} has no model. Edit the provider and choose one."
    return None


def _read(row: AiConnection, *, in_use: bool, full: bool) -> AiConnectionRead:
    key = try_decrypt(row.api_key_encrypted)
    return AiConnectionRead(
        id=row.id,
        name=row.name,
        provider=row.provider,
        model=row.model,
        input_per_mtok=row.input_per_mtok,
        output_per_mtok=row.output_per_mtok,
        cache_read_per_mtok=row.cache_read_per_mtok,
        cache_write_per_mtok=row.cache_write_per_mtok,
        custom_price=row.custom_price,
        base_url=row.base_url if full else None,
        workspace_id=row.workspace_id if full else None,
        key_masked=mask_tail(key) if key else None,
        in_use=in_use,
        last_test_at=row.last_test_at,
        last_test_ok=row.last_test_ok,
        last_test_message=row.last_test_message,
    )


def _draft_key(
    api_key: str | None, row: AiConnection | None, provider: str, base_url: str
) -> str:
    """A typed key, or the stored one while the provider and server are unchanged."""
    if api_key and _fresh(api_key):
        return api_key.strip()
    if row is not None and _server(provider, base_url) == _server(
        row.provider, row.base_url
    ):
        return try_decrypt(row.api_key_encrypted) or ""
    return ""


class AiSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _settings(self) -> InstanceSettings:
        return await InstanceSettingsService(self.session).get_or_create()

    async def _in_use(
        self, settings: InstanceSettings | None = None
    ) -> tuple[InstanceSettings, AiConnection | None]:
        settings = settings or await self._settings()
        if settings.ai_connection_id is None:
            return settings, None
        return settings, await self.session.get(AiConnection, settings.ai_connection_id)

    async def _connection(self, connection_id: uuid.UUID) -> AiConnection:
        row = await self.session.get(AiConnection, connection_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
        return row

    @staticmethod
    def _provider(value: str | None) -> str:
        provider = (value or "").strip()
        if not provider:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_PROVIDER)
        if provider not in _VALID_PROVIDERS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Unknown provider '{provider}'."
            )
        return provider

    async def _commit(self, name: str, *, flush: bool = False) -> None:
        try:
            await (self.session.flush() if flush else self.session.commit())
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Provider not saved. A provider named {name} exists.",
            ) from None

    async def _name(
        self,
        requested: str | None,
        provider: str,
        base_url: str,
        *,
        exclude: uuid.UUID | None = None,
    ) -> str:
        query = select(AiConnection.name)
        if exclude is not None:
            query = query.where(AiConnection.id != exclude)
        taken = {n.lower() for n in (await self.session.execute(query)).scalars()}
        name = (requested or "").strip()
        if name:
            if name.lower() in taken:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Provider not saved. A provider named {name} exists.",
                )
            return name
        base = connection_name(provider, base_url)
        candidate, n = base, 2
        while candidate.lower() in taken:
            suffix = f" {n}"
            candidate = f"{base[: MAX_CONNECTION_NAME - len(suffix)]}{suffix}"
            n += 1
        return candidate

    # ---------- status ----------

    async def status(self, *, full: bool = False) -> AiStatus:
        settings, row = await self._in_use()
        key = (try_decrypt(row.api_key_encrypted) or "") if row else ""
        return AiStatus(
            enabled=settings.ai_enabled,
            configured=row is not None and _unusable(row, key) is None,
            connection_id=row.id if row else None,
            provider=row.provider if row else None,
            model=row.model if row else None,
            workspace_id=(row.workspace_id or "") if row and full else None,
            base_url=(row.base_url or "") if row and full else None,
            key_masked=mask_tail(key) if key else None,
            features=feature_switches(settings.ai_features),
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
                    func.coalesce(func.sum(AiCall.cache_read_tokens), 0),
                    func.coalesce(func.sum(AiCall.cache_write_tokens), 0),
                    func.sum(AiCall.cost_usd),
                    func.count(AiCall.id).filter(
                        AiCall.cost_usd.is_(None), AiCall.cached.is_(False)
                    ),
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
                cache_read_tokens=int(reads),
                cache_write_tokens=int(writes),
                cost_usd=round(float(cost), 6) if cost is not None else None,
                unpriced=int(unpriced),
                last_at=last,
            )
            for (
                feature,
                calls,
                cached,
                failed,
                tokens_in,
                tokens_out,
                reads,
                writes,
                cost,
                unpriced,
                last,
                _,
            ) in rows
        ]
        by_feature.sort(key=lambda f: (-(f.cost_usd or 0), -f.calls))
        costs = [f.cost_usd for f in by_feature if f.cost_usd is not None]
        return AiUsageRead(
            calls=sum(f.calls - f.cached for f in by_feature),
            failed=sum(f.failed for f in by_feature),
            cost_usd=round(sum(costs), 6) if costs else None,
            unpriced=sum(f.unpriced for f in by_feature),
            since=min((r[-1] for r in rows if r[-1] is not None), default=None),
            by_feature=by_feature,
        )

    async def calls(
        self, limit: int, before: tuple[datetime, uuid.UUID] | None = None
    ) -> AiCallPage:
        query = select(AiCall).order_by(AiCall.at.desc(), AiCall.id.desc())
        if before is not None:
            at, row_id = before
            query = query.where(
                or_(AiCall.at < at, and_(AiCall.at == at, AiCall.id < row_id))
            )
        rows = list((await self.session.execute(query.limit(limit + 1))).scalars())
        return AiCallPage(
            items=[
                AiCallRead.model_validate(r, from_attributes=True) for r in rows[:limit]
            ],
            has_more=len(rows) > limit,
        )

    # ---------- providers ----------

    async def connections(self, *, full: bool = False) -> list[AiConnectionRead]:
        settings = await self._settings()
        rows = (
            await self.session.execute(
                select(AiConnection).order_by(
                    AiConnection.created_at, AiConnection.name
                )
            )
        ).scalars()
        return [
            _read(r, in_use=r.id == settings.ai_connection_id, full=full) for r in rows
        ]

    async def _add(self, data: AiConnectionCreate) -> AiConnection:
        provider = self._provider(data.provider)
        base_url = (
            _clean_base_url(data.base_url or "")
            if provider in BASE_URL_PROVIDERS
            else ""
        )
        if provider in BASE_URL_PROVIDERS and not base_url:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_URL)
        key = (data.api_key or "").strip() if _fresh(data.api_key) else ""
        if not key and provider not in KEY_OPTIONAL_PROVIDERS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_KEY)
        model = model_for(provider, data.model)
        if not model:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_MODEL)
        row = AiConnection(
            name=await self._name(data.name, provider, base_url),
            provider=provider,
            api_key_encrypted=encrypt_secret(key) if key else None,
            base_url=base_url or None,
            model=model,
            workspace_id=(
                _optional(data.workspace_id)
                if provider in WORKSPACE_PROVIDERS
                else None
            ),
        )
        await _price(row, data, provider, model, base_url, fresh=True)
        self.session.add(row)
        await self._commit(row.name, flush=True)
        return row

    async def create_connection(self, data: AiConnectionCreate) -> AiConnectionRead:
        settings = await self._settings()
        row = await self._add(data)
        if data.use or settings.ai_connection_id is None:
            settings.ai_connection_id = row.id
            settings.updated_at = utc_now()
        await self._commit(row.name)
        return _read(row, in_use=settings.ai_connection_id == row.id, full=True)

    async def _change(self, row: AiConnection, data: AiConnectionUpdate) -> None:
        provider = (
            self._provider(data.provider) if data.provider is not None else row.provider
        )
        if provider in BASE_URL_PROVIDERS:
            base_url = (
                _clean_base_url(data.base_url)
                if data.base_url is not None
                else (row.base_url or "")
            )
            if not base_url:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_URL)
        else:
            base_url = ""
        moved = _server(provider, base_url) != _server(row.provider, row.base_url)
        stored = try_decrypt(row.api_key_encrypted) or ""
        if _fresh(data.api_key):
            key = (data.api_key or "").strip()
        else:
            key = "" if moved else stored
        if not key and provider not in KEY_OPTIONAL_PROVIDERS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_KEY)
        switched = provider != row.provider
        requested = (
            data.model if data.model is not None else (None if switched else row.model)
        )
        model = model_for(provider, requested)
        if not model:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _NO_MODEL)
        if provider not in WORKSPACE_PROVIDERS:
            workspace = None
        elif data.workspace_id is not None:
            workspace = _optional(data.workspace_id)
        else:
            workspace = row.workspace_id
        if data.name is not None:
            row.name = await self._name(data.name, provider, base_url, exclude=row.id)
        if key != stored:
            row.api_key_encrypted = encrypt_secret(key) if key else None
        reconfigured = model != row.model or workspace != row.workspace_id
        if moved or key != stored or reconfigured:
            row.last_test_at = None
            row.last_test_ok = None
            row.last_test_message = None
        await _price(
            row, data, provider, model, base_url, fresh=moved or model != row.model
        )
        row.provider = provider
        row.base_url = base_url or None
        row.model = model
        row.workspace_id = workspace
        row.updated_at = utc_now()

    async def update_connection(
        self, connection_id: uuid.UUID, data: AiConnectionUpdate
    ) -> AiConnectionRead:
        settings = await self._settings()
        row = await self._connection(connection_id)
        await self._change(row, data)
        await self._commit(row.name)
        return _read(row, in_use=settings.ai_connection_id == row.id, full=True)

    async def delete_connection(self, connection_id: uuid.UUID) -> None:
        row = await self._connection(connection_id)
        settings = await self._settings()
        if settings.ai_connection_id == row.id:
            settings.ai_connection_id = None
            settings.updated_at = utc_now()
            await self.session.flush()
        await self.session.delete(row)
        await self.session.commit()

    async def _reprice(self, row: AiConnection) -> None:
        """Store today's price for the row's model."""
        await self.session.commit()
        rates.apply(row, await run_in_threadpool(rates.lookup, row))

    async def use_connection(self, connection_id: uuid.UUID) -> AiConnectionRead:
        row = await self._connection(connection_id)
        reason = _unusable(row, try_decrypt(row.api_key_encrypted) or "")
        if reason:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
        settings = await self._settings()
        if settings.ai_connection_id != row.id:
            settings.ai_connection_id = row.id
            settings.updated_at = utc_now()
            await self.session.commit()
        return _read(row, in_use=True, full=True)

    async def test_connection(
        self, connection_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> AiTestResult:
        row = await self._connection(connection_id)
        cfg = connection_config(row, timeout=_TEST_TIMEOUT)
        reason = _unusable(row, cfg.api_key)
        await self.session.commit()
        result = (
            AiTestResult(success=False, message=reason)
            if reason
            else await self._ping(cfg, row.name, user_id)
        )
        if result.success:
            await self._reprice(row)
        row.last_test_at = utc_now()
        row.last_test_ok = result.success
        row.last_test_message = result.message[:MAX_TEST_MESSAGE]
        await self.session.commit()
        return result

    async def models(self, data: AiModelsRequest) -> AiModelList:
        row = await self._connection(data.connection_id) if data.connection_id else None
        value = data.provider or (row.provider if row else None)
        if not value:
            return AiModelList(error=_NO_PROVIDER)
        provider = self._provider(value)
        base_url = ""
        if provider in BASE_URL_PROVIDERS:
            requested = (
                data.base_url
                if data.base_url is not None
                else (row.base_url if row else "")
            )
            try:
                base_url = _clean_base_url(requested or "")
            except HTTPException as exc:
                return AiModelList(error=str(exc.detail))
            if not base_url:
                return AiModelList(error=_NO_URL)
        key = _draft_key(data.api_key, row, provider, base_url)
        if not key and provider not in KEY_OPTIONAL_PROVIDERS:
            return AiModelList(error=_NO_KEY)
        workspace = ""
        if provider in WORKSPACE_PROVIDERS:
            workspace = (
                data.workspace_id
                if data.workspace_id is not None
                else (row.workspace_id if row else "")
            ) or ""
        cfg = AIConfig(
            provider=provider,
            api_key=key,
            model="",
            features={},
            workspace=workspace.strip(),
            timeout=MODEL_LIST_TIMEOUT,
            base_url=base_url,
        )
        await self.session.commit()
        return await run_in_threadpool(list_models, cfg)

    # ---------- settings ----------

    async def update(self, data: AiSettingsUpdate) -> AiStatus:
        settings, row = await self._in_use()
        if data.features is not None:
            features = feature_switches(settings.ai_features)
            features.update(
                {
                    k: bool(v)
                    for k, v in data.features.items()
                    if k in DEFAULT_AI_FEATURES
                }
            )
            settings.ai_features = features
        if data.enabled is not None:
            if data.enabled:
                if row is None:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "Choose a provider before turning AI on.",
                    )
                reason = _unusable(row, try_decrypt(row.api_key_encrypted) or "")
                if reason:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
            settings.ai_enabled = data.enabled
        settings.updated_at = utc_now()
        await self.session.commit()
        return await self.status(full=True)

    # ---------- onboarding ----------

    async def _onboarded(
        self,
    ) -> tuple[InstanceSettings, AiConnection | None]:
        settings = await self._settings()
        raw = (settings.onboarding_state or {}).get(ONBOARDING_KEY)
        try:
            connection_id = uuid.UUID(str(raw)) if raw else None
        except ValueError:
            connection_id = None
        if connection_id is None:
            return settings, None
        return settings, await self.session.get(AiConnection, connection_id)

    @staticmethod
    def _onboarding_read(
        settings: InstanceSettings, row: AiConnection | None
    ) -> AiOnboardingRead:
        return AiOnboardingRead(
            enabled=settings.ai_enabled,
            connection=(
                _read(row, in_use=settings.ai_connection_id == row.id, full=True)
                if row
                else None
            ),
            features=feature_switches(settings.ai_features),
        )

    async def onboarding(self) -> AiOnboardingRead:
        return self._onboarding_read(*await self._onboarded())

    async def onboard(self, data: AiOnboarding) -> AiOnboardingRead:
        """Save the setup step's provider, put it in use and store the switches."""
        settings, row = await self._onboarded()
        if data.features is not None:
            features = feature_switches(settings.ai_features)
            features.update(
                {
                    k: bool(v)
                    for k, v in data.features.items()
                    if k in DEFAULT_AI_FEATURES
                }
            )
            settings.ai_features = features
        settings.updated_at = utc_now()
        if not data.enabled:
            settings.ai_enabled = False
            await self.session.commit()
            return self._onboarding_read(settings, row)
        fields = data.model_dump(include=_ONBOARDING_FIELDS, exclude_unset=True)
        if row is None:
            row = await self._add(
                AiConnectionCreate(**fields, provider=data.provider or "")
            )
            settings.onboarding_state = {
                **(settings.onboarding_state or {}),
                ONBOARDING_KEY: str(row.id),
            }
        else:
            await self._change(
                row, AiConnectionUpdate(**fields, provider=data.provider)
            )
        settings.ai_connection_id = row.id
        settings.ai_enabled = True
        await self._commit(row.name)
        return self._onboarding_read(settings, row)

    # ---------- tests ----------

    async def test(
        self, data: AiTestRequest, user_id: uuid.UUID | None = None
    ) -> AiTestResult:
        row = await self._connection(data.connection_id) if data.connection_id else None
        provider = self._provider(data.provider or (row.provider if row else None))
        base_url = ""
        if provider in BASE_URL_PROVIDERS:
            base_url = _clean_base_url(
                data.base_url
                if data.base_url is not None
                else ((row.base_url or "") if row else "")
            )
        same = row is not None and _server(provider, base_url) == _server(
            row.provider, row.base_url
        )
        key = _draft_key(data.api_key, row, provider, base_url)
        if not key and provider not in KEY_OPTIONAL_PROVIDERS:
            return AiTestResult(
                success=False,
                message="No API key is configured." if same else _NO_KEY,
            )
        if provider in BASE_URL_PROVIDERS and not base_url:
            return AiTestResult(success=False, message="No server URL is configured.")
        stored_model = (
            row.model if row is not None and row.provider == provider else None
        )
        model = model_for(provider, data.model or stored_model)
        if not model:
            return AiTestResult(success=False, message="No model is configured.")
        workspace = ""
        if provider in WORKSPACE_PROVIDERS:
            workspace = (
                data.workspace_id
                if data.workspace_id is not None
                else ((row.workspace_id or "") if row else "")
            )
        priced = row if same and row is not None and model == row.model else None
        cfg = AIConfig(
            provider=provider,
            api_key=key,
            model=model,
            features=dict.fromkeys(DEFAULT_AI_FEATURES, True),
            enabled=True,
            workspace=workspace.strip(),
            timeout=_TEST_TIMEOUT,
            base_url=base_url,
            input_per_mtok=priced.input_per_mtok if priced else None,
            output_per_mtok=priced.output_per_mtok if priced else None,
            cache_read_per_mtok=priced.cache_read_per_mtok if priced else None,
            cache_write_per_mtok=priced.cache_write_per_mtok if priced else None,
            custom_price=priced.custom_price if priced else False,
        )
        label = row.name if same and row else PROVIDER_LABELS[provider]
        await self.session.commit()
        return await self._ping(cfg, label, user_id)

    async def _ping(
        self, cfg: AIConfig, label: str, user_id: uuid.UUID | None
    ) -> AiTestResult:
        started = time.monotonic()
        try:
            with ledger.source("user", user_id, user_id):
                result = await run_in_threadpool(
                    complete,
                    cfg,
                    system="Answer in one word.",
                    prompt=_TEST_PROMPT,
                    task=AITask.CONNECTION_TEST.value,
                )
        except AIError as exc:
            return AiTestResult(
                success=False, message=scrub_error(str(exc), cfg), model=cfg.model
            )
        except Exception as exc:
            return AiTestResult(
                success=False,
                message=scrub_error(f"{type(exc).__name__}: {exc}", cfg),
                model=cfg.model,
            )
        elapsed = int((time.monotonic() - started) * 1000)
        return AiTestResult(
            success=True,
            message=f"{label} answered in {elapsed} ms.",
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
                    "workspace": key in WORKSPACE_PROVIDERS,
                    "default_model": DEFAULT_MODEL.get(key, ""),
                    "models": [
                        {
                            "id": m.id,
                            "label": m.label,
                            "note": m.note,
                            "input_per_mtok": m.input_per_mtok,
                            "output_per_mtok": m.output_per_mtok,
                            "cache_read_per_mtok": m.cache_read_per_mtok,
                            "cache_write_per_mtok": m.cache_write_per_mtok,
                            "context": m.context,
                            "recommended": m.recommended,
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
