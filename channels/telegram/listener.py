"""Long-poll the Bot API and hand every private message to the dispatcher."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from channels import settings, status
from channels.base import Channel, ChatLocks, Inbound
from channels.dispatch import Dispatcher
from channels.models import BotInfo, ChannelConfig
from channels.render import Message
from channels.telegram.api import (
    LONG_POLL_SECONDS,
    SAFE_LIMIT,
    TelegramApi,
    TelegramError,
)
from channels.telegram.driver import menu
from shared.definitions.channels import DISPATCH_SLOTS, ChannelKind
from shared.logging import get_logger

logger = get_logger(__name__)

CONFIG_REFRESH_SECONDS = 5.0
MAX_BACKOFF_SECONDS = 120
UNAUTHORIZED_PAUSE_SECONDS = 60
PRIVATE = "private"


class TelegramChannel(Channel):
    kind = ChannelKind.TELEGRAM.value
    limit = SAFE_LIMIT

    def __init__(self, api: TelegramApi):
        self.api = api

    async def send(self, external_id: str, message: Message) -> str | None:
        sent = await self.api.send_message(external_id, message.text, message.entities)
        message_id = sent.get("message_id") if isinstance(sent, dict) else None
        return str(message_id) if message_id is not None else None

    async def delete(self, external_id: str, message_id: str) -> None:
        await self.api.delete_message(external_id, message_id)


def to_inbound(update: dict) -> Inbound | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    text = message.get("text")
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    if not isinstance(text, str) or not text.strip() or "id" not in chat:
        return None
    return Inbound(
        external_id=str(chat["id"]),
        username=sender.get("username") or None,
        first_name=sender.get("first_name") or None,
        text=text,
        message_id=str(message["message_id"]) if "message_id" in message else None,
        private=chat.get("type") == PRIVATE,
    )


class TelegramListener:
    kind = ChannelKind.TELEGRAM.value

    def __init__(self, sessions: Any, ui_base: str):
        self.sessions = sessions
        self.ui_base = ui_base
        self._token: str | None = None
        self._api: TelegramApi | None = None
        self._dispatcher: Dispatcher | None = None
        self._bot: BotInfo | None = None
        self._offset = 0
        self._last_error: str | None = None
        self._failures = 0
        self._tasks: set[asyncio.Task] = set()
        self._chats = ChatLocks()
        self._slots = asyncio.Semaphore(DISPATCH_SLOTS)

    # ---------- config ----------

    async def _config(self) -> tuple[settings.ChannelSettings, str | None]:
        async with self.sessions() as session:
            row = await session.get(ChannelConfig, self.kind)
            try:
                secret = await settings.bot_token(session, self.kind)
            except Exception as exc:
                self._note_error(type(exc).__name__)
                secret = None
            return settings.read(row), secret

    async def _connect(self, token: str) -> bool:
        await self._disconnect()
        api = TelegramApi(token)
        try:
            self._bot = await api.get_me()
            await api.delete_webhook()
            await api.set_my_commands(menu())
        except TelegramError as exc:
            await api.close()
            self._note_error(f"Telegram refused the bot token: {exc.description}")
            return False
        self._api = api
        self._token = token
        if self._dispatcher is None:
            self._dispatcher = Dispatcher(
                TelegramChannel(api), self.sessions, self.ui_base
            )
        else:
            self._dispatcher.channel = TelegramChannel(api)
        self._offset = await status.load_offset(self.kind, self._bot.id)
        self._failures = 0
        self._last_error = None
        logger.info("telegram listener connected", bot=self._bot.username)
        return True

    async def _disconnect(self) -> None:
        if self._api is not None:
            await self._api.close()
        self._api = None
        self._token = None

    async def _release(self) -> None:
        if self._dispatcher is not None:
            await self._dispatcher.close()
        self._dispatcher = None

    def _note_error(self, message: str) -> None:
        self._last_error = message[:300]
        logger.warning("telegram listener error", error=self._last_error)

    # ---------- status ----------

    async def _publish(self, enabled: bool) -> None:
        await status.publish(
            self.kind,
            {
                "running": enabled and self._api is not None,
                "last_error": self._last_error,
            },
        )

    # ---------- loop ----------

    async def run(self, stop: asyncio.Event) -> None:
        poll: asyncio.Task | None = None
        stopper = asyncio.create_task(stop.wait())
        try:
            while not stop.is_set():
                cfg, token = await self._config()
                if not cfg.enabled or not token:
                    if self._api is not None:
                        logger.info("telegram listener stopped by configuration")
                    await self._cancel(poll)
                    poll = None
                    await self._release()
                    await self._disconnect()
                    await self._publish(False)
                    await self._sleep(stop, CONFIG_REFRESH_SECONDS)
                    continue

                if token != self._token:
                    await self._cancel(poll)
                    poll = None
                    if not await self._connect(token):
                        await self._publish(False)
                        await self._sleep(stop, UNAUTHORIZED_PAUSE_SECONDS)
                        continue

                if poll is None:
                    poll = asyncio.create_task(self._poll_once())
                await self._publish(True)

                done, _ = await asyncio.wait(
                    {poll, stopper},
                    timeout=CONFIG_REFRESH_SECONDS,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if poll in done:
                    delay = poll.result()
                    poll = None
                    if delay:
                        await self._sleep(stop, delay)
        finally:
            await self._cancel(poll)
            stopper.cancel()
            await self._drain()
            await self._release()
            await self._disconnect()

    async def _poll_once(self) -> float:
        """Run one long poll and return the pause before the next."""
        api, bot = self._api, self._bot
        if api is None or bot is None:
            return CONFIG_REFRESH_SECONDS
        try:
            updates = await api.get_updates(self._offset, LONG_POLL_SECONDS)
        except TelegramError as exc:
            self._failures += 1
            self._note_error(exc.description)
            if exc.unauthorized:
                return UNAUTHORIZED_PAUSE_SECONDS
            if exc.retry_after:
                return float(exc.retry_after)
            return float(min(MAX_BACKOFF_SECONDS, 2**self._failures))
        except Exception as exc:
            self._failures += 1
            self._note_error(type(exc).__name__)
            return float(min(MAX_BACKOFF_SECONDS, 2**self._failures))

        self._failures = 0
        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self._offset = max(self._offset, update_id + 1)
            inbound = to_inbound(update)
            if inbound is None:
                continue
            self._spawn(inbound)
        if updates:
            await status.save_offset(self.kind, bot.id, self._offset)
        return 0.0

    def _spawn(self, inbound: Inbound) -> None:
        task = asyncio.create_task(self._dispatch(inbound))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _dispatch(self, inbound: Inbound) -> None:
        dispatcher = self._dispatcher
        if dispatcher is None or self._api is None:
            return
        async with self._chats.hold(inbound.external_id), self._slots:
            try:
                await dispatcher.handle(inbound)
            except TelegramError as exc:
                logger.warning(
                    "reply not delivered",
                    chat=inbound.external_id,
                    error=exc.description,
                )
                if exc.unauthorized:
                    self._note_error(exc.description)
            except Exception:
                logger.exception("message not handled", chat=inbound.external_id)

    async def _drain(self) -> None:
        if not self._tasks:
            return
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                asyncio.gather(*self._tasks, return_exceptions=True), timeout=10
            )

    @staticmethod
    async def _cancel(task: asyncio.Task | None) -> None:
        if task is None or task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task

    @staticmethod
    async def _sleep(stop: asyncio.Event, seconds: float) -> None:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=seconds)
