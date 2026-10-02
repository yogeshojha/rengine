"""Telegram Bot API client."""

from __future__ import annotations

from typing import Any

import httpx

from channels.base import DriverError
from channels.models import BotInfo
from channels.settings import redact
from shared.http import get_async_client

API_BASE = "https://api.telegram.org"
LONG_POLL_SECONDS = 50
SAFE_LIMIT = 4000
MAX_MENU_COMMANDS = 100
_UNAUTHORIZED = 401


class TelegramError(DriverError):
    def __init__(
        self,
        description: str,
        *,
        code: int | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(description)
        self.code = code
        self.retry_after = retry_after

    @property
    def unauthorized(self) -> bool:
        return self.code == _UNAUTHORIZED


def bot_info(me: dict) -> BotInfo:
    return BotInfo(
        id=str(me.get("id", "")),
        username=str(me.get("username") or ""),
        name=str(me.get("first_name") or ""),
    )


class TelegramApi:
    def __init__(self, token: str):
        self._token = token.strip()
        self._client = get_async_client(
            timeout=httpx.Timeout(20.0, read=LONG_POLL_SECONDS + 20),
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def call(self, method: str, **params: Any) -> Any:
        url = f"{API_BASE}/bot{self._token}/{method}"
        body = {k: v for k, v in params.items() if v is not None}
        try:
            response = await self._client.post(url, json=body)
        except httpx.HTTPError as exc:
            raise TelegramError(type(exc).__name__) from None
        try:
            payload = response.json()
        except ValueError:
            msg = f"HTTP {response.status_code}"
            raise TelegramError(msg, code=response.status_code) from None
        if not isinstance(payload, dict) or not payload.get("ok"):
            description = redact(
                str(payload.get("description") or f"HTTP {response.status_code}"),
                self._token,
            )
            parameters = payload.get("parameters") or {}
            raise TelegramError(
                description,
                code=int(payload.get("error_code") or response.status_code),
                retry_after=parameters.get("retry_after"),
            )
        return payload.get("result")

    # ---------- identity ----------

    async def get_me(self) -> BotInfo:
        return bot_info(await self.call("getMe"))

    async def delete_webhook(self) -> None:
        await self.call("deleteWebhook", drop_pending_updates=False)

    async def set_my_commands(self, commands: list[tuple[str, str]]) -> None:
        menu = [
            {"command": name, "description": description[:256]}
            for name, description in commands[:MAX_MENU_COMMANDS]
        ]
        await self.call("setMyCommands", commands=menu)

    # ---------- updates ----------

    async def get_updates(
        self, offset: int, poll_seconds: int = LONG_POLL_SECONDS
    ) -> list[dict]:
        result = await self.call(
            "getUpdates",
            offset=offset,
            timeout=poll_seconds,
            allowed_updates=["message"],
        )
        return result if isinstance(result, list) else []

    # ---------- messages ----------

    async def send_message(
        self, chat_id: str, text: str, entities: list[dict] | None = None
    ) -> dict:
        return await self.call(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            entities=entities or None,
            link_preview_options={"is_disabled": True},
        )

    async def delete_message(self, chat_id: str, message_id: str) -> None:
        await self.call("deleteMessage", chat_id=chat_id, message_id=int(message_id))
