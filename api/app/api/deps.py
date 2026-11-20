from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.client_ip import client_id
from app.core.database import async_db_session, get_session
from app.core.ratelimit import is_token_revoked, tokens_valid_after
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    ISSUED_MS_CLAIM,
    TOKEN_TYPE_ACCESS,
    decode_token,
)
from app.services import access_keys
from shared.definitions.access_keys import (
    ACCESS_KEY_PREFIX,
    READ_ONLY_DETAIL,
    REFUSED_DETAIL,
    KeyRule,
    allows,
    key_rule,
)
from shared.models.access_key import AccessKey
from shared.models.user import User
from shared.services.credential_access import hold_as_key

security = HTTPBearer(auto_error=False, bearerFormat="JWT")

BEARER_HEADERS = {"WWW-Authenticate": "Bearer"}


async def get_token_from_request(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
) -> str:
    if credentials:
        return credentials.credentials

    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers=BEARER_HEADERS,
        )

    return token


async def resolve_user(token: str, session: AsyncSession) -> User:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers=BEARER_HEADERS,
        )

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
            headers=BEARER_HEADERS,
        )

    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
            headers=BEARER_HEADERS,
        )

    return await user_for_payload(payload, session)


async def revoked_since_issue(user_id: UUID, issued: object) -> bool:
    """True when the user's sessions were revoked after the token was issued."""
    cutoff = await tokens_valid_after(user_id)
    return cutoff is not None and (not isinstance(issued, int) or issued < cutoff)


async def user_for_payload(payload: dict, session: AsyncSession) -> User:
    """The account a validated token names."""
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers=BEARER_HEADERS,
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token.",
            headers=BEARER_HEADERS,
        ) from e

    if await revoked_since_issue(user_id, payload.get(ISSUED_MS_CLAIM)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
            headers=BEARER_HEADERS,
        )

    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers=BEARER_HEADERS,
        )
    return user


def ensure_active(user: User) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    return user


# ---------- access keys ----------

_KEY_STATE = "access_key"
_ROUTES_STATE = "key_routes"


def presented_key(request: Request) -> str | None:
    """The access key in the Authorization header, if one is sent."""
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    value = value.strip()
    if scheme.lower() == "bearer" and value.startswith(ACCESS_KEY_PREFIX):
        return value
    return None


@dataclass(frozen=True)
class RouteFacts:
    path: str
    gated: bool
    regex: Any = None


def _dependency_calls(dependant: Any) -> set[Any]:
    found: set[Any] = set()
    stack = list(dependant.dependencies)
    while stack:
        dependency = stack.pop()
        found.add(dependency.call)
        stack.extend(dependency.dependencies)
    return found


def served_routes(app: Any) -> list[Any]:
    """Every route the app serves, each with its full path."""
    found = []
    for route in app.routes:
        contexts = getattr(route, "effective_route_contexts", None)
        found.extend(contexts() if contexts else [route])
    return [r for r in found if getattr(r, "dependant", None) is not None]


def route_facts(route: Any, prefix: str) -> RouteFacts:
    calls = _dependency_calls(route.dependant)
    return RouteFacts(
        path=route.path.removeprefix(prefix) or "/",
        gated=bool(calls & {get_current_superuser, get_stream_user}),
        regex=getattr(route, "path_regex", None),
    )


def _route_index(app: Any) -> dict[int, list[RouteFacts]]:
    from app.config import API_V1_PREFIX  # noqa: PLC0415

    index: dict[int, list[RouteFacts]] = {}
    for route in served_routes(app):
        original = getattr(route, "original_route", route)
        index.setdefault(id(original), []).append(route_facts(route, API_V1_PREFIX))
    return index


def _facts_of(request: Request) -> RouteFacts | None:
    index = getattr(request.app.state, _ROUTES_STATE, None)
    if index is None:
        index = _route_index(request.app)
        setattr(request.app.state, _ROUTES_STATE, index)
    candidates = index.get(id(request.scope.get("route")), [])
    if len(candidates) > 1:
        candidates = [
            c for c in candidates if c.regex and c.regex.match(request.url.path)
        ]
    return candidates[0] if len(candidates) == 1 else None


async def _key_holder(
    request: Request, secret: str, session: AsyncSession
) -> tuple[AccessKey, User]:
    held = getattr(request.state, _KEY_STATE, None)
    if held is None:
        held = await access_keys.authenticate(session, secret, client_id(request))
        setattr(request.state, _KEY_STATE, held)
    hold_as_key(session, held[1].id)
    return held


def _check_key(request: Request, key: AccessKey) -> None:
    facts = _facts_of(request)
    rule = (
        key_rule(request.method, facts.path, gated=facts.gated)
        if facts
        else KeyRule.REFUSED
    )
    if not allows(key.access, rule):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=REFUSED_DETAIL if rule is KeyRule.REFUSED else READ_ONLY_DETAIL,
        )


async def access_key_gate(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Authenticate an access key and hold it to what its level may call."""
    secret = presented_key(request)
    if secret is None:
        hold_as_key(session, None)
        return
    key, _ = await _key_holder(request, secret, session)
    _check_key(request, key)


def key_owner(request: Request) -> User | None:
    """The account behind the access key this request carries, if any."""
    held = getattr(request.state, _KEY_STATE, None)
    return held[1] if held else None


def _as_key_holder(user: User) -> User:
    """A detached copy of the owner with no administrator powers."""
    return User.model_validate(user, update={"is_superuser": False})


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(get_token_from_request)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    secret = presented_key(request)
    if secret is not None:
        key, user = await _key_holder(request, secret, session)
        _check_key(request, key)
        return _as_key_holder(user)
    return await resolve_user(token, session)


async def get_stream_user(
    request: Request,
    token: Annotated[str, Depends(get_token_from_request)],
) -> User:
    if presented_key(request) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=REFUSED_DETAIL
        )
    async with async_db_session() as session:
        user = await resolve_user(token, session)
    return ensure_active(user)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return ensure_active(current_user)


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return current_user


async def token_still_valid(token: str) -> bool:
    payload = decode_token(token)
    if payload is None or payload.get("type") != TOKEN_TYPE_ACCESS:
        return False
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        return False
    try:
        async with async_db_session() as session:
            user = await user_for_payload(payload, session)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        return False
    except (SQLAlchemyError, TimeoutError):
        return True
    return user.is_active


CurrentUser = Annotated[User, Depends(get_current_active_user)]
StreamUser = Annotated[User, Depends(get_stream_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
