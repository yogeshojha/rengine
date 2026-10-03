import ipaddress
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.launch import CONTEXT_NOUN, CREDENTIAL_CHANGE
from shared.enums.scan import SCAN_OPEN_STATUSES
from shared.enums.scan_context import AuthType
from shared.models.proxy import Proxy
from shared.models.scan import Scan
from shared.models.scan_context import (
    AUTH_TYPES,
    HTTP_PROTOCOLS,
    MULTIPLIERS,
    AuthConfig,
    AuthHeader,
    ContextUsage,
    ScanContext,
    ScanContextCreate,
    ScanContextRead,
    ScanContextUpdate,
)
from shared.models.scan_schedule import ScanSchedule
from shared.models.user import User
from shared.services.credential_access import context_carries_credentials, may_use
from shared.services.scan_resolve import (
    MASK,
    SECRET_FIELDS,
    _auth_summary,
    _mask_auth,
    _mask_headers,
    _reject_ctrl,
    restore_masked_headers,
)
from shared.services.scope_filter import looks_like_domain, pattern_hazard
from shared.utils.datetime import utc_now
from stages.registry import rate_tools

_AUTH_KEEP = {
    AuthType.NONE.value: set(),
    AuthType.BEARER.value: {"bearer_token"},
    AuthType.BASIC.value: {"basic_username", "basic_password"},
    AuthType.HEADER.value: {"header_name", "header_value"},
    AuthType.COOKIE.value: {"cookie_value"},
    AuthType.API_KEY.value: {"api_key_name", "api_key_value"},
}


async def usage_counts[U: BaseModel](
    session: AsyncSession, column: str, ids: list[UUID], usage: type[U]
) -> dict[UUID, U]:
    """Schedules and scans per value of the named column."""
    out = {i: usage() for i in ids}
    if not ids:
        return out
    for model, field in ((ScanSchedule, "schedules"), (Scan, "scans")):
        key = getattr(model, column)
        rows = await session.execute(
            select(key, func.count()).where(key.in_(ids)).group_by(key)
        )
        for value, count in rows.all():
            setattr(out[value], field, count)
    return out


async def _usage_for(
    session: AsyncSession, context_ids: list[UUID]
) -> dict[UUID, ContextUsage]:
    return await usage_counts(session, "context_id", context_ids, ContextUsage)


def _to_read(ctx: ScanContext, usage: ContextUsage | None = None) -> ScanContextRead:
    masked_auth = _mask_auth(ctx.auth or {})
    masked_headers = _mask_headers(ctx.extra_headers or [])
    return ScanContextRead(
        usage=usage or ContextUsage(),
        id=ctx.id,
        project_id=ctx.project_id,
        created_by=ctx.created_by,
        name=ctx.name,
        description=ctx.description,
        auth_type=ctx.auth_type,
        auth=AuthConfig(**masked_auth),
        auth_summary=_auth_summary(ctx.auth or {}, ctx.extra_headers or []),
        extra_headers=[AuthHeader(**h) for h in masked_headers],
        global_rate_limit_override=ctx.global_rate_limit_override,
        per_tool_rate_overrides=ctx.per_tool_rate_overrides or {},
        thread_multiplier=ctx.thread_multiplier,
        timeout_multiplier=ctx.timeout_multiplier,
        excluded_subdomains=ctx.excluded_subdomains or [],
        excluded_paths=ctx.excluded_paths or [],
        excluded_ips=ctx.excluded_ips or [],
        included_subdomains=ctx.included_subdomains or [],
        follow_redirects_override=ctx.follow_redirects_override,
        http_protocol=ctx.http_protocol,
        proxy_id=ctx.proxy_id,
        created_at=ctx.created_at,
        updated_at=ctx.updated_at,
        last_used_at=ctx.last_used_at,
        last_used_scan_id=ctx.last_used_scan_id,
        carries_credentials=context_carries_credentials(ctx),
    )


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


_PROXY_ADMIN = "Setting a proxy requires administrator access."


