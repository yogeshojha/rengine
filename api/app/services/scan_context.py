import ipaddress
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.scan_context import (
    AUTH_TYPES,
    HTTP_PROTOCOLS,
    MULTIPLIERS,
    VALID_RATE_TOOLS,
    AuthConfig,
    AuthHeader,
    ScanContext,
    ScanContextCreate,
    ScanContextRead,
    ScanContextUpdate,
)
from shared.services.scan_resolve import (
    _SENSITIVE_HEADER,
    MASK,
    _auth_summary,
    _mask_auth,
    _mask_headers,
    _reject_ctrl,
)
from shared.utils.datetime import utc_now

# Secret fields kept per auth_type; off-type secrets are stripped on write so
# stale plaintext credentials never linger at rest after a type switch.
_AUTH_KEEP = {
    "none": set(),
    "bearer": {"bearer_token"},
    "basic": {"basic_username", "basic_password"},
    "header": {"header_name", "header_value"},
    "cookie": {"cookie_value"},
    "api_key": {"api_key_name", "api_key_value"},
}


def _to_read(ctx: ScanContext) -> ScanContextRead:
    masked_auth = _mask_auth(ctx.auth or {})
    masked_headers = _mask_headers(ctx.extra_headers or [])
    return ScanContextRead(
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
        compare_baseline_scan_id=ctx.compare_baseline_scan_id,
        scan_only_new_assets=ctx.scan_only_new_assets,
        created_at=ctx.created_at,
        updated_at=ctx.updated_at,
        last_used_at=ctx.last_used_at,
        last_used_scan_id=ctx.last_used_scan_id,
    )


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


_MAX_LIST_ITEMS = 1000
_MAX_ITEM_LEN = 2048
_MIN_RATE = 1
_MAX_RATE = 10000


def _validate_list_caps(name: str, items: list) -> None:
    """Cap list length and per-element string length to stop a single writer from
    persisting a multi-MB blob that is re-serialized on every scan read/preview."""
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
        msg = f"Invalid {name}. Must be an integer between 1 and 10000."
        raise _bad(msg)
    if value < _MIN_RATE or value > _MAX_RATE:
        msg = f"Invalid {name}. Must be between 1 and 10000."
        raise _bad(msg)


def _validate_per_tool(overrides: dict) -> None:
    for tool, val in (overrides or {}).items():
        if tool not in VALID_RATE_TOOLS:
            msg = f"Invalid per-tool rate key '{tool}'. Must be one of {', '.join(VALID_RATE_TOOLS)}."
            raise _bad(msg)
        _validate_rate(f"per_tool_rate_overrides[{tool}]", val)


def _validate_paths(paths: list) -> None:
    _validate_list_caps("excluded_paths", paths)
    for p in paths or []:
        if not isinstance(p, str) or not p.startswith("/"):
            msg = f"Excluded path '{p}' must start with '/'."
            raise _bad(msg)
        _reject_ctrl("Excluded path", p)


def _validate_ips(ips: list) -> None:
    _validate_list_caps("excluded_ips", ips)
    for ip in ips or []:
        try:
            ipaddress.ip_network(ip, strict=False)
        except (ValueError, TypeError) as e:
            msg = f"Invalid excluded IP/CIDR '{ip}': {e}"
            raise _bad(msg) from e


def _validate_subdomains(name: str, subs: list) -> None:
    """Cap list size and reject control chars (CRLF/NUL) on subdomain lists, which
    otherwise flow unvalidated into execution_config destined for the worker."""
    _validate_list_caps(name, subs)
    for s in subs or []:
        if not isinstance(s, str):
            msg = f"{name} entries must be strings."
            raise _bad(msg)
        _reject_ctrl(name, s)


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


def _check_baseline_deferred(compare_baseline_scan_id, scan_only_new_assets) -> None:
    if compare_baseline_scan_id is not None or scan_only_new_assets:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Baseline comparison is not available yet.",
        )


def _apply_auth_update(ctx: ScanContext, data: ScanContextUpdate) -> None:
    """Merge incoming auth over stored, dropping None keys (None/omitted keeps the
    stored secret; "" clears it), then prune off-type secrets so stale plaintext
    credentials never linger after a type switch. Mutates ctx in place."""
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
            if key == "auth_type":
                continue
            if value is None:
                continue  # keep stored
            merged[key] = value  # "" clears, value sets
    merged["auth_type"] = new_auth_type
    _validate_auth_type(new_auth_type)
    _validate_auth_fields(merged)
    ctx.auth = _prune_auth(merged, new_auth_type)
    ctx.auth_type = new_auth_type


