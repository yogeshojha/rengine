"""Everything the API layer needs: settings, tokens, status, authentication."""

from __future__ import annotations

import json
import math
import uuid
from datetime import timedelta

from sqlalchemy import func
from sqlmodel import select

from mcp import auth, clients, registry, telemetry
from mcp import settings as server_settings
from mcp.capabilities import (
    ALWAYS_GRANTED,
    CAPABILITY_HELP,
    CAPABILITY_LABELS,
    CAPABILITY_ORDER,
    CAPABILITY_REACH,
    TOUCHES_TARGETS,
    normalize,
    within_ceiling,
)
from mcp.context import TokenIdentity
from mcp.errors import AuthError
from mcp.models import (
    MAX_NAME,
    MAX_TOKENS,
    McpCallRead,
    McpSessionRead,
    McpSettingsUpdate,
    McpStatus,
    McpToken,
    McpTokenCreate,
    McpTokenCreated,
    McpTokenRead,
    McpTokenUpdate,
    McpToolRead,
)
from shared.definitions.ask import ASK_CLIENT
from shared.definitions.channels import CHANNEL_ORDER
from shared.models.instance_settings import InstanceSettings
from shared.models.project import Project
from shared.models.target import Target
from shared.models.user import User
from shared.utils.datetime import utc_now

HIDDEN_CLIENTS: tuple[str, ...] = (*CHANNEL_ORDER, ASK_CLIENT)


class McpConfigError(ValueError):
    """The requested change is not allowed."""


