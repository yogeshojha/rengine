import asyncio
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.mode_features import (
    VALID_MODES,
    capabilities_for,
    has_capability,
)
from shared.definitions.retention import (
    KEEP_FOREVER,
    SCAN_RETENTION_DAYS,
    SCREENSHOT_RETENTION_DAYS,
)
from shared.logging import get_logger
from shared.models.instance_settings import (
    SINGLETON_KEY,
    InstanceSettings,
    InstanceSettingsRead,
    InstanceSettingsUpdate,
)
from shared.services import scan_admission
from shared.services.celery_dispatch import dispatch_scan_admission
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


def _apply_limit(settings: InstanceSettings, value: int | None) -> bool:
    if value is None or value == settings.concurrent_scans:
        return False
    settings.concurrent_scans = value
    return True


async def _admit_on_change(changed: bool) -> None:
    if not changed:
        return
    try:
        await asyncio.to_thread(dispatch_scan_admission)
    except Exception:
        logger.warning("scan admission dispatch failed", exc_info=True)


def _check_window(label: str, days: int, allowed: tuple[int, ...]) -> None:
    if days not in allowed:
        choices = ", ".join(str(d) for d in allowed if d != KEEP_FOREVER)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} retention must be {choices} days, or {KEEP_FOREVER} to keep forever.",
        )


class InstanceSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self) -> InstanceSettings:
        result = await self.session.execute(
            select(InstanceSettings).where(
                InstanceSettings.singleton_key == SINGLETON_KEY
            )
        )
        settings = result.scalar_one_or_none()
        if settings is None:
            settings = InstanceSettings(singleton_key=SINGLETON_KEY)
            self.session.add(settings)
            try:
                await self.session.commit()
                await self.session.refresh(settings)
            except IntegrityError:
                await self.session.rollback()
                result = await self.session.execute(
                    select(InstanceSettings).where(
                        InstanceSettings.singleton_key == SINGLETON_KEY
                    )
                )
                settings = result.scalar_one()
        return settings

    async def has_capability(self, cap: str) -> bool:
        return has_capability((await self.get_or_create()).mode, cap)

    def to_read(self, settings: InstanceSettings) -> InstanceSettingsRead:
        return InstanceSettingsRead(
            id=settings.id,
            singleton_key=settings.singleton_key,
            instance_name=settings.instance_name,
            timezone=settings.timezone,
            mode=settings.mode,
            onboarding_completed=settings.onboarding_completed,
            onboarding_completed_at=settings.onboarding_completed_at,
            onboarding_completed_by=settings.onboarding_completed_by,
            onboarding_step=settings.onboarding_step,
            onboarding_state=settings.onboarding_state or {},
            scan_history_retention_days=settings.scan_history_retention_days,
            screenshot_retention_days=settings.screenshot_retention_days,
            cert_recheck_enabled=settings.cert_recheck_enabled,
            infostealer_lookups=settings.infostealer_lookups,
            concurrent_scans=settings.concurrent_scans,
            capabilities=capabilities_for(settings.mode),
            created_at=settings.created_at,
            updated_at=settings.updated_at,
        )

    async def update(self, data: InstanceSettingsUpdate) -> InstanceSettingsRead:
        settings = await self.get_or_create()

        if data.instance_name is not None:
            name = data.instance_name.strip()
            if not name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Instance name is required.",
                )
            settings.instance_name = name[:120]
        if data.timezone is not None:
            try:
                ZoneInfo(data.timezone)
            except Exception as exc:
                msg = f"Invalid timezone '{data.timezone}'."
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=msg
                ) from exc
            settings.timezone = data.timezone
        if data.mode is not None:
            if data.mode not in VALID_MODES:
                msg = f"Invalid mode '{data.mode}'. Must be one of {', '.join(sorted(VALID_MODES))}."
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
            settings.mode = data.mode
        if data.scan_history_retention_days is not None:
            _check_window(
                "Scan history", data.scan_history_retention_days, SCAN_RETENTION_DAYS
            )
            settings.scan_history_retention_days = data.scan_history_retention_days
        if data.screenshot_retention_days is not None:
            _check_window(
                "Screenshot",
                data.screenshot_retention_days,
                SCREENSHOT_RETENTION_DAYS,
            )
            settings.screenshot_retention_days = data.screenshot_retention_days
        if data.cert_recheck_enabled is not None:
            settings.cert_recheck_enabled = data.cert_recheck_enabled
        if data.infostealer_lookups is not None:
            settings.infostealer_lookups = data.infostealer_lookups
        limit_changed = _apply_limit(settings, data.concurrent_scans)
        settings.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(settings)
        await _admit_on_change(limit_changed)
        return await self.with_limit(self.to_read(settings))

    async def with_limit(self, read: InstanceSettingsRead) -> InstanceSettingsRead:
        try:
            read.concurrent_scans_auto = await asyncio.to_thread(
                scan_admission.automatic_limit
            )
        except Exception:
            logger.warning("automatic scan limit unreadable", exc_info=True)
        return read