def _apply_extra_headers_update(ctx: ScanContext, data: ScanContextUpdate) -> None:
    """Replace stored extra_headers with the incoming set, but never let a masked
    value overwrite a stored secret: when an incoming value equals MASK for a
    sensitive-named header, keep the stored value (case-insensitive). Mutates ctx."""
    if data.extra_headers is None:
        return
    _validate_list_caps("extra_headers", data.extra_headers)
    incoming = [h.model_dump() for h in data.extra_headers]
    _validate_extra_headers(incoming)
    stored = {
        (h.get("name") or "").lower(): h.get("value") for h in (ctx.extra_headers or [])
    }
    for h in incoming:
        if h.get("value") == MASK and _SENSITIVE_HEADER.search(h.get("name") or ""):
            prev = stored.get((h.get("name") or "").lower())
            h["value"] = prev if prev is not None else ""
    ctx.extra_headers = incoming


class ScanContextService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        project_id: UUID,
        created_by: UUID,
        data: ScanContextCreate,
    ) -> ScanContextRead:
        _check_baseline_deferred(
            data.compare_baseline_scan_id, data.scan_only_new_assets
        )

        auth = data.auth or AuthConfig()
        auth_type = data.auth_type or auth.auth_type or "none"

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
        _validate_subdomains("excluded_subdomains", data.excluded_subdomains)
        _validate_subdomains("included_subdomains", data.included_subdomains)
        _validate_list_caps("extra_headers", data.extra_headers)
        _validate_auth_fields(auth.model_dump())
        _validate_extra_headers([h.model_dump() for h in data.extra_headers])

        # Strip off-type secrets so only the active type's fields persist.
        auth_dict = _prune_auth(auth.model_dump(), auth_type)

        ctx = ScanContext(
            project_id=project_id,
            created_by=created_by,
            name=data.name,
            description=data.description,
            auth_type=auth_type,
            auth=auth_dict,
            extra_headers=[h.model_dump() for h in data.extra_headers],
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
            compare_baseline_scan_id=data.compare_baseline_scan_id,
            scan_only_new_assets=data.scan_only_new_assets,
        )
        self.session.add(ctx)
        await self.session.commit()
        await self.session.refresh(ctx)
        return _to_read(ctx)

    async def list(self, project_id: UUID) -> list[ScanContextRead]:
        result = await self.session.execute(
            select(ScanContext)
            .where(ScanContext.project_id == project_id)
            .order_by(ScanContext.updated_at.desc())
        )
        contexts = result.scalars().all()
        return [_to_read(c) for c in contexts]

    async def get(self, id: UUID, project_id: UUID) -> ScanContextRead:
        ctx = await self._get_or_404(id, project_id)
        return _to_read(ctx)

    async def update(
        self,
        id: UUID,
        project_id: UUID,
        data: ScanContextUpdate,
    ) -> ScanContextRead:
        ctx = await self._get_or_404(id, project_id)

        # Deferred baseline guard: only reject explicit non-default values.
        if data.compare_baseline_scan_id is not None or data.scan_only_new_assets:
            _check_baseline_deferred(
                data.compare_baseline_scan_id, data.scan_only_new_assets
            )

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
            _validate_subdomains("excluded_subdomains", data.excluded_subdomains)
            ctx.excluded_subdomains = list(data.excluded_subdomains)
        if data.included_subdomains is not None:
            _validate_subdomains("included_subdomains", data.included_subdomains)
            ctx.included_subdomains = list(data.included_subdomains)
        if data.follow_redirects_override is not None:
            ctx.follow_redirects_override = data.follow_redirects_override

        _apply_auth_update(ctx, data)
        _apply_extra_headers_update(ctx, data)

        ctx.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(ctx)
        return _to_read(ctx)

    async def delete(self, id: UUID, project_id: UUID) -> bool:
        ctx = await self._get_or_404(id, project_id)
        await self.session.delete(ctx)
        await self.session.commit()
        return True

    async def duplicate(
        self, id: UUID, project_id: UUID, created_by: UUID
    ) -> ScanContextRead:
        original = await self._get_or_404(id, project_id)

        ctx = ScanContext(
            project_id=project_id,
            created_by=created_by,
            name=f"{original.name} (copy)",
            description=original.description,
            auth_type=original.auth_type,
            auth=dict(original.auth or {}),
            extra_headers=[dict(h) for h in (original.extra_headers or [])],
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
            compare_baseline_scan_id=original.compare_baseline_scan_id,
            scan_only_new_assets=original.scan_only_new_assets,
        )
        self.session.add(ctx)
        await self.session.commit()
        await self.session.refresh(ctx)
        return _to_read(ctx)

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
