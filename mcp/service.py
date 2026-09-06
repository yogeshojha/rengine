"""Everything the API layer needs: settings, tokens, status, authentication."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

from sqlmodel import select

from mcp import auth, registry, telemetry
from mcp import settings as server_settings
from mcp.capabilities import (
    CAPABILITY_HELP,
    CAPABILITY_LABELS,
    CAPABILITY_ORDER,
    TOUCHES_TARGETS,
    normalize,
    within_ceiling,
)
from mcp.context import TokenIdentity
from mcp.errors import AuthError
from mcp.models import (
    MAX_TOKENS,
    McpCallRead,
    McpSessionRead,
    McpSettingsUpdate,
    McpStatus,
    McpToken,
    McpTokenCreate,
    McpTokenCreated,
    McpTokenRead,
    McpToolRead,
)
from shared.models.instance_settings import InstanceSettings
from shared.models.project import Project
from shared.utils.datetime import utc_now


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

    async def update(self, data: McpSettingsUpdate) -> McpStatus:
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
        return await self.status()

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

    async def status(self, ui_base: str = "") -> McpStatus:
        config = await self.config()
        specs = registry.registry()
        tokens = (await self.session.execute(select(McpToken))).scalars().all()
        active = [t for t in tokens if _active(t)]
        raw_sessions = await telemetry.sessions()

        return McpStatus(
            enabled=config.enabled,
            started_at=config.started_at,
            endpoint=server_settings.endpoint_url(ui_base),
            stdio_command=server_settings.stdio_command(),
            protocol_version=server_settings.PROTOCOL_VERSION,
            rate_limit_per_minute=config.rate_limit_per_minute,
            ceiling=config.ceiling,
            tools_total=len(specs),
            tools_available=sum(
                1 for s in specs.values() if config.ceiling.get(s.capability, False)
            ),
            tokens_total=len(tokens),
            tokens_active=len(active),
            sessions=[_session(s) for s in raw_sessions],
            calls_today=await telemetry.calls_today(),
            last_call_at=await telemetry.last_call_at(),
            capabilities=capability_catalog(),
        )

    def tools(self) -> list[McpToolRead]:
        return [
            McpToolRead(
                name=spec.name,
                title=spec.title,
                description=spec.description,
                capability=spec.capability,
                group=spec.group,
                examples=list(spec.examples),
                schema=spec.schema,
            )
            for spec in registry.registry().values()
        ]

    async def calls(self, limit: int = 100) -> list[McpCallRead]:
        return [McpCallRead(**entry) for entry in await telemetry.recent(limit)]

    async def disconnect(self, token_id: uuid.UUID) -> int:
        return await telemetry.drop(token_id)

    # ---- tokens ---------------------------------------------------------

    async def tokens(self) -> list[McpTokenRead]:
        rows = (
            (await self.session.execute(select(McpToken).order_by(McpToken.created_at)))
            .scalars()
            .all()
        )
        names = await self._project_names({r.project_id for r in rows if r.project_id})
        return [_read(row, names.get(row.project_id)) for row in rows]

    async def create_token(
        self, data: McpTokenCreate, user_id: uuid.UUID, ui_base: str = ""
    ) -> McpTokenCreated:
        existing = (await self.session.execute(select(McpToken))).scalars().all()
        if len([t for t in existing if t.revoked_at is None]) >= MAX_TOKENS:
            msg = f"This instance already has {MAX_TOKENS} tokens. Revoke one first."
            raise McpConfigError(msg)

        if data.project_id is not None and not await self._project_exists(
            data.project_id
        ):
            msg = "That project does not exist."
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
            name=data.name.strip()[:80],
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
        return McpTokenCreated(
            token=_read(row, names.get(row.project_id)),
            secret=secret,
            client_config=client_config(secret, ui_base),
        )

    async def revoke_token(self, token_id: uuid.UUID) -> None:
        row = await self.session.get(McpToken, token_id)
        if row is None:
            msg = "That token does not exist."
            raise McpConfigError(msg)
        row.revoked_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        await telemetry.drop(token_id)

    async def delete_token(self, token_id: uuid.UUID) -> None:
        row = await self.session.get(McpToken, token_id)
        if row is None:
            msg = "That token does not exist."
            raise McpConfigError(msg)
        await self.session.delete(row)
        await self.session.commit()
        await telemetry.drop(token_id)

    # ---- authentication -------------------------------------------------

    async def authenticate(self, secret: str | None) -> tuple[TokenIdentity, McpToken]:
        if not secret or not auth.looks_like_token(secret):
            msg = "Send a reNgine MCP token as `Authorization: Bearer <token>`."
            raise AuthError(msg)

        digest = auth.fingerprint(secret)
        row = (
            await self.session.execute(
                select(McpToken).where(McpToken.token_hash == digest)
            )
        ).scalar_one_or_none()

        if row is None:
            msg = "That token is not valid."
            raise AuthError(msg)
        if row.revoked_at is not None:
            msg = "That token was revoked."
            raise AuthError(msg)
        if row.expires_at is not None and row.expires_at <= utc_now():
            msg = "That token expired."
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
        return await self.session.get(Project, project_id) is not None

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
            "always": key not in ("plan", "write", "launch"),
            "touches_targets": key in TOUCHES_TARGETS,
        }
        for key in CAPABILITY_ORDER
    ]


def client_config(secret: str, ui_base: str = "") -> str:
    """A block the user pastes into their agent, with the token already in it."""
    body = {
        "mcpServers": {
            server_settings.SERVER_NAME: {
                "type": "http",
                "url": server_settings.endpoint_url(ui_base or "http://localhost:8000"),
                "headers": {"Authorization": f"Bearer {secret}"},
            }
        }
    }
    return json.dumps(body, indent=2)


def _active(row: McpToken) -> bool:
    if row.revoked_at is not None:
        return False
    return row.expires_at is None or row.expires_at > utc_now()


def _read(row: McpToken, project_name: str | None) -> McpTokenRead:
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
    )


def _session(entry: dict) -> McpSessionRead:
    return McpSessionRead(
        token_id=uuid.UUID(entry["token_id"]),
        token_name=entry.get("token_name", "token"),
        client=entry.get("client", "unknown"),
        capabilities=list(entry.get("capabilities", [])),
        first_seen=entry["first_seen"],
        last_seen=entry["last_seen"],
        calls=int(entry.get("calls", 0)),
        last_tool=entry.get("last_tool"),
    )
