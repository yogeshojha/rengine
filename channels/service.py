"""Channel settings, pairing requests, paired chats and commands."""

from __future__ import annotations

import uuid
from datetime import datetime
from types import ModuleType

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from channels import commands, pairing, settings, status, stepup
from channels.base import DriverError
from channels.identity import effective_capabilities
from channels.models import (
    BotInfo,
    ChannelCatalogEntry,
    ChannelChat,
    ChannelChatRead,
    ChannelChatUpdate,
    ChannelCommandRead,
    ChannelConfig,
    ChannelSettingsUpdate,
    ChannelStatus,
    ChannelVerifyResult,
    CommandArgRead,
    ListenerStatus,
    PairingApprove,
    PairingRequestRead,
)
from channels.render import line
from channels.telegram import driver as telegram_driver
from mcp import telemetry
from mcp.capabilities import (
    ALWAYS_GRANTED,
    CAPABILITY_LABELS,
    normalize,
    within_ceiling,
)
from mcp.models import McpCallRead
from mcp.service import capability_catalog
from shared.definitions.channels import (
    CHANNEL_LABELS,
    CHANNEL_ORDER,
    MAX_CHATS,
    ChannelKind,
    ChatState,
)
from shared.logging import get_logger
from shared.models.project import Project
from shared.models.user import User
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

DRIVERS: dict[str, ModuleType] = {ChannelKind.TELEGRAM.value: telegram_driver}
PAIRED_MESSAGE = "Paired. Send /help for the command list."
REVOKED_MESSAGE = "Chat access revoked."


class ChannelConfigError(ValueError):
    """The requested change is not allowed."""


class ChannelNotFoundError(LookupError):
    """No channel of that name."""


