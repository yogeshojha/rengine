"""Who may launch with a context or engine that carries credentials."""

from __future__ import annotations

import uuid

from shared.definitions.launch import CONTEXT_NOUN, CREDENTIAL_LAUNCH, ENGINE_NOUN
from shared.enums.scan_context import AuthType
from shared.models.user import User
from shared.services.scan_resolve import redact_command


def context_carries_credentials(context) -> bool:
    auth_type = context.auth_type or AuthType.NONE.value
    return auth_type != AuthType.NONE.value or bool(context.extra_headers)


def credential_option(value: str | None) -> bool:
    return redact_command(value or "") != (value or "")


def engine_carries_credentials(engine) -> bool:
    if getattr(engine, "id", None) is None:
        return False
    if engine.global_headers:
        return True
    return any(credential_option(v) for v in (engine.tool_options or {}).values())


def may_use(
    owner_id: uuid.UUID | None, user_id: uuid.UUID | None, superuser: bool
) -> bool:
    return superuser or (user_id is not None and owner_id == user_id)


def launch_refusal(
    *, engine, context, user_id: uuid.UUID | None, superuser: bool
) -> str | None:
    """Why the user may not launch with this engine and context, or None."""
    if (
        context is not None
        and context_carries_credentials(context)
        and not may_use(context.created_by, user_id, superuser)
    ):
        return CREDENTIAL_LAUNCH.format(noun=CONTEXT_NOUN, name=context.name)
    if (
        engine is not None
        and engine_carries_credentials(engine)
        and not may_use(engine.created_by, user_id, superuser)
    ):
        return CREDENTIAL_LAUNCH.format(noun=ENGINE_NOUN, name=engine.name)
    return None


def plain_tool_options(options: dict | None) -> dict[str, str]:
    """Tool options with every credential-bearing entry left out."""
    return {
        tool: value
        for tool, value in (options or {}).items()
        if not credential_option(value)
    }


async def superuser_of(session, user_id: uuid.UUID | None) -> bool:
    if user_id is None:
        return False
    user = await session.get(User, user_id)
    return bool(user is not None and user.is_active and user.is_superuser)


def superuser_of_sync(session, user_id: uuid.UUID | None) -> bool:
    if user_id is None:
        return False
    user = session.get(User, user_id)
    return bool(user is not None and user.is_active and user.is_superuser)
