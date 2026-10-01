from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import apprise
from sqlalchemy import Engine, bindparam, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session

from shared.config import base_settings
from shared.enums.api_key import APIProvider
from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.notification_channel import (
    DIRECT_POST_PROVIDERS,
    NotificationProvider,
)
from shared.http import get_sync_client
from shared.models.notification_channel import NotificationChannel
from shared.utils.crypto import try_decrypt
from shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)

_RANK = {"info": 0, "warning": 1, "error": 2}
_NOTIFY_TYPE = {
    "info": apprise.NotifyType.INFO,
    "warning": apprise.NotifyType.WARNING,
    "error": apprise.NotifyType.FAILURE,
}
_CARD_COLOR = {"error": "Attention", "warning": "Warning"}
_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
NOT_SENT = "Not sent"
INVALID_CONFIG = "invalid configuration"


@dataclass(frozen=True)
class Outbound:
    """One message as a channel receives it."""

    title: str
    body: str
    severity: str
    type: str = ""
    url: str | None = None
    scan_id: str | None = None
    target_id: str | None = None
    attach: str | None = None
    sent_at: str = field(default_factory=lambda: utc_now().isoformat())

    @classmethod
    def build(
        cls,
        ntype: NotificationType | str,
        severity: NotificationSeverity | str,
        title: str,
        body: str,
        metadata: dict | None = None,
        attach: str | None = None,
    ) -> Outbound:
        meta = metadata or {}
        return cls(
            title=title,
            body=body,
            severity=getattr(severity, "value", severity),
            type=getattr(ntype, "value", ntype),
            url=absolute_url(meta.get("url")),
            scan_id=meta.get("scan_id"),
            target_id=meta.get("target_id"),
            attach=attach,
        )

    @property
    def lines(self) -> list[str]:
        return [line for line in self.body.split("\n") if line.strip()]

    def text(self, *, title: str | None = None) -> str:
        """Title, one fact per line, the link last."""
        parts = [title if title is not None else self.title, *self.lines]
        if self.url:
            parts.append(self.url)
        return "\n".join(p for p in parts if p)


def absolute_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("/"):
        return f"{base_settings().ui_base_url}{url}"
    return url


def severity_passes(min_severity: str, severity: str) -> bool:
    return _RANK.get(severity, 0) >= _RANK.get(min_severity, 0)


def wants(pref: dict, ntype: NotificationType, severity: NotificationSeverity) -> bool:
    types = (pref or {}).get("types") or []
    if ntype.value not in types:
        return False
    return severity_passes((pref or {}).get("min_severity", "info"), severity.value)


SHARED_BOT_PROVIDER = NotificationProvider.TELEGRAM.value


def with_shared_bot(provider: str, config: dict, lookup) -> dict:
    """A Telegram channel with no token of its own sends as the Telegram API key's bot."""
    if provider != SHARED_BOT_PROVIDER or (config or {}).get("bot_token"):
        return config or {}
    token = lookup(APIProvider.TELEGRAM)
    return {**(config or {}), "bot_token": token} if token else (config or {})


def _shared_bot_targets(targets: list[dict], lookup) -> None:
    for target in targets:
        target["config"] = with_shared_bot(target["provider"], target["config"], lookup)


def build_apprise_url(provider: str, config: dict) -> str | None:
    config = config or {}
    if provider == NotificationProvider.SLACK.value:
        m = re.search(
            r"hooks\.slack\.com/services/(.+)$", config.get("webhook_url", "")
        )
        return f"slack://{m.group(1)}?footer=no&image=no&format=text" if m else None
    if provider == NotificationProvider.DISCORD.value:
        m = re.search(r"/webhooks/(\d+)/([\w-]+)", config.get("webhook_url", ""))
        return (
            f"discord://{m.group(1)}/{m.group(2)}?avatar=no&format=text" if m else None
        )
    if provider == NotificationProvider.EMAIL.value:
        return _email_url(config)
    if provider == NotificationProvider.CUSTOM.value:
        return config.get("apprise_url") or None
    return None


def _email_url(config: dict) -> str | None:
    host = config.get("smtp_host")
    user = config.get("username")
    pwd = config.get("password")
    to_email = config.get("to_email") or user
    from_email = config.get("from_email") or user
    if not (host and user and pwd and to_email):
        return None
    port = config.get("smtp_port") or 587
    scheme = "mailtos" if config.get("use_tls", True) else "mailto"
    return (
        f"{scheme}://{quote(str(user), safe='')}:{quote(str(pwd), safe='')}"
        f"@{host}:{port}/?from={quote(str(from_email), safe='')}"
        f"&to={quote(str(to_email), safe='')}"
    )


