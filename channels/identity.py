"""Capabilities and token identity of a paired chat."""

from __future__ import annotations

from channels.models import ChannelChat
from mcp.capabilities import ALWAYS_GRANTED, within_ceiling
from mcp.context import TokenIdentity
from shared.models.user import User


def effective_capabilities(
    chat: ChannelChat, user: User | None, ceiling: dict[str, bool]
) -> list[str]:
    granted = within_ceiling(list(chat.capabilities or []), ceiling)
    if user is None or not user.totp_enabled:
        return [c for c in granted if c in ALWAYS_GRANTED]
    return granted


def identity_for(
    chat: ChannelChat, user: User, ceiling: dict[str, bool]
) -> TokenIdentity:
    return TokenIdentity(
        id=chat.id,
        name=f"{chat.channel}:{chat.display or chat.external_id}",
        project_id=chat.project_id,
        capabilities=frozenset(effective_capabilities(chat, user, ceiling)),
        issued_by=user.id,
    )
