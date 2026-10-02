"""Channel settings, read from and written to the channel's config row."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from channels.models import BotInfo, ChannelConfig
from mcp.capabilities import DEFAULT_CEILING
from shared.definitions.channels import CHANNEL_PROVIDERS, DEFAULT_RATE_LIMIT
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now

_RATE = "rate_limit_per_minute"
_CEILING = "ceiling"
_BOT = "bot"
_STARTED = "started_at"


@dataclass
class ChannelSettings:
    enabled: bool = False
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT
    ceiling: dict[str, bool] = field(default_factory=dict)
    bot: BotInfo | None = None
    started_at: datetime | None = None

    def __post_init__(self) -> None:
        self.ceiling = {**DEFAULT_CEILING, **(self.ceiling or {})}


def read(row: ChannelConfig | None) -> ChannelSettings:
    if row is None:
        return ChannelSettings()
    blob = dict(row.settings or {})
    bot = blob.get(_BOT)
    return ChannelSettings(
        enabled=bool(row.enabled),
        rate_limit_per_minute=int(blob.get(_RATE, DEFAULT_RATE_LIMIT)),
        ceiling=blob.get(_CEILING) or {},
        bot=BotInfo(**bot) if isinstance(bot, dict) and bot.get("username") else None,
        started_at=row.started_at,
    )


def write(row: ChannelConfig, settings: ChannelSettings) -> None:
    row.enabled = settings.enabled
    row.started_at = settings.started_at
    row.settings = {
        _RATE: settings.rate_limit_per_minute,
        _CEILING: settings.ceiling,
        _BOT: settings.bot.model_dump() if settings.bot else None,
    }
    row.updated_at = utc_now()


async def bot_token(session, channel: str) -> str | None:
    """The channel's API key."""
    provider = CHANNEL_PROVIDERS[channel]
    return await APIKeyService(session).get_key_for_provider(provider)


def mask_secret(secret: str | None) -> str | None:
    """Mask the token after the bot id."""
    if not secret:
        return None
    head, sep, _ = secret.partition(":")
    return f"{head}{sep}{MASK}" if sep else MASK


def redact(text: str, secret: str | None) -> str:
    """Replace the bot token in text with the mask."""
    if not secret:
        return text
    return text.replace(secret, MASK)