def send_one(provider: str, config: dict, message: Outbound) -> tuple[bool, str]:
    """Returns (sent, reason); the reason is empty when sent."""
    try:
        if provider in DIRECT_POST_PROVIDERS:
            return _send_direct(provider, config, message)
        url = build_apprise_url(provider, config)
        if url is None:
            return False, INVALID_CONFIG
        client = apprise.Apprise()
        if not client.add(url):
            return False, INVALID_CONFIG
        title, body = _apprise_text(provider, message)
        ok = client.notify(
            title=title,
            body=body,
            notify_type=_NOTIFY_TYPE.get(message.severity, apprise.NotifyType.INFO),
            attach=message.attach or None,
        )
        return (True, "") if ok else (False, "no response")
    except Exception as exc:
        logger.warning("notifier send error (%s): %s", provider, type(exc).__name__)
        return False, type(exc).__name__


def _apprise_text(provider: str, message: Outbound) -> tuple[str, str]:
    """Discord renders markdown in plain content; the rest take a title of their own."""
    if provider == NotificationProvider.DISCORD.value:
        return "", message.text(title=f"**{message.title}**")
    body = "\n".join([*message.lines, *([message.url] if message.url else [])])
    if not body:
        return "", message.title
    return message.title, body


def _send_direct(provider: str, config: dict, message: Outbound) -> tuple[bool, str]:
    if provider == NotificationProvider.TELEGRAM.value:
        return _send_telegram(config or {}, message)
    url = (config or {}).get("webhook_url")
    if not url:
        return False, INVALID_CONFIG
    payload = (
        _teams_card(message)
        if provider == NotificationProvider.TEAMS.value
        else _webhook_payload(message)
    )
    with get_sync_client(follow_redirects=False) as client:
        resp = client.post(url, json=payload)
    return (True, "") if resp.is_success else (False, f"HTTP {resp.status_code}")


def _webhook_payload(message: Outbound) -> dict:
    return {
        "source": "reNgine",
        "type": message.type,
        "severity": message.severity,
        "title": message.title,
        "message": message.body,
        "url": message.url,
        "scan_id": message.scan_id,
        "target_id": message.target_id,
        "sent_at": message.sent_at,
    }


def _teams_card(message: Outbound) -> dict:
    title: dict = {
        "type": "TextBlock",
        "text": message.title,
        "weight": "Bolder",
        "size": "Medium",
        "wrap": True,
    }
    if message.severity in _CARD_COLOR:
        title["color"] = _CARD_COLOR[message.severity]
    card: dict = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": [
            title,
            *(
                {"type": "TextBlock", "text": line, "wrap": True, "spacing": "None"}
                for line in message.lines
            ),
        ],
    }
    if message.url:
        card["actions"] = [
            {"type": "Action.OpenUrl", "title": "Open", "url": message.url}
        ]
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": card,
            }
        ],
    }


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _send_telegram(config: dict, message: Outbound) -> tuple[bool, str]:
    """Plain text with a bold entity for the title; nothing is parsed."""
    token, chat = config.get("bot_token"), config.get("chat_id")
    if not (token and chat):
        return False, INVALID_CONFIG
    text = message.text()
    payload = {
        "chat_id": chat,
        "text": text,
        "disable_web_page_preview": True,
        "entities": [
            {"type": "bold", "offset": 0, "length": _utf16_len(message.title)}
        ],
    }
    with get_sync_client(follow_redirects=False) as client:
        resp = client.post(
            _TELEGRAM_API.format(token=token, method="sendMessage"), json=payload
        )
        if not resp.is_success:
            return False, f"HTTP {resp.status_code}"
        if message.attach and Path(message.attach).is_file():
            with Path(message.attach).open("rb") as fh:
                photo = client.post(
                    _TELEGRAM_API.format(token=token, method="sendPhoto"),
                    data={"chat_id": chat},
                    files={"photo": (Path(message.attach).name, fh)},
                )
            if not photo.is_success:
                return False, f"HTTP {photo.status_code}"
    return True, ""


