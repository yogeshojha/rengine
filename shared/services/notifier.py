from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.parse import quote

import apprise
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.enums.notification import NotificationSeverity, NotificationType
from shared.http import get_sync_client
from shared.models.notification_channel import NotificationChannel
from shared.utils.crypto import try_decrypt

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


def build_apprise_url(provider: str, config: dict) -> str | None:
    config = config or {}
    if provider == "slack":
        m = re.search(
            r"hooks\.slack\.com/services/(.+)$", config.get("webhook_url", "")
        )
        return f"slack://{m.group(1)}" if m else None
    if provider == "discord":
        m = re.search(r"/webhooks/(\d+)/([\w-]+)", config.get("webhook_url", ""))
        return f"discord://{m.group(1)}/{m.group(2)}" if m else None
    if provider == "telegram":
        token, chat = config.get("bot_token"), config.get("chat_id")
        return f"tgram://{token}/{chat}" if token and chat else None
    if provider == "email":
        return _email_url(config)
    if provider == "custom":
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
    provider: str, config: dict, title: str, body: str, severity: str
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
            )
            return (True, "Sent.") if ok else (False, "Delivery failed.")
        return _send_direct(provider, config, title, body, severity)
    except Exception as exc:
        logger.warning("notifier send error (%s): %s", provider, exc)
        return False, str(exc)


def _send_direct(
    provider: str, config: dict, title: str, body: str, severity: str
) -> tuple[bool, str]:
    url = (config or {}).get("webhook_url")
    if not url:
        return False, "Missing webhook URL."
    if provider == "teams":
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
            }
        )
    return targets


def _fan_out(
    targets: list[dict],
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    body: str,
) -> None:
    for t in targets:
        if not wants(t["pref"], ntype, severity):
            continue
        ok, msg = send_one(t["provider"], t["config"], title, body, severity.value)
        if not ok:
            logger.warning("dispatch to channel '%s' failed: %s", t["name"], msg)


def dispatch_sync(
    session: Session,
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    body: str,
) -> None:
    rows = (
        session.execute(
            select(NotificationChannel).where(NotificationChannel.is_active.is_(True))
        )
        .scalars()
        .all()
    )
    targets = _channels_to_targets(list(rows))
    if targets:
        _fan_out(targets, ntype, severity, title, body)


async def dispatch_async(
    session: AsyncSession,
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    body: str,
) -> None:
    result = await session.execute(
        select(NotificationChannel).where(NotificationChannel.is_active.is_(True))
    )
    targets = _channels_to_targets(list(result.scalars().all()))
    if targets:
        await asyncio.to_thread(_fan_out, targets, ntype, severity, title, body)
