"""The message pipeline: pairing gate, step-up, parse, invoke, render."""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from typing import Any

from sqlalchemy import String, cast, select

from channels import commands, pairing, render, settings, stepup
from channels.base import Channel, Inbound
from channels.commands import CommandError, CommandSpec, Parsed
from channels.identity import effective_capabilities, identity_for
from channels.models import MAX_COMMAND, ChannelChat, ChannelConfig
from channels.render import Line, bold, code, italic, line
from mcp import limits, server, telemetry
from mcp.capabilities import CAPABILITY_LABELS
from mcp.context import TokenIdentity, ToolContext
from mcp.errors import McpError
from mcp.phrasing import short_id
from shared.definitions.channels import (
    CHAT_GROUP_LABELS,
    COMMAND_TEXT_MAX,
    PAIRING_CODE_TTL,
    STEP_UP_PENDING_SECONDS,
    ChatState,
    CommandSource,
)
from shared.definitions.toolbox import TERMINAL_STATUSES, RunStatus
from shared.logging import get_logger
from shared.models.project import Project
from shared.models.scan import Scan
from shared.models.target import Target
from shared.models.user import User
from shared.services.celery_dispatch import dispatch_toolbox_run
from shared.utils.datetime import utc_now
from shared.utils.net import redact_url_queries
from shared.utils.text import strip_control
from toolbox import registry as toolbox_registry
from toolbox import store
from toolbox.base import ToolContext as LookupContext
from toolbox.base import ToolError as LookupError
from toolbox.runner import RUN_DEADLINE_SECONDS, expire, validate

logger = get_logger(__name__)

INLINE_TIMEOUT = 60
FOLLOW_POLL_SECONDS = 3
_PREFIX = re.compile(r"^[0-9a-f-]{6,36}$")
_UUID_IN_TEXT = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I
)
_STAMP_IN_TEXT = re.compile(
    r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}):\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?"
)

HELP_HINT = "Send /help for the command list."
STEP_UP_PROMPT = (
    "Send the 6-digit authenticator code to confirm. "
    f"The request expires in {STEP_UP_PENDING_SECONDS // 60} minutes."
)
INACTIVE_ACCOUNT = "The account bound to this chat is inactive."
PAIRING_HOW = (
    "An administrator approves it under Integrations, Remote control. "
    f"The code expires in {PAIRING_CODE_TTL // 60} minutes."
)
QUEUE_FULL = "Pairing queue is full. Try again later."