class McpService:
    def __init__(self, session):
        self.session = session

    # ---- settings -------------------------------------------------------

    async def _row(self) -> InstanceSettings:
        from app.services.instance_settings import (  # noqa: PLC0415
            InstanceSettingsService,
        )

        return await InstanceSettingsService(self.session).get_or_create()

    async def config(self) -> server_settings.ServerSettings:
        return server_settings.read(await self._row())

    async def update(self, data: McpSettingsUpdate) -> None:
        row = await self._row()
        current = server_settings.read(row)

        if data.rate_limit_per_minute is not None:
            current.rate_limit_per_minute = data.rate_limit_per_minute
        if data.ceiling is not None:
            current.ceiling = data.ceiling.as_dict()
        if data.enabled is not None and data.enabled != current.enabled:
            current.enabled = data.enabled
            current.started_at = utc_now() if data.enabled else None

        server_settings.write(row, current)
        self.session.add(row)
        await self.session.commit()

        if data.ceiling is not None:
            await self._reconcile_tokens(current.ceiling)

    async def _reconcile_tokens(self, ceiling: dict[str, bool]) -> None:
        """Lowering the ceiling narrows every token that exceeded it."""
        rows = (await self.session.execute(select(McpToken))).scalars().all()
        changed = False
        for row in rows:
            trimmed = within_ceiling(list(row.capabilities or []), ceiling)
            if trimmed != list(row.capabilities or []):
                row.capabilities = trimmed
                self.session.add(row)
                changed = True
        if changed:
            await self.session.commit()

    # ---- status ---------------------------------------------------------

    async def status(self, ui_base: str, *, sessions: bool) -> McpStatus:
        config = await self.config()
        raw_sessions = (
            [
                s
                for s in await telemetry.sessions()
                if s.get("client") not in HIDDEN_CLIENTS
            ]
            if sessions
            else []
        )

        return McpStatus(
            enabled=config.enabled,
            started_at=config.started_at,
            endpoint=server_settings.endpoint_url(ui_base),
            stdio_command=server_settings.stdio_command(),
            protocol_version=server_settings.PROTOCOL_VERSION,
            rate_limit_per_minute=config.rate_limit_per_minute,
            ceiling=config.ceiling,
            sessions=[_session(s) for s in raw_sessions],
            capabilities=capability_catalog(),
            clients=clients.catalog(),
        )

    def tools(self) -> list[McpToolRead]:
        return [
            McpToolRead(
                name=spec.name,
                title=spec.title,
                description=spec.description,
                capability=spec.capability,
                group=spec.group,
                destructive=spec.destructive,
                examples=list(spec.examples),
                context_tokens=context_tokens(spec.descriptor()),
                schema=spec.schema,
            )
            for spec in registry.registry().values()
        ]

    async def calls(self, limit: int = 100) -> list[McpCallRead]:
        entries = await telemetry.recent(limit, without=HIDDEN_CLIENTS)
        return [McpCallRead(**entry) for entry in entries]

    # ---- tokens ---------------------------------------------------------

    async def tokens(self) -> list[McpTokenRead]:
        rows = (
            await self.session.execute(
                select(McpToken, User)
                .outerjoin(User, User.id == McpToken.created_by)
                .order_by(McpToken.created_at)
            )
        ).all()
        names = await self._project_names(
            {token.project_id for token, _ in rows if token.project_id}
        )
        reach = await self._reach()
        return [
            _read(token, names.get(token.project_id), reach, issuer)
            for token, issuer in rows
        ]

    async def _reach(self) -> dict[uuid.UUID | None, tuple[int, int]]:
        """Projects and targets a token scoped to each project reaches; None is every."""
        active = select(Project.id).where(Project.is_active.is_(True))
        counts = dict(
            (
                await self.session.execute(
                    select(Target.project_id, func.count())
                    .where(Target.project_id.in_(active))
                    .group_by(Target.project_id)
                )
            ).all()
        )
        projects = (
            await self.session.execute(
                select(func.count(Project.id)).where(Project.is_active.is_(True))
            )
        ).scalar()
        out: dict[uuid.UUID | None, tuple[int, int]] = {
            pid: (1, n) for pid, n in counts.items()
        }
        out[None] = (int(projects or 0), sum(counts.values()))
        return out

    async def create_token(
        self, data: McpTokenCreate, user_id: uuid.UUID, ui_base: str
    ) -> McpTokenCreated:
        existing = (await self.session.execute(select(McpToken))).scalars().all()
        if len([t for t in existing if t.revoked_at is None]) >= MAX_TOKENS:
            msg = f"The instance has {MAX_TOKENS} tokens. Revoke one first."
            raise McpConfigError(msg)
        name = _name(data.name)

        if data.project_id is not None and not await self._project_exists(
            data.project_id
        ):
            msg = "The project does not exist."
            raise McpConfigError(msg)

        config = await self.config()
        granted = within_ceiling(normalize(data.capabilities), config.ceiling)
        refused = [c for c in normalize(data.capabilities) if c not in granted]
        if refused:
            names = ", ".join(CAPABILITY_LABELS[c] for c in refused)
            msg = f"{names} is switched off for this instance. Raise the ceiling first."
            raise McpConfigError(msg)

        secret, token_hash, prefix = auth.mint()
        expires = (
            utc_now() + timedelta(days=data.expires_in_days)
            if data.expires_in_days
            else None
        )
        row = McpToken(
            name=name,
            project_id=data.project_id,
            capabilities=granted,
            token_hash=token_hash,
            token_prefix=prefix,
            expires_at=expires,
            created_by=user_id,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)

        names = await self._project_names({row.project_id} if row.project_id else set())
        url = server_settings.endpoint_url(ui_base)
        issuer = await self.session.get(User, user_id)
        return McpTokenCreated(
            token=_read(row, names.get(row.project_id), await self._reach(), issuer),
            secret=secret,
            clients=clients.snippets(url, secret),
        )

    async def update_token(
        self, token_id: uuid.UUID, data: McpTokenUpdate
    ) -> McpTokenRead:
        row = await self.session.get(McpToken, token_id)
        if row is None:
            msg = "The token does not exist."
            raise McpConfigError(msg)
        if row.revoked_at is not None:
            msg = "The token was revoked."
            raise McpConfigError(msg)

        given = data.model_fields_set
        if "name" in given and data.name is not None:
            row.name = _name(data.name)
        if "project_id" in given:
            if data.project_id is not None and not await self._project_exists(
                data.project_id
            ):
                msg = "The project does not exist."
                raise McpConfigError(msg)
            row.project_id = data.project_id
        if data.capabilities is not None:
            config = await self.config()
            asked = normalize(data.capabilities)
            granted = within_ceiling(asked, config.ceiling)
            refused = [c for c in asked if c not in granted]
            if refused:
                names = ", ".join(CAPABILITY_LABELS[c] for c in refused)
                msg = f"{names} is switched off for this instance. Raise the ceiling first."
                raise McpConfigError(msg)
            row.capabilities = granted

        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        names = await self._project_names({row.project_id} if row.project_id else set())
        issuer = (
            await self.session.get(User, row.created_by) if row.created_by else None
        )
        return _read(row, names.get(row.project_id), await self._reach(), issuer)

    async def revoke_token(self, token_id: uuid.UUID) -> None:
        row = await self.session.get(McpToken, token_id)
        if row is None:
            msg = "The token does not exist."
            raise McpConfigError(msg)
        row.revoked_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        await telemetry.drop(token_id)

    async def delete_token(self, token_id: uuid.UUID) -> None:
        row = await self.session.get(McpToken, token_id)
        if row is None:
            msg = "The token does not exist."
            raise McpConfigError(msg)
        await self.session.delete(row)
        await self.session.commit()
        await telemetry.drop(token_id)

    # ---- authentication -------------------------------------------------

    async def authenticate(self, secret: str | None) -> tuple[TokenIdentity, McpToken]:
        if not secret or not auth.looks_like_token(secret):
            msg = "Send an MCP token as `Authorization: Bearer <token>`."
            raise AuthError(msg)

        digest = auth.fingerprint(secret)
        row = (
            await self.session.execute(
                select(McpToken).where(McpToken.token_hash == digest)
            )
        ).scalar_one_or_none()

        if row is None:
            msg = "The token is not valid."
            raise AuthError(msg)
        if row.revoked_at is not None:
            msg = "The token was revoked."
            raise AuthError(msg)
        if row.expires_at is not None and row.expires_at <= utc_now():
            msg = "The token expired."
            raise AuthError(msg)
        issuer = (
            await self.session.get(User, row.created_by) if row.created_by else None
        )
        if not _backs(issuer):
            msg = "The token's issuer is not an active administrator."
            raise AuthError(msg)
        if row.project_id is not None and not await self._project_exists(
            row.project_id
        ):
            msg = "The token's project was deleted."
            raise AuthError(msg)

        config = await self.config()
        granted = within_ceiling(list(row.capabilities or []), config.ceiling)
        identity = TokenIdentity(
            id=row.id,
            name=row.name,
            project_id=row.project_id,
            capabilities=frozenset(granted),
            issued_by=row.created_by,
        )
        return identity, row

    async def mark_used(self, row: McpToken, client: str) -> None:
        row.last_used_at = utc_now()
        row.last_client = client[:120]
        row.calls = (row.calls or 0) + 1
        self.session.add(row)
        await self.session.commit()

    # ---- helpers --------------------------------------------------------

    async def _project_exists(self, project_id: uuid.UUID) -> bool:
        row = await self.session.get(Project, project_id)
        return row is not None and row.is_active

    async def _project_names(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = (
            (await self.session.execute(select(Project).where(Project.id.in_(ids))))
            .scalars()
            .all()
        )
        return {row.id: row.name for row in rows}


def capability_catalog() -> list[dict]:
    return [
        {
            "key": key,
            "label": CAPABILITY_LABELS[key],
            "help": CAPABILITY_HELP[key],
            "reach": CAPABILITY_REACH[key],
            "always": key in ALWAYS_GRANTED,
            "touches_targets": key in TOUCHES_TARGETS,
        }
        for key in CAPABILITY_ORDER
    ]


def context_tokens(descriptor: dict) -> int:
    """Estimated at four characters a token."""
    return math.ceil(len(json.dumps(descriptor, separators=(",", ":"))) / 4)


def _name(value: str) -> str:
    name = value.strip()[:MAX_NAME]
    if not name:
        msg = "Name the agent."
        raise McpConfigError(msg)
    return name


def _backs(issuer: User | None) -> bool:
    """Whether the issuer is an active superuser."""
    return issuer is not None and issuer.is_active and issuer.is_superuser


def _read(
    row: McpToken,
    project_name: str | None,
    reach: dict[uuid.UUID | None, tuple[int, int]] | None = None,
    issuer: User | None = None,
) -> McpTokenRead:
    projects, targets = (reach or {}).get(
        row.project_id, (1 if row.project_id else 0, 0)
    )
    return McpTokenRead(
        id=row.id,
        name=row.name,
        project_id=row.project_id,
        project_name=project_name,
        capabilities=list(row.capabilities or []),
        token_prefix=row.token_prefix,
        expires_at=row.expires_at,
        expired=row.expires_at is not None and row.expires_at <= utc_now(),
        revoked=row.revoked_at is not None,
        last_used_at=row.last_used_at,
        last_client=row.last_client,
        calls=row.calls or 0,
        created_at=row.created_at,
        projects=projects,
        targets=targets,
        issuer=issuer.username if issuer else None,
        issuer_valid=_backs(issuer),
    )


def _session(entry: dict) -> McpSessionRead:
    return McpSessionRead(
        token_id=uuid.UUID(entry["token_id"]),
        client=entry.get("client", "unknown"),
        agent=entry.get("agent"),
        last_seen=entry["last_seen"],
    )