def _gains_credentials(ctx: ScanContext, data: ScanContextUpdate) -> bool:
    auth_type = data.auth_type or ctx.auth_type or AuthType.NONE.value
    headers = (
        data.extra_headers if data.extra_headers is not None else ctx.extra_headers
    )
    return auth_type != AuthType.NONE.value or bool(headers)


def _check_change(
    ctx: ScanContext, actor: User | None, data: ScanContextUpdate | None = None
) -> None:
    if actor is None or may_use(ctx.created_by, actor.id, actor.is_superuser):
        return
    if context_carries_credentials(ctx) or (
        data is not None and _gains_credentials(ctx, data)
    ):
        raise _forbidden(CREDENTIAL_CHANGE.format(noun=CONTEXT_NOUN, name=ctx.name))


_MAX_LIST_ITEMS = 1000
_MAX_ITEM_LEN = 2048
_MIN_RATE = 1
_MAX_RATE = 10000


def _validate_list_caps(name: str, items: list) -> None:
    if items is None:
        return
    if len(items) > _MAX_LIST_ITEMS:
        msg = f"{name} may not exceed {_MAX_LIST_ITEMS} entries."
        raise _bad(msg)
    for item in items:
        if isinstance(item, str) and len(item) > _MAX_ITEM_LEN:
            msg = f"{name} entries may not exceed {_MAX_ITEM_LEN} characters."
            raise _bad(msg)


def _validate_auth_type(auth_type: str) -> None:
    if auth_type not in AUTH_TYPES:
        msg = f"Invalid auth_type. Must be one of {', '.join(AUTH_TYPES)}."
        raise _bad(msg)


def _validate_http_protocol(proto: str) -> None:
    if proto not in HTTP_PROTOCOLS:
        msg = f"Invalid http_protocol. Must be one of {', '.join(HTTP_PROTOCOLS)}."
        raise _bad(msg)


def _validate_multiplier(name: str, value: float) -> None:
    if value not in MULTIPLIERS:
        msg = (
            f"Invalid {name}. Must be one of {', '.join(str(m) for m in MULTIPLIERS)}."
        )
        raise _bad(msg)