class Dispatcher:
    def __init__(self, channel: Channel, sessions: Any, ui_base: str):
        self.channel = channel
        self.sessions = sessions
        self.ui_base = ui_base
        self._followers: set[asyncio.Task] = set()

    async def close(self) -> None:
        for task in list(self._followers):
            task.cancel()
        await asyncio.gather(*self._followers, return_exceptions=True)

    # ---------- entry ----------

    async def handle(self, inbound: Inbound) -> None:  # noqa: PLR0911
        if not inbound.private:
            return
        kind = self.channel.kind
        async with self.sessions() as session:
            row = await session.get(ChannelConfig, kind)
            cfg = settings.read(row)
            if not cfg.enabled:
                return

            chat = await self._chat(session, inbound.external_id)
            if chat is None or chat.state == ChatState.REVOKED.value:
                await self._pair(inbound)
                return
            if chat.state != ChatState.ACTIVE.value:
                return

            user = await session.get(User, chat.user_id) if chat.user_id else None
            if user is None or not user.is_active:
                await self._say(inbound.external_id, INACTIVE_ACCOUNT)
                return

            text = inbound.text.strip()
            if stepup.looks_like_code(text):
                await self._confirm(session, cfg, chat, user, inbound, text)
                return

            try:
                parsed = commands.parse(text)
            except CommandError as exc:
                await self._say(inbound.external_id, str(exc))
                return
            if parsed is None:
                await self._say(inbound.external_id, HELP_HINT)
                return

            await self._run(session, cfg, chat, user, inbound, parsed)

    # ---------- pairing ----------

    async def _pair(self, inbound: Inbound) -> None:
        code_value, created = await pairing.request(
            self.channel.kind,
            external_id=inbound.external_id,
            display=inbound.display,
            username=inbound.username,
            first_name=inbound.first_name,
        )
        if code_value is None:
            await self._say(inbound.external_id, QUEUE_FULL)
            return
        if not created:
            return
        await self.channel.reply(
            inbound.external_id,
            [line("Pairing code ", code(code_value), "."), line(PAIRING_HOW)],
        )

    # ---------- step-up ----------

    async def _confirm(
        self,
        session: Any,
        cfg: settings.ChannelSettings,
        chat: ChannelChat,
        user: User,
        inbound: Inbound,
        text: str,
    ) -> None:
        kind = self.channel.kind
        external_id = inbound.external_id
        if inbound.message_id:
            try:
                await self.channel.delete(external_id, inbound.message_id)
            except Exception as exc:
                logger.debug("code message not deleted", error=str(exc))

        wait = await stepup.attempts_exhausted(kind, external_id, user.id)
        if wait:
            minutes = max(1, -(-wait // 60))
            await self._say(
                external_id, f"Too many attempts. Try again in {minutes} min."
            )
            return

        pending = await stepup.take(kind, external_id)
        if pending is None:
            await self._say(external_id, "No command is waiting for confirmation.")
            return

        from app.services.totp import TOTPService  # noqa: PLC0415

        try:
            accepted = await TOTPService(session).verify_code(user, text)
        except ValueError:
            accepted = False
        if not accepted:
            await stepup.note_failure(kind, external_id, user.id)
            await stepup.hold(kind, external_id, pending)
            await self._say(external_id, "Code not accepted.")
            return

        await stepup.clear_failures(kind, external_id, user.id)
        await stepup.grant(kind, external_id)
        parsed = commands.parse(pending)
        if parsed is None:
            return
        await self._run(session, cfg, chat, user, inbound, parsed, confirmed=True)

    # ---------- commands ----------

    async def _run(  # noqa: PLR0911
        self,
        session: Any,
        cfg: settings.ChannelSettings,
        chat: ChannelChat,
        user: User,
        inbound: Inbound,
        parsed: Parsed,
        *,
        confirmed: bool = False,
    ) -> None:
        kind = self.channel.kind
        external_id = inbound.external_id
        spec = commands.get(parsed.name)
        if spec is None:
            await self._say(external_id, f"Unknown command /{parsed.name}. {HELP_HINT}")
            return

        await self._touch(session, chat, parsed.name)
        if not confirmed:
            await stepup.take(kind, external_id)

        if spec.builtin:
            await self._builtin(session, cfg, chat, user, parsed, spec)
            return

        identity = identity_for(chat, user, cfg.ceiling)
        if spec.capability not in identity.capabilities:
            await self.channel.reply(
                external_id, self._refusal(spec, chat, user, cfg.ceiling)
            )
            return

        if chat.project_id is None:
            await self._say(external_id, "Select a project first: /project <name>.")
            return

        try:
            args = commands.bind(spec, parsed)
        except CommandError as exc:
            await self._say(external_id, str(exc))
            return

        if await limits.exceeded(identity.id, cfg.rate_limit_per_minute):
            await self._say(external_id, "Rate limit exceeded. Try again in a minute.")
            return

        if (
            spec.steps_up
            and not confirmed
            and not await stepup.in_grace(kind, external_id)
        ):
            await stepup.hold(kind, external_id, parsed.raw)
            await self._say(external_id, STEP_UP_PROMPT)
            return

        try:
            args = await self._expand_ids(session, chat, args)
        except CommandError as exc:
            await self._say(external_id, str(exc))
            return

        if spec.source == CommandSource.TOOLBOX.value:
            await self._lookup(
                session, chat, user, identity, spec, args, external_id, said(parsed)
            )
        else:
            await self._tool(session, identity, spec, args, external_id, said(parsed))

    async def _tool(
        self,
        session: Any,
        identity: TokenIdentity,
        spec: CommandSpec,
        args: dict,
        external_id: str,
        command: str,
    ) -> None:
        ctx = ToolContext(
            session=session,
            token=identity,
            ui_base_url=self.ui_base,
            client=self.channel.kind,
            extras={"command": command},
        )
        try:
            result = await server.invoke(ctx, spec.tool or "", args)
        except McpError as exc:
            await self.channel.reply(external_id, render.text_lines(exc.message))
            return
        await self.channel.reply(
            external_id, render.result_lines(result, rewrite=self._chat_text)
        )

    async def _lookup(  # noqa: PLR0911
        self,
        session: Any,
        chat: ChannelChat,
        user: User,
        identity: TokenIdentity,
        spec: CommandSpec,
        args: dict,
        external_id: str,
        command: str,
    ) -> None:
        tool = toolbox_registry.get(spec.tool or "")
        if tool is None:
            await self._say(external_id, f"/{spec.name} is not available.")
            return
        try:
            payload = validate(tool, args)
        except LookupError as exc:
            await self._say(external_id, str(exc))
            return

        ctx = LookupContext(session=session, project_id=chat.project_id)
        label = tool.tool_cls.label_for(payload)

        if tool.queued:
            run = store.new_run(
                tool=tool.name,
                title=tool.title,
                label=label,
                payload=payload.model_dump(mode="json"),
                status=RunStatus.QUEUED.value,
            )
            await store.save(user.id, run)
            accepted = dispatch_toolbox_run(
                run_id=run.id,
                user_id=str(user.id),
                tool=tool.name,
                payload=run.input,
                project_id=str(chat.project_id) if chat.project_id else None,
            )
            if not accepted:
                await self._say(
                    external_id, "Run not queued. Check that the worker is running."
                )
                return
            await self.channel.reply(
                external_id,
                [
                    line(
                        f"{tool.title} for {label} queued. Run ",
                        code(short_id(run.id)),
                        ". The result is sent when it completes.",
                    )
                ],
            )
            task = asyncio.create_task(
                self._follow(user.id, run.id, external_id, identity, tool.name, command)
            )
            self._followers.add(task)
            task.add_done_callback(self._followers.discard)
            return

        started = time.monotonic()
        try:
            outcome = await asyncio.wait_for(
                tool.tool_cls().run(ctx, payload), timeout=INLINE_TIMEOUT
            )
        except TimeoutError:
            await self._observe(identity, tool.name, False, started, "timeout", command)
            await self._say(
                external_id,
                f"Lookup timed out after {INLINE_TIMEOUT} seconds.",
            )
            return
        except LookupError as exc:
            await self._observe(identity, tool.name, False, started, str(exc), command)
            await self._say(external_id, str(exc))
            return
        except Exception as exc:
            reason = redact_url_queries(f"{type(exc).__name__}: {exc}")
            logger.warning("lookup failed", tool=tool.name, error=reason)
            await self._observe(identity, tool.name, False, started, reason, command)
            await self._say(external_id, "Lookup failed.")
            return
        await self._observe(identity, tool.name, True, started, None, command)
        await self.channel.reply(
            external_id, render.outcome_lines(outcome, self.ui_base)
        )

    async def _follow(self, *args: Any) -> None:
        try:
            await self._follow_run(*args)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("run result not delivered", error=type(exc).__name__)

    async def _follow_run(
        self,
        user_id: uuid.UUID,
        run_id: str,
        external_id: str,
        identity: TokenIdentity,
        tool: str,
        command: str,
    ) -> None:
        started = time.monotonic()
        deadline = started + RUN_DEADLINE_SECONDS + 30
        run = None
        while time.monotonic() < deadline:
            await asyncio.sleep(FOLLOW_POLL_SECONDS)
            run = await store.get(user_id, run_id)
            if run is None:
                await self._say(
                    external_id, f"Run {short_id(run_id)} is no longer available."
                )
                return
            run = expire(run)
            if run.status in TERMINAL_STATUSES:
                break
        if run is None or run.status not in TERMINAL_STATUSES:
            await self._observe(identity, tool, False, started, "timeout", command)
            await self._say(external_id, f"Run {short_id(run_id)} did not complete.")
            return
        ok = run.status == RunStatus.COMPLETED.value
        await self._observe(
            identity, tool, ok, started, None if ok else run.error, command
        )
        await self.channel.reply(external_id, render.run_lines(run, self.ui_base))

    async def _observe(
        self,
        identity: TokenIdentity,
        tool: str,
        ok: bool,
        started: float,
        detail: str | None,
        command: str | None = None,
    ) -> None:
        await telemetry.record(
            telemetry.CallRecord(
                token_id=identity.id,
                token_name=identity.name,
                client=self.channel.kind,
                tool=tool,
                ok=ok,
                duration_ms=int((time.monotonic() - started) * 1000),
                detail=detail[:300] if detail else None,
                command=command,
            )
        )

    # ---------- builtins ----------

    async def _builtin(
        self,
        session: Any,
        cfg: settings.ChannelSettings,
        chat: ChannelChat,
        user: User,
        parsed: Parsed,
        spec: CommandSpec,
    ) -> None:
        external_id = chat.external_id
        if spec.name == "help":
            target = parsed.bare[0] if parsed.bare else None
            await self.channel.reply(external_id, self._help(target))
        elif spec.name in {"start", "whoami"}:
            await self.channel.reply(
                external_id, await self._whoami(session, cfg, chat, user)
            )
        elif spec.name == "projects":
            await self.channel.reply(external_id, await self._projects(session, chat))
        elif spec.name == "project":
            await self._project(session, chat, parsed)
        elif spec.name == "unpair":
            chat.state = ChatState.REVOKED.value
            chat.revoked_at = utc_now()
            session.add(chat)
            await session.commit()
            await pairing.forget(self.channel.kind, external_id)
            await stepup.clear_grace(self.channel.kind, external_id)
            await self._say(external_id, "Chat unpaired.")

    def _help(self, name: str | None) -> list[Line]:
        if name:
            spec = commands.get(name)
            if spec is None:
                return [
                    line(
                        f"Unknown command /{commands.normalise_name(name)}. {HELP_HINT}"
                    )
                ]
            return self._usage(spec)

        out: list[Line] = [line(bold("reNgine commands"))]
        for group, specs in commands.by_group():
            out.append(line(""))
            out.append(line(bold(CHAT_GROUP_LABELS[group])))
            for spec in specs:
                tail = " · confirm" if spec.steps_up else ""
                out.append(
                    line(code(spec.usage.split(" [")[0]), f" · {spec.title}{tail}")
                )
        out.append(line(""))
        out.append(line("Send /help <command> for its arguments."))
        return out

    @staticmethod
    def _usage(spec: CommandSpec) -> list[Line]:
        out: list[Line] = [line(code(spec.usage)), line(spec.description)]
        args = spec.args()
        if args:
            out.append(line(""))
            out.append(line(bold("Arguments")))
            for arg in args:
                flags = [arg["type"]]
                if arg["required"]:
                    flags.append("required")
                if arg["default"]:
                    flags.append(f"default {arg['default']}")
                detail = f": {arg['description']}" if arg["description"] else ""
                out.append(
                    line(f"{render.BULLET}{arg['name']} ({', '.join(flags)}){detail}")
                )
                if arg["options"]:
                    out.append(
                        line(f"{render.INDENT}one of: {', '.join(arg['options'])}")
                    )
        if spec.steps_up:
            out.append(line(""))
            out.append(line(italic("Confirmed with the account's authenticator code.")))
        return out

    async def _whoami(
        self, session: Any, cfg: settings.ChannelSettings, chat: ChannelChat, user: User
    ) -> list[Line]:
        project = (
            await session.get(Project, chat.project_id) if chat.project_id else None
        )
        granted = effective_capabilities(chat, user, cfg.ceiling)
        remaining = await stepup.grace_remaining(self.channel.kind, chat.external_id)
        out = [
            line(bold(chat.display or chat.external_id), f" · account {user.username}"),
            line(f"Project: {project.name if project else 'none selected'}"),
            line(
                "Capabilities: "
                + ", ".join(CAPABILITY_LABELS[c].lower() for c in granted)
            ),
        ]
        if user.totp_enabled:
            window = f"{max(1, remaining // 60)} min remaining" if remaining else "none"
            out.append(line(f"Authenticator: enrolled · confirmation window: {window}"))
        else:
            out.append(line("Authenticator: not enrolled · read only"))
        return out

    async def _projects(self, session: Any, chat: ChannelChat) -> list[Line]:
        rows = (
            (await session.execute(select(Project).where(Project.is_active.is_(True))))
            .scalars()
            .all()
        )
        if not rows:
            return [line("No projects.")]
        out = [line(bold("Projects"))]
        for row in sorted(rows, key=lambda r: r.name.lower()):
            mark = " · selected" if row.id == chat.project_id else ""
            out.append(line(f"{render.BULLET}{row.name} ", code(row.slug), mark))
        out.append(line(""))
        out.append(line("Switch with /project <name>."))
        return out

    async def _project(self, session: Any, chat: ChannelChat, parsed: Parsed) -> None:
        external_id = chat.external_id
        wanted = " ".join(parsed.bare).strip()
        if not wanted:
            project = (
                await session.get(Project, chat.project_id) if chat.project_id else None
            )
            if project is None:
                await self._say(
                    external_id, "No project selected. Send /project <name>."
                )
            else:
                await self._say(external_id, f"Project: {project.name}.")
            return
        rows = (
            (await session.execute(select(Project).where(Project.is_active.is_(True))))
            .scalars()
            .all()
        )
        match = _pick_project(rows, wanted)
        if match is None:
            names = ", ".join(sorted(r.name for r in rows)[:8])
            await self._say(
                external_id,
                f"No project matches {wanted}. Projects: {names or 'none'}.",
            )
            return
        chat.project_id = match.id
        session.add(chat)
        await session.commit()
        await self._say(external_id, f"Project set to {match.name}.")

    # ---------- helpers ----------

    @staticmethod
    def _chat_text(text: str) -> str:
        """Rewrite tool names as commands and shorten ids and timestamps."""
        for name, spec in commands.by_tool().items():
            text = re.sub(rf"\b{re.escape(name)}\b", f"/{spec.name}", text)
        text = _UUID_IN_TEXT.sub(lambda m: short_id(m.group(0)), text)
        text = _STAMP_IN_TEXT.sub(r"\1 \2", text)
        return text.replace("via MCP", "from chat")

    async def _chat(self, session: Any, external_id: str) -> ChannelChat | None:
        statement = select(ChannelChat).where(
            ChannelChat.channel == self.channel.kind,
            ChannelChat.external_id == external_id,
        )
        return (await session.execute(statement)).scalar_one_or_none()

    @staticmethod
    async def _touch(session: Any, chat: ChannelChat, command: str) -> None:
        chat.last_seen_at = utc_now()
        chat.last_command = command[:MAX_COMMAND]
        chat.calls = (chat.calls or 0) + 1
        session.add(chat)
        await session.commit()

    async def _say(self, external_id: str, text: str) -> None:
        await self.channel.reply(external_id, render.text_lines(text))

    @staticmethod
    def _refusal(
        spec: CommandSpec, chat: ChannelChat, user: User, ceiling: dict[str, bool]
    ) -> list[Line]:
        capability = spec.capability
        label = CAPABILITY_LABELS.get(capability, capability).lower()
        if not ceiling.get(capability, False):
            reason = "It is off in the channel ceiling."
        elif capability not in (chat.capabilities or []):
            reason = "This chat was not granted it."
        elif not user.totp_enabled:
            reason = "The account has no authenticator enrolled."
        else:
            reason = "It is not available to this chat."
        return [line(f"/{spec.name} needs the {label} capability. {reason}")]

    async def _expand_ids(self, session: Any, chat: ChannelChat, args: dict) -> dict:
        """Resolve a scan id prefix to the scan, or to its target on a target field."""
        for key, value in list(args.items()):
            if not isinstance(value, str) or not value:
                continue
            if key == "scan" or (
                key == "target" and _PREFIX.match(value.lower()) and "." not in value
            ):
                prefix = value.lower()
            else:
                continue
            matches = await self._scans_by_prefix(session, chat.project_id, prefix)
            if len(matches) > 1:
                msg = f"{value} matches more than one scan. Add more characters."
                raise CommandError(msg)
            if matches:
                scan_id, target_value = matches[0]
                args[key] = str(scan_id) if key == "scan" else target_value
            elif key == "scan" and not _UUID_IN_TEXT.fullmatch(value):
                msg = f"No scan matches {value}. /scans lists the recent ones."
                raise CommandError(msg)
        return args

    @staticmethod
    async def _scans_by_prefix(
        session: Any, project_id: uuid.UUID, prefix: str
    ) -> list[tuple[uuid.UUID, str]]:
        statement = (
            select(Scan.id, Target.target_value)
            .join(Target, Target.id == Scan.target_id)
            .where(
                Scan.project_id == project_id,
                cast(Scan.id, String).like(f"{prefix}%"),
            )
            .order_by(Scan.created_at.desc())
            .limit(2)
        )
        return [(row[0], row[1]) for row in (await session.execute(statement)).all()]


def said(parsed: Parsed) -> str:
    return strip_control(parsed.raw)[:COMMAND_TEXT_MAX]


def _pick_project(rows: list[Project], wanted: str) -> Project | None:
    needle = wanted.lower()
    for row in rows:
        if needle in {str(row.id), row.name.lower(), row.slug.lower()}:
            return row
    partial = [
        r
        for r in rows
        if r.name.lower().startswith(needle) or r.slug.startswith(needle)
    ]
    return partial[0] if len(partial) == 1 else None
