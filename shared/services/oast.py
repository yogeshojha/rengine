"""The instance's out-of-band settings, resolved into what a scanner is handed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shared.definitions.oast import DEFAULT_WAIT_SECONDS, OastConfig, OastMode
from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.instance_settings import InstanceSettings, oast_reason

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)


def settings_row(session: Session | None) -> InstanceSettings | None:
    if session is None:
        return None
    return session.execute(InstanceSettings.singleton()).scalars().first()


def config(session: Session | None) -> OastConfig:
    """The effective configuration. Off whenever the mode cannot be used."""
    row = settings_row(session)
    reason = oast_reason(row)
    if row is None:
        return OastConfig(reason=reason)
    wait_seconds = row.oast_wait_seconds or DEFAULT_WAIT_SECONDS
    if reason is not None:
        return OastConfig(wait_seconds=wait_seconds, reason=reason)
    self_hosted = row.oast_mode == OastMode.SELF_HOSTED.value
    return OastConfig(
        mode=row.oast_mode,
        server=row.oast_host if self_hosted else None,
        token=_token(session) if self_hosted else None,
        wait_seconds=wait_seconds,
    )


def _token(session: Session) -> str | None:
    from shared.services.api_key.sync_api_key import SyncAPIKeyService  # noqa: PLC0415

    try:
        return SyncAPIKeyService(session).get_key_for_provider(APIProvider.INTERACTSH)
    except Exception:
        logger.warning("could not read the out-of-band token", exc_info=True)
        return None


__all__ = ["config", "settings_row"]