def _validate_rate(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"Invalid {name}. Must be an integer between {_MIN_RATE} and {_MAX_RATE}."
        raise _bad(msg)
    if value < _MIN_RATE or value > _MAX_RATE:
        msg = f"Invalid {name}. Must be between {_MIN_RATE} and {_MAX_RATE}."
        raise _bad(msg)


def _validate_per_tool(overrides: dict) -> None:
    for tool, val in (overrides or {}).items():
        allowed = rate_tools()
        if tool not in allowed:
            msg = f"Invalid per-tool rate key '{tool}'. Must be one of {', '.join(allowed)}."
            raise _bad(msg)
        _validate_rate(f"per_tool_rate_overrides[{tool}]", val)


def _validate_paths(paths: list) -> None:
    _validate_list_caps("excluded_paths", paths)
    for p in paths or []:
        if not isinstance(p, str) or not p.startswith("/"):
            msg = f"Excluded path '{p}' must start with '/'."
            raise _bad(msg)
        _reject_ctrl("Excluded path", p)
        if hazard := pattern_hazard(p):
            msg = (
                f"'{p}' {hazard}. "
                "Use a prefix such as /admin or a wildcard such as /admin/*."
            )
            raise _bad(msg)


def _validate_ips(ips: list) -> None:
    _validate_list_caps("excluded_ips", ips)
    for ip in ips or []:
        try:
            ipaddress.ip_network(ip, strict=False)
        except (ValueError, TypeError) as e:
            msg = f"Invalid excluded IP/CIDR '{ip}': {e}"
            raise _bad(msg) from e


def _validate_subdomains(name: str, subs: list) -> None:
    _validate_list_caps(name, subs)
    for s in subs or []:
        if not isinstance(s, str):
            msg = f"{name} entries must be strings."
            raise _bad(msg)
        _reject_ctrl(name, s)


def _validate_exclusion_patterns(name: str, patterns: list) -> None:
    _validate_list_caps(name, patterns)
    for p in patterns or []:
        if not isinstance(p, str):
            msg = f"{name} entries must be strings."
            raise _bad(msg)
        _reject_ctrl(name, p)
        if hazard := pattern_hazard(p):
            msg = (
                f"'{p}' {hazard}. "
                "Use a keyword such as admin or a wildcard such as *admin*."
            )
            raise _bad(msg)
        if looks_like_domain(p):
            msg = (
                f"'{p}' is a domain name. "
                "Use a keyword such as admin, a wildcard such as *admin* or a regex."
            )
            raise _bad(msg)


def _validate_auth_fields(auth: dict) -> None:
    for field in (
        "bearer_token",
        "basic_username",
        "basic_password",
        "header_name",
        "header_value",
        "cookie_value",
        "api_key_name",
        "api_key_value",
    ):
        _reject_ctrl(f"auth.{field}", auth.get(field))


def _validate_extra_headers(headers: list) -> None:
    for h in headers or []:
        name = h.get("name") if isinstance(h, dict) else getattr(h, "name", None)
        value = h.get("value") if isinstance(h, dict) else getattr(h, "value", None)
        _reject_ctrl("Header name", name)
        _reject_ctrl("Header value", value)


def _prune_auth(auth: dict, auth_type: str) -> dict:
    keep = _AUTH_KEEP.get(auth_type, set())
    pruned = {"auth_type": auth_type}
    for key in keep:
        if auth.get(key) is not None:
            pruned[key] = auth[key]
    return pruned


def _apply_auth_update(ctx: ScanContext, data: ScanContextUpdate) -> None:
    new_auth_type = ctx.auth_type
    if data.auth_type is not None:
        _validate_auth_type(data.auth_type)
        new_auth_type = data.auth_type

    if data.auth is None and data.auth_type is None:
        return

    merged = dict(ctx.auth or {})
    if data.auth is not None:
        incoming = data.auth.model_dump()
        for key, value in incoming.items():
            if key == "auth_type" or value is None:
                continue
            if key in SECRET_FIELDS and MASK in str(value):
                continue
            merged[key] = value
    merged["auth_type"] = new_auth_type
    _validate_auth_type(new_auth_type)
    _validate_auth_fields(merged)
    ctx.auth = _prune_auth(merged, new_auth_type)
    ctx.auth_type = new_auth_type


def _apply_extra_headers_update(ctx: ScanContext, data: ScanContextUpdate) -> None:
    if data.extra_headers is None:
        return
    _validate_list_caps("extra_headers", data.extra_headers)
    incoming = [h.model_dump() for h in data.extra_headers]
    _validate_extra_headers(incoming)
    ctx.extra_headers = restore_masked_headers(incoming, ctx.extra_headers)


class ScanContextService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _validate_proxy_id(self, proxy_id: UUID | None) -> None:
        if proxy_id is None:
            return
        if await self.session.get(Proxy, proxy_id) is None:
            msg = "Proxy not found."
            raise _bad(msg)

    async def create(
        self,
        project_id: UUID,
        created_by: UUID,
        data: ScanContextCreate,
        actor: User | None = None,
    ) -> ScanContextRead:
        auth = data.auth or AuthConfig()
        auth_type = data.auth_type or auth.auth_type or AuthType.NONE.value

        _validate_auth_type(auth_type)
        _validate_http_protocol(data.http_protocol)
        _validate_multiplier("thread_multiplier", data.thread_multiplier)
        _validate_multiplier("timeout_multiplier", data.timeout_multiplier)
        if data.global_rate_limit_override is not None:
            _validate_rate(
                "global_rate_limit_override", data.global_rate_limit_override
            )
        _validate_per_tool(data.per_tool_rate_overrides)
        _validate_paths(data.excluded_paths)
        _validate_ips(data.excluded_ips)
        _validate_exclusion_patterns("excluded_subdomains", data.excluded_subdomains)
        _validate_subdomains("included_subdomains", data.included_subdomains)
        _validate_list_caps("extra_headers", data.extra_headers)
        _validate_auth_fields(auth.model_dump())
        _validate_extra_headers([h.model_dump() for h in data.extra_headers])
        await self._validate_proxy_id(data.proxy_id)
        proxy_id = data.proxy_id
        if "proxy_id" not in data.model_fields_set:
            proxy_id = await self._default_proxy_id()
        elif (
            actor is not None
            and not actor.is_superuser
            and proxy_id != await self._default_proxy_id()
        ):
            raise _forbidden(_PROXY_ADMIN)

        auth_dict = _prune_auth(auth.model_dump(), auth_type)

        ctx = ScanContext(
            project_id=project_id,
            created_by=created_by,
            name=data.name,
            description=data.description,
            auth_type=auth_type,
            auth=auth_dict,
            extra_headers=restore_masked_headers(
                [h.model_dump() for h in data.extra_headers], []
            ),
            global_rate_limit_override=data.global_rate_limit_override,
            per_tool_rate_overrides=dict(data.per_tool_rate_overrides),
            thread_multiplier=data.thread_multiplier,
            timeout_multiplier=data.timeout_multiplier,
            excluded_subdomains=list(data.excluded_subdomains),
            excluded_paths=list(data.excluded_paths),
            excluded_ips=list(data.excluded_ips),
            included_subdomains=list(data.included_subdomains),
            follow_redirects_override=data.follow_redirects_override,
            http_protocol=data.http_protocol,
            proxy_id=proxy_id,
        )
        self.session.add(ctx)
        await self.session.commit()
        await self.session.refresh(ctx)
        return _to_read(ctx)

    async def _default_proxy_id(self) -> UUID | None:
        result = await self.session.execute(
            select(Proxy.id).where(
                Proxy.is_default.is_(True), Proxy.is_active.is_(True)
            )
        )
        return result.scalars().first()

    async def list(self, project_id: UUID) -> list[ScanContextRead]:
        result = await self.session.execute(
            select(ScanContext)
            .where(ScanContext.project_id == project_id)
            .order_by(ScanContext.updated_at.desc())
        )
        contexts = list(result.scalars().all())
        usage = await _usage_for(self.session, [c.id for c in contexts])
        return [_to_read(c, usage.get(c.id)) for c in contexts]

    async def get(self, id: UUID, project_id: UUID) -> ScanContextRead:
        ctx = await self._get_or_404(id, project_id)
        usage = await _usage_for(self.session, [ctx.id])
        return _to_read(ctx, usage.get(ctx.id))

    async def update(
        self,
        id: UUID,
        project_id: UUID,
        data: ScanContextUpdate,
        actor: User | None = None,
    ) -> ScanContextRead:
        ctx = await self._get_or_404(id, project_id)
        _check_change(ctx, actor, data)
        if (
            actor is not None
            and not actor.is_superuser
            and data.proxy_id is not None
            and data.proxy_id != ctx.proxy_id
        ):
            raise _forbidden(_PROXY_ADMIN)

        if data.name is not None:
            ctx.name = data.name
        if data.description is not None:
            ctx.description = data.description

        if data.http_protocol is not None:
            _validate_http_protocol(data.http_protocol)
            ctx.http_protocol = data.http_protocol
        if data.thread_multiplier is not None:
            _validate_multiplier("thread_multiplier", data.thread_multiplier)
            ctx.thread_multiplier = data.thread_multiplier
        if data.timeout_multiplier is not None:
            _validate_multiplier("timeout_multiplier", data.timeout_multiplier)
            ctx.timeout_multiplier = data.timeout_multiplier
        if data.global_rate_limit_override is not None:
            _validate_rate(
                "global_rate_limit_override", data.global_rate_limit_override
            )
            ctx.global_rate_limit_override = data.global_rate_limit_override
        if data.per_tool_rate_overrides is not None:
            _validate_per_tool(data.per_tool_rate_overrides)
            ctx.per_tool_rate_overrides = dict(data.per_tool_rate_overrides)
        if data.excluded_paths is not None:
            _validate_paths(data.excluded_paths)
            ctx.excluded_paths = list(data.excluded_paths)
        if data.excluded_ips is not None:
            _validate_ips(data.excluded_ips)
            ctx.excluded_ips = list(data.excluded_ips)
        if data.excluded_subdomains is not None:
            _validate_exclusion_patterns(
                "excluded_subdomains", data.excluded_subdomains
            )
            ctx.excluded_subdomains = list(data.excluded_subdomains)
        if data.included_subdomains is not None:
            _validate_subdomains("included_subdomains", data.included_subdomains)
            ctx.included_subdomains = list(data.included_subdomains)
        if data.follow_redirects_override is not None:
            ctx.follow_redirects_override = data.follow_redirects_override
        if data.proxy_id is not None:
            await self._validate_proxy_id(data.proxy_id)
            ctx.proxy_id = data.proxy_id

        _apply_auth_update(ctx, data)
        _apply_extra_headers_update(ctx, data)

        ctx.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(ctx)
        return _to_read(ctx)

    async def delete(
        self, id: UUID, project_id: UUID, actor: User | None = None
    ) -> bool:
        ctx = await self._get_or_404(id, project_id)
        _check_change(ctx, actor)
        running = (
            await self.session.execute(
                select(func.count())
                .select_from(Scan)
                .where(Scan.context_id == ctx.id, Scan.status.in_(SCAN_OPEN_STATUSES))
            )
        ).scalar_one()
        if running:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"'{ctx.name}' is in use by {running} running "
                    f"scan{'s' if running != 1 else ''}. Cancel them first."
                ),
            )
        usage = (await _usage_for(self.session, [ctx.id]))[ctx.id]
        if usage.schedules:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"'{ctx.name}' is used by {usage.schedules} scheduled "
                    f"scan{'s' if usage.schedules != 1 else ''}. "
                    "Detach or delete those schedules first."
                ),
            )
        await self.session.delete(ctx)
        await self.session.commit()
        return True

    async def duplicate(
        self, id: UUID, project_id: UUID, created_by: UUID, actor: User | None = None
    ) -> ScanContextRead:
        original = await self._get_or_404(id, project_id)
        keep = actor is None or may_use(
            original.created_by, actor.id, actor.is_superuser
        )

        ctx = ScanContext(
            project_id=project_id,
            created_by=created_by,
            name=f"{original.name} (copy)",
            description=original.description,
            auth_type=original.auth_type if keep else AuthType.NONE.value,
            auth=dict(original.auth or {})
            if keep
            else {"auth_type": AuthType.NONE.value},
            extra_headers=[dict(h) for h in (original.extra_headers or [])]
            if keep
            else [],
            global_rate_limit_override=original.global_rate_limit_override,
            per_tool_rate_overrides=dict(original.per_tool_rate_overrides or {}),
            thread_multiplier=original.thread_multiplier,
            timeout_multiplier=original.timeout_multiplier,
            excluded_subdomains=list(original.excluded_subdomains or []),
            excluded_paths=list(original.excluded_paths or []),
            excluded_ips=list(original.excluded_ips or []),
            included_subdomains=list(original.included_subdomains or []),
            follow_redirects_override=original.follow_redirects_override,
            http_protocol=original.http_protocol,
            proxy_id=original.proxy_id,
        )
        self.session.add(ctx)
        await self.session.commit()
        await self.session.refresh(ctx)
        return _to_read(ctx)

    async def set_rate_limit(
        self, id: UUID, project_id: UUID, rate: int | None
    ) -> None:
        ctx = await self.session.get(ScanContext, id)
        if ctx is None or ctx.project_id != project_id:
            return
        if rate is not None:
            _validate_rate("global_rate_limit_override", rate)
        ctx.global_rate_limit_override = rate
        ctx.updated_at = utc_now()
        await self.session.flush()

    async def touch(
        self, id: UUID, project_id: UUID, scan_id: UUID | None = None
    ) -> None:
        ctx = await self._get_or_404(id, project_id)
        ctx.last_used_at = utc_now()
        if scan_id is not None:
            ctx.last_used_scan_id = scan_id
        await self.session.commit()

    async def _get_or_404(self, id: UUID, project_id: UUID) -> ScanContext:
        result = await self.session.execute(
            select(ScanContext).where(
                ScanContext.id == id,
                ScanContext.project_id == project_id,
            )
        )
        ctx = result.scalar_one_or_none()
        if not ctx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan context not found",
            )
        return ctx