def _channels_to_targets(rows: list[NotificationChannel]) -> list[dict]:
    targets = []
    for row in rows:
        raw = try_decrypt(row.config_encrypted)
        if not raw:
            continue
        try:
            config = json.loads(raw)
        except (ValueError, TypeError):
            continue
        targets.append(
            {
                "provider": row.provider,
                "config": config,
                "pref": row.events,
                "name": row.name,
                "id": row.id,
            }
        )
    return targets


def _fan_out(
    targets: list[dict], message: Outbound, *, explicit: bool = False
) -> list[tuple]:
    ntype = NotificationType(message.type)
    severity = NotificationSeverity(message.severity)
    sent = []
    for t in targets:
        if not explicit and not wants(t["pref"], ntype, severity):
            continue
        ok, reason = send_one(t["provider"], t["config"], message)
        if not ok:
            logger.warning("dispatch to channel '%s' failed: %s", t["name"], reason)
        sent.append((t["id"], ok, reason))
    return sent


_CHANNELS = NotificationChannel.__table__
_RECORD_DELIVERY = (
    update(_CHANNELS)
    .where(_CHANNELS.c.id == bindparam("cid"))
    .values(
        last_sent_at=bindparam("at"),
        last_sent_ok=bindparam("ok"),
        last_sent_message=bindparam("msg"),
    )
)


def _delivery_rows(sent: list[tuple]) -> list[dict]:
    now = utc_now()
    return [
        {"cid": cid, "at": now, "ok": ok, "msg": (msg or "")[:500]}
        for cid, ok, msg in sent
    ]


def _record_sync(session: Session, sent: list[tuple]) -> None:
    """Writes on its own connection, outside the caller's transaction."""
    if not sent:
        return
    try:
        bind = session.get_bind()
        if isinstance(bind, Engine):
            with bind.begin() as conn:
                conn.execute(_RECORD_DELIVERY, _delivery_rows(sent))
        else:
            session.execute(_RECORD_DELIVERY, _delivery_rows(sent))
    except Exception:
        logger.warning("channel delivery status not recorded", exc_info=True)


async def _record_async(session: AsyncSession, sent: list[tuple]) -> None:
    if not sent:
        return
    try:
        bind = session.bind
        if isinstance(bind, AsyncEngine):
            async with bind.begin() as conn:
                await conn.execute(_RECORD_DELIVERY, _delivery_rows(sent))
        else:
            await session.execute(_RECORD_DELIVERY, _delivery_rows(sent))
    except Exception:
        logger.warning("channel delivery status not recorded", exc_info=True)


def _channel_query(channel_ids=None):
    stmt = select(NotificationChannel).where(NotificationChannel.is_active.is_(True))
    if channel_ids:
        stmt = stmt.where(NotificationChannel.id.in_(list(channel_ids)))
    return stmt


def dispatch_sync(
    session: Session,
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    body: str,
    *,
    channel_ids=None,
    attach: str | None = None,
    metadata: dict | None = None,
) -> list[tuple]:
    """Named channels receive it whatever their preferences. Returns (id, ok, reason) per channel."""
    from shared.services.api_key.sync_api_key import SyncAPIKeyService  # noqa: PLC0415

    rows = session.execute(_channel_query(channel_ids)).scalars().all()
    targets = _channels_to_targets(list(rows))
    _shared_bot_targets(targets, SyncAPIKeyService(session).get_key_for_provider)
    if not targets:
        return []
    message = Outbound.build(ntype, severity, title, body, metadata, attach)
    sent = _fan_out(targets, message, explicit=bool(channel_ids))
    _record_sync(session, sent)
    return sent


async def dispatch_async(
    session: AsyncSession,
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    body: str,
    *,
    channel_ids=None,
    attach: str | None = None,
    metadata: dict | None = None,
) -> None:
    from shared.services.api_key.async_api_key import APIKeyService  # noqa: PLC0415

    result = await session.execute(_channel_query(channel_ids))
    targets = _channels_to_targets(list(result.scalars().all()))
    if targets:
        token = await APIKeyService(session).get_key_for_provider(APIProvider.TELEGRAM)
        _shared_bot_targets(targets, lambda _provider: token)
        message = Outbound.build(ntype, severity, title, body, metadata, attach)
        sent = await asyncio.to_thread(
            _fan_out, targets, message, explicit=bool(channel_ids)
        )
        await _record_async(session, sent)
