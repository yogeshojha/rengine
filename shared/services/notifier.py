from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.parse import quote

import apprise
from sqlalchemy import Engine, bindparam, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session

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

_RANK = {"success": 0, "info": 0, "warning": 1, "error": 2}
_NOTIFY_TYPE = {
    "success": apprise.NotifyType.SUCCESS,
    "info": apprise.NotifyType.INFO,
    "warning": apprise.NotifyType.WARNING,
    "error": apprise.NotifyType.FAILURE,
}
_TEAMS_COLOR = {
    "error": "E11900",
    "warning": "E8A33D",
    "success": "2DA44E",
    "info": "5E5E5E",
}


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
        return f"slack://{m.group(1)}" if m else None
    if provider == NotificationProvider.DISCORD.value:
        m = re.search(r"/webhooks/(\d+)/([\w-]+)", config.get("webhook_url", ""))
        return f"discord://{m.group(1)}/{m.group(2)}" if m else None
    if provider == NotificationProvider.TELEGRAM.value:
        token, chat = config.get("bot_token"), config.get("chat_id")
        return f"tgram://{token}/{chat}" if token and chat else None
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


def send_one(
    provider: str,
    config: dict,
    title: str,
    body: str,
    severity: str,
    attach: str | None = None,
) -> tuple[bool, str]:
    try:
        url = build_apprise_url(provider, config)
        if url is not None:
            client = apprise.Apprise()
            if not client.add(url):
                return False, "Invalid channel configuration."
            ok = client.notify(
                title=title,
                body=body,
                notify_type=_NOTIFY_TYPE.get(severity, apprise.NotifyType.INFO),
                attach=attach or None,
            )
            return (True, "Sent.") if ok else (False, "Delivery failed.")
        if provider in DIRECT_POST_PROVIDERS:
            return _send_direct(provider, config, title, body, severity)
        return False, "Invalid channel configuration."
    except Exception as exc:
        logger.warning("notifier send error (%s): %s", provider, exc)
        return False, f"Delivery failed: {type(exc).__name__}."


def _send_direct(
    provider: str, config: dict, title: str, body: str, severity: str
) -> tuple[bool, str]:
    url = (config or {}).get("webhook_url")
    if not url:
        return False, "Missing webhook URL."
    if provider == NotificationProvider.TEAMS.value:
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": _TEAMS_COLOR.get(severity, "5E5E5E"),
            "summary": title,
            "sections": [{"activityTitle": title, "text": body}],
        }
    else:
        payload = {
            "source": "reNgine",
            "title": title,
            "message": body,
            "severity": severity,
        }
    with get_sync_client(follow_redirects=False) as client:
        resp = client.post(url, json=payload)
    if resp.is_success:
        return True, "Sent."
    return False, f"HTTP {resp.status_code}."


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
    targets: list[dict],
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    body: str,
    *,
    explicit: bool = False,
    attach: str | None = None,
) -> list[tuple]:
    sent = []
    for t in targets:
        if not explicit and not wants(t["pref"], ntype, severity):
            continue
        ok, msg = send_one(
            t["provider"], t["config"], title, body, severity.value, attach=attach
        )
        if not ok:
            logger.warning("dispatch to channel '%s' failed: %s", t["name"], msg)
        sent.append((t["id"], ok, msg))
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
) -> None:
    """Named channels receive it regardless of their event preferences."""
    from shared.services.api_key.sync_api_key import SyncAPIKeyService  # noqa: PLC0415

    rows = session.execute(_channel_query(channel_ids)).scalars().all()
    targets = _channels_to_targets(list(rows))
    _shared_bot_targets(targets, SyncAPIKeyService(session).get_key_for_provider)
    if targets:
        sent = _fan_out(
            targets,
            ntype,
            severity,
            title,
            body,
            explicit=bool(channel_ids),
            attach=attach,
        )
        _record_sync(session, sent)


async def dispatch_async(
    session: AsyncSession,
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    body: str,
    *,
    channel_ids=None,
    attach: str | None = None,
) -> None:
    from shared.services.api_key.async_api_key import APIKeyService  # noqa: PLC0415

    result = await session.execute(_channel_query(channel_ids))
    targets = _channels_to_targets(list(result.scalars().all()))
    if targets:
        token = await APIKeyService(session).get_key_for_provider(APIProvider.TELEGRAM)
        _shared_bot_targets(targets, lambda _provider: token)
        sent = await asyncio.to_thread(
            _fan_out,
            targets,
            ntype,
            severity,
            title,
            body,
            explicit=bool(channel_ids),
            attach=attach,
        )
        await _record_async(session, sent)