def _granted(wanted: list[str], ceiling: dict[str, bool]) -> list[str]:
    """The requested capabilities, refused by name when above the ceiling."""
    asked = normalize(wanted)
    granted = within_ceiling(asked, ceiling)
    refused = [c for c in asked if c not in granted]
    if refused:
        names = ", ".join(CAPABILITY_LABELS[c] for c in refused)
        msg = f"{names} is off in the channel ceiling. Raise the ceiling first."
        raise ChannelConfigError(msg)
    return granted


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class ChannelService:
    def __init__(self, session, channel: str):
        if channel not in CHANNEL_ORDER:
            msg = f"No channel called {channel!r}."
            raise ChannelNotFoundError(msg)
        self.session = session
        self.channel = channel
        self.label = CHANNEL_LABELS[channel]
        self.driver = DRIVERS[channel]

    # ---------- config ----------

    async def row(self) -> ChannelConfig:
        found = await self.session.get(ChannelConfig, self.channel)
        if found is not None:
            return found
        found = ChannelConfig(channel=self.channel)
        self.session.add(found)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            found = await self.session.get(ChannelConfig, self.channel)
        return found

    async def status(self) -> ChannelStatus:
        row = await self.row()
        cfg = settings.read(row)
        secret = await self._token()
        heartbeat = await status.read(self.channel) or {}
        chats = (
            (
                await self.session.execute(
                    select(ChannelChat).where(ChannelChat.channel == self.channel)
                )
            )
            .scalars()
            .all()
        )
        calls = await self.calls()
        return ChannelStatus(
            channel=self.channel,
            label=self.label,
            configured=secret is not None,
            enabled=cfg.enabled,
            started_at=cfg.started_at,
            secret_masked=settings.mask_secret(secret),
            bot=cfg.bot,
            listener=ListenerStatus(
                reporting=bool(heartbeat),
                running=bool(heartbeat.get("running")),
                last_poll_at=_parse(heartbeat.get("last_poll_at")),
                updates_seen=int(heartbeat.get("updates_seen") or 0),
                last_error=heartbeat.get("last_error"),
                last_error_at=_parse(heartbeat.get("last_error_at")),
            ),
            rate_limit_per_minute=cfg.rate_limit_per_minute,
            ceiling=cfg.ceiling,
            capabilities=capability_catalog(),
            chats_total=len(chats),
            chats_active=sum(1 for c in chats if c.state == ChatState.ACTIVE.value),
            pending_total=len(await pairing.pending(self.channel)),
            commands_total=len(commands.catalog()),
            calls_recent=len(calls),
            last_call_at=calls[0].at if calls else None,
        )

    async def update(
        self, data: ChannelSettingsUpdate, user_id: uuid.UUID
    ) -> ChannelStatus:
        row = await self.row()
        cfg = settings.read(row)

        if data.rate_limit_per_minute is not None:
            cfg.rate_limit_per_minute = data.rate_limit_per_minute
        if data.ceiling is not None:
            cfg.ceiling = data.ceiling.as_dict()

        if data.enabled is not None and data.enabled != cfg.enabled:
            if data.enabled:
                secret = await self._token()
                if secret is None:
                    msg = f"Add a {self.label} API key before starting the listener."
                    raise ChannelConfigError(msg)
                cfg.bot = await self._verify(secret)
                cfg.started_at = utc_now()
            else:
                cfg.started_at = None
            cfg.enabled = data.enabled

        settings.write(row, cfg)
        row.updated_by = user_id
        self.session.add(row)
        await self.session.commit()

        if data.ceiling is not None:
            await self._reconcile_chats(cfg.ceiling)
        return await self.status()

    async def verify(self) -> ChannelVerifyResult:
        row = await self.row()
        secret = await self._token()
        if secret is None:
            error = f"No {self.label} API key is saved."
            return ChannelVerifyResult(ok=False, error=error)
        try:
            info = await self._verify(secret)
        except ChannelConfigError as exc:
            return ChannelVerifyResult(ok=False, error=str(exc))
        cfg = settings.read(row)
        cfg.bot = info
        settings.write(row, cfg)
        self.session.add(row)
        await self.session.commit()
        return ChannelVerifyResult(ok=True, bot=info)

    async def _token(self) -> str | None:
        return await settings.bot_token(self.session, self.channel)

    async def _verify(self, secret: str) -> BotInfo:
        try:
            return await self.driver.verify(secret)
        except DriverError as exc:
            msg = f"{self.label} refused the bot token: {exc.description}."
            raise ChannelConfigError(msg) from exc

    async def _reconcile_chats(self, ceiling: dict[str, bool]) -> None:
        rows = (
            (
                await self.session.execute(
                    select(ChannelChat).where(ChannelChat.channel == self.channel)
                )
            )
            .scalars()
            .all()
        )
        changed = False
        for row in rows:
            trimmed = within_ceiling(list(row.capabilities or []), ceiling)
            if trimmed != list(row.capabilities or []):
                row.capabilities = trimmed
                self.session.add(row)
                changed = True
        if changed:
            await self.session.commit()

    # ---------- pairing ----------

    async def pending(self) -> list[PairingRequestRead]:
        out = []
        for entry in await pairing.pending(self.channel):
            requested = _parse(entry.get("requested_at"))
            expires = _parse(entry.get("expires_at"))
            if requested is None or expires is None:
                continue
            out.append(
                PairingRequestRead(
                    code=entry["code"],
                    external_id=entry["external_id"],
                    display=entry.get("display") or entry["external_id"],
                    username=entry.get("username"),
                    first_name=entry.get("first_name"),
                    requested_at=requested,
                    expires_at=expires,
                )
            )
        return out

    async def approve(
        self, code: str, data: PairingApprove, admin_id: uuid.UUID
    ) -> ChannelChatRead:
        user = await self.session.get(User, data.user_id)
        if user is None or not user.is_active:
            msg = "The account does not exist or is inactive."
            raise ChannelConfigError(msg)
        project = await self.session.get(Project, data.project_id)
        if project is None:
            msg = "The project does not exist."
            raise ChannelConfigError(msg)

        cfg = settings.read(await self.row())
        granted = _granted(data.capabilities, cfg.ceiling)

        active = await self._count_active()
        if active >= MAX_CHATS:
            msg = f"The channel has {MAX_CHATS} paired chats. Revoke one first."
            raise ChannelConfigError(msg)

        request = await pairing.take(self.channel, code)
        if request is None:
            msg = "The pairing code expired or was already used."
            raise ChannelConfigError(msg)

        row = await self._chat_by_external(request["external_id"])
        if row is None:
            row = ChannelChat(channel=self.channel, external_id=request["external_id"])
        row.display = (request.get("display") or request["external_id"])[:120]
        row.user_id = user.id
        row.project_id = project.id
        row.capabilities = granted
        row.state = ChatState.ACTIVE.value
        row.approved_by = admin_id
        row.approved_at = utc_now()
        row.revoked_at = None
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)

        await self._notify(row.external_id, PAIRED_MESSAGE)
        return await self._read(row)

    async def block(self, code: str, admin_id: uuid.UUID) -> None:
        request = await pairing.take(self.channel, code)
        if request is None:
            msg = "The pairing code expired or was already used."
            raise ChannelConfigError(msg)
        row = await self._chat_by_external(request["external_id"])
        if row is None:
            row = ChannelChat(channel=self.channel, external_id=request["external_id"])
        row.display = (request.get("display") or request["external_id"])[:120]
        row.state = ChatState.BLOCKED.value
        row.capabilities = []
        row.approved_by = admin_id
        row.revoked_at = utc_now()
        self.session.add(row)
        await self.session.commit()

    # ---------- chats ----------

    async def chats(self) -> list[ChannelChatRead]:
        rows = (
            (
                await self.session.execute(
                    select(ChannelChat)
                    .where(ChannelChat.channel == self.channel)
                    .order_by(ChannelChat.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [await self._read(row) for row in rows]

    async def update_chat(
        self, chat_id: uuid.UUID, data: ChannelChatUpdate
    ) -> ChannelChatRead:
        row = await self._chat(chat_id)
        if row.state != ChatState.ACTIVE.value:
            msg = "Only an active chat can be changed."
            raise ChannelConfigError(msg)
        if data.project_id is not None:
            if await self.session.get(Project, data.project_id) is None:
                msg = "The project does not exist."
                raise ChannelConfigError(msg)
            row.project_id = data.project_id
        if data.capabilities is not None:
            cfg = settings.read(await self.row())
            row.capabilities = _granted(data.capabilities, cfg.ceiling)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return await self._read(row)

    async def revoke_chat(self, chat_id: uuid.UUID) -> ChannelChatRead:
        row = await self._chat(chat_id)
        if row.state == ChatState.ACTIVE.value:
            row.state = ChatState.REVOKED.value
            row.revoked_at = utc_now()
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
            await stepup.clear_grace(self.channel, row.external_id)
            await self._notify(row.external_id, REVOKED_MESSAGE)
        return await self._read(row)

    async def delete_chat(self, chat_id: uuid.UUID) -> None:
        row = await self._chat(chat_id)
        await stepup.clear_grace(self.channel, row.external_id)
        await pairing.forget(self.channel, row.external_id)
        await self.session.delete(row)
        await self.session.commit()

    async def _chat(self, chat_id: uuid.UUID) -> ChannelChat:
        row = await self.session.get(ChannelChat, chat_id)
        if row is None or row.channel != self.channel:
            msg = "The chat does not exist."
            raise ChannelConfigError(msg)
        return row

    async def _chat_by_external(self, external_id: str) -> ChannelChat | None:
        statement = select(ChannelChat).where(
            ChannelChat.channel == self.channel,
            ChannelChat.external_id == external_id,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def _count_active(self) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(ChannelChat)
            .where(
                ChannelChat.channel == self.channel,
                ChannelChat.state == ChatState.ACTIVE.value,
            )
        )
        return int(total or 0)

    async def _read(self, row: ChannelChat) -> ChannelChatRead:
        user = await self.session.get(User, row.user_id) if row.user_id else None
        project = (
            await self.session.get(Project, row.project_id) if row.project_id else None
        )
        cfg = settings.read(await self.row())
        return ChannelChatRead(
            id=row.id,
            channel=row.channel,
            external_id=row.external_id,
            display=row.display,
            user_id=row.user_id,
            username=user.username if user else None,
            totp_enabled=bool(user.totp_enabled) if user else False,
            project_id=row.project_id,
            project_name=project.name if project else None,
            capabilities=list(row.capabilities or []),
            effective_capabilities=effective_capabilities(row, user, cfg.ceiling),
            state=row.state,
            approved_at=row.approved_at,
            revoked_at=row.revoked_at,
            last_seen_at=row.last_seen_at,
            last_command=row.last_command,
            calls=row.calls or 0,
            created_at=row.created_at,
        )

    async def _notify(self, external_id: str, text: str) -> None:
        row = await self.row()
        cfg = settings.read(row)
        secret = await self._token()
        if not cfg.enabled or secret is None:
            return
        try:
            await self.driver.notify(secret, external_id, [line(text)])
        except Exception as exc:
            logger.warning("chat not notified", error=type(exc).__name__)

    # ---------- catalog ----------

    @staticmethod
    def commands() -> list[ChannelCommandRead]:
        out = []
        for spec in commands.catalog().values():
            out.append(
                ChannelCommandRead(
                    name=spec.name,
                    tool=spec.tool,
                    source=spec.source,
                    group=spec.group,
                    title=spec.title,
                    description=spec.description,
                    capability=spec.capability,
                    touches_target=spec.touches_target,
                    queued=spec.queued,
                    value_field=spec.value_field,
                    presets=dict(spec.presets),
                    usage=spec.usage,
                    args=[CommandArgRead(**arg) for arg in spec.args()],
                )
            )
        return out

    async def calls(self, limit: int = 200) -> list[McpCallRead]:
        entries = await telemetry.recent(limit, client=self.channel)
        return [McpCallRead(**entry) for entry in entries]


async def catalog(session) -> list[ChannelCatalogEntry]:
    out = []
    for kind in CHANNEL_ORDER:
        row = await session.get(ChannelConfig, kind)
        cfg = settings.read(row)
        heartbeat = await status.read(kind) or {}
        out.append(
            ChannelCatalogEntry(
                channel=kind,
                label=CHANNEL_LABELS[kind],
                configured=await settings.bot_token(session, kind) is not None,
                enabled=cfg.enabled,
                running=bool(heartbeat.get("running")),
            )
        )
    return out


__all__ = [
    "ALWAYS_GRANTED",
    "ChannelConfigError",
    "ChannelNotFoundError",
    "ChannelService",
    "catalog",
]
