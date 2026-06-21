from __future__ import annotations

import base64
import re
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field, PrivateAttr

if TYPE_CHECKING:
    from fastapi import HTTPException

MASK = "••••••••"

SECRET_FIELDS = {
    "bearer_token",
    "basic_password",
    "header_value",
    "cookie_value",
    "api_key_value",
}

_SENSITIVE_HEADER = re.compile(
    r"^(authorization|cookie|x-api-key)$|token|secret", re.IGNORECASE
)

_CTRL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

_MAX_RATE = 10000
_MAX_THREADS = 1000
_MAX_TIMEOUT = 3600


def _bad(detail: str) -> HTTPException:
    from fastapi import HTTPException, status  # noqa: PLC0415

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _reject_ctrl(label: str, value) -> None:
    if isinstance(value, str) and _CTRL_CHARS.search(value):
        msg = f"{label} must not contain control characters (CR/LF/NUL)."
        raise _bad(msg)


def _mask_auth(auth: dict) -> dict:
    masked = dict(auth or {})
    for field in SECRET_FIELDS:
        if masked.get(field):
            masked[field] = MASK
    return masked


def _mask_headers(headers: list) -> list:
    out = []
    for h in headers or []:
        name = h.get("name", "")
        value = h.get("value", "")
        if value and _SENSITIVE_HEADER.search(name):
            value = MASK
        out.append({"name": name, "value": value})
    return out


def _auth_summary(auth: dict, extra_headers: list) -> str:  # noqa: PLR0911
    auth = auth or {}
    auth_type = auth.get("auth_type", "none")
    if auth_type == "bearer":
        return "Bearer ••••"
    if auth_type == "basic":
        user = auth.get("basic_username") or ""
        return f"Basic ({user})" if user else "Basic"
    if auth_type == "cookie":
        return "Cookie ••••"
    if auth_type == "header":
        return auth.get("header_name") or "Header"
    if auth_type == "api_key":
        return auth.get("api_key_name") or "API Key"
    n = len(extra_headers or [])
    if n:
        return f"{n} header{'s' if n != 1 else ''}"
    return "None"


def resolve_headers(ctx_or_auth, extra_headers: list | None = None) -> dict[str, str]:
    def _get(key: str):
        if isinstance(ctx_or_auth, dict):
            return ctx_or_auth.get(key)
        return getattr(ctx_or_auth, key, None)

    auth_type = _get("auth_type") or "none"
    headers: dict[str, str] = {}

    if auth_type == "bearer":
        token = _get("bearer_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic":
        user = _get("basic_username") or ""
        password = _get("basic_password") or ""
        raw = f"{user}:{password}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode()
    elif auth_type == "header":
        name = _get("header_name")
        value = _get("header_value")
        if name:
            headers[name] = value or ""
    elif auth_type == "cookie":
        cookie = _get("cookie_value")
        if cookie:
            headers["Cookie"] = cookie
    elif auth_type == "api_key":
        name = _get("api_key_name")
        value = _get("api_key_value")
        if name:
            headers[name] = value or ""

    lower_map = {k.lower(): k for k in headers}
    for h in extra_headers or []:
        if isinstance(h, dict):
            name = h.get("name")
            value = h.get("value", "")
        else:
            name = getattr(h, "name", None)
            value = getattr(h, "value", "")
        if not name:
            continue
        existing = lower_map.get(name.lower())
        if existing is not None:
            del headers[existing]
        headers[name] = value
        lower_map[name.lower()] = name

    return headers


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


class _NeutralContext:
    auth: ClassVar[dict] = {"auth_type": "none"}
    extra_headers: ClassVar[list] = []
    global_rate_limit_override = None
    per_tool_rate_overrides: ClassVar[dict] = {}
    thread_multiplier = 1.0
    timeout_multiplier = 1.0
    excluded_subdomains: ClassVar[list] = []
    excluded_paths: ClassVar[list] = []
    excluded_ips: ClassVar[list] = []
    included_subdomains: ClassVar[list] = []
    follow_redirects_override = None
    http_protocol = "both"
    compare_baseline_scan_id = None
    scan_only_new_assets = False


class ResolvedScanConfig(BaseModel):
    target_value: str
    target_type: str
    headers: dict[str, str] = Field(default_factory=dict)
    per_tool_rate_limits: dict[str, int] = Field(default_factory=dict)
    global_rate_limit_ceiling: int | None = None
    global_threads: int = 30
    resolved_threads: dict[str, int] = Field(default_factory=dict)
    resolved_timeouts: dict[str, int] = Field(default_factory=dict)
    thread_multiplier: float = 1.0
    timeout_multiplier: float = 1.0
    phases: dict = Field(default_factory=dict)
    excluded_subdomains: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)
    excluded_ips: list[str] = Field(default_factory=list)
    included_subdomains: list[str] = Field(default_factory=list)
    follow_redirects: bool | None = None
    http_protocol: str = "both"
    global_http_crawl: bool = True
    intensity: str = "normal"
    proxy_url: str | None = None

    _auth_header_names: list[str] = PrivateAttr(default_factory=list)

    def __repr__(self) -> str:
        proxy = "<set>" if self.proxy_url else "None"
        return (
            f"ResolvedScanConfig(target_value={self.target_value!r}, "
            f"target_type={self.target_type!r}, "
            f"headers=<{len(self.headers)} redacted>, "
            f"global_threads={self.global_threads}, "
            f"http_protocol={self.http_protocol!r}, intensity={self.intensity!r}, "
            f"proxy={proxy})"
        )

    __str__ = __repr__


def _check_baseline_deferred(compare_baseline_scan_id, scan_only_new_assets) -> None:
    if compare_baseline_scan_id is not None or scan_only_new_assets:
        from fastapi import HTTPException, status  # noqa: PLC0415

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Baseline comparison is not available yet.",
        )


def _ctx_get(ctx, key, default=None):
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    return getattr(ctx, key, default)


def _build_headers(engine, ctx) -> tuple[dict[str, str], list[str]]:
    headers: dict[str, str] = {}
    for line in engine.global_headers or []:
        if not isinstance(line, str) or ":" not in line:
            continue
        name, value = line.split(":", 1)
        name = name.strip()
        value = value.strip()
        if name:
            headers[name] = value

    auth = _ctx_get(ctx, "auth") or {"auth_type": "none"}
    extra_headers = _ctx_get(ctx, "extra_headers") or []
    ctx_headers = resolve_headers(auth, extra_headers)

    auth_header_names: list[str] = list(ctx_headers.keys())

    lower_map = {k.lower(): k for k in headers}
    for name, value in ctx_headers.items():
        existing = lower_map.get(name.lower())
        if existing is not None:
            del headers[existing]
        headers[name] = value
        lower_map[name.lower()] = name

    for k, v in headers.items():
        _reject_ctrl("Header name", k)
        _reject_ctrl("Header value", v)

    return headers, auth_header_names


def _resolve_rate(engine_base: int, tool: str, ctx) -> int:
    per_tool = _ctx_get(ctx, "per_tool_rate_overrides") or {}
    global_override = _ctx_get(ctx, "global_rate_limit_override")
    val = per_tool.get(tool, engine_base)
    if global_override is not None:
        val = min(val, global_override)
    return _clamp(int(val), 1, _MAX_RATE)


def merge_engine_context(
    engine, context, target_value: str, target_type: str, proxy_url: str | None = None
) -> ResolvedScanConfig:
    from shared.models.scan_context import VALID_RATE_TOOLS  # noqa: PLC0415
    from shared.models.scan_engine import (  # noqa: PLC0415
        DepthConfig,
        DiscoveryConfig,
        ExpansionConfig,
    )

    ctx = context if context is not None else _NeutralContext()

    _check_baseline_deferred(
        _ctx_get(ctx, "compare_baseline_scan_id"),
        _ctx_get(ctx, "scan_only_new_assets"),
    )

    discovery = DiscoveryConfig(**(engine.discovery or {}))
    expansion = ExpansionConfig(**(engine.expansion or {}))
    depth = DepthConfig(**(engine.depth or {}))

    thread_mult = float(_ctx_get(ctx, "thread_multiplier", 1.0))
    timeout_mult = float(_ctx_get(ctx, "timeout_multiplier", 1.0))

    headers, auth_header_names = _build_headers(engine, ctx)

    per_tool_rate_limits = {
        tool: _resolve_rate(base, tool, ctx)
        for tool, base in zip(
            VALID_RATE_TOOLS,
            (
                expansion.port_scan_rate_limit,
                depth.dir_fuzz_rate_limit,
                depth.nuclei_rate_limit,
            ),
            strict=True,
        )
    }

    global_rate_limit_ceiling = _ctx_get(ctx, "global_rate_limit_override")

    global_threads = _clamp(round(engine.global_threads * thread_mult), 1, _MAX_THREADS)

    def _thr(base: int) -> int:
        return _clamp(int(base * thread_mult) or 1, 1, _MAX_THREADS)

    def _tmo(base: int) -> int:
        return _clamp(int(base * timeout_mult) or 1, 1, _MAX_TIMEOUT)

    resolved_threads = {
        "dns_threads": _thr(discovery.dns_threads),
        "port_scan_threads": _thr(expansion.port_scan_threads),
        "screenshot_threads": _thr(expansion.screenshot_threads),
        "dir_fuzz_threads": _thr(depth.dir_fuzz_threads),
        "url_threads": _thr(depth.url_threads),
        "nuclei_concurrency": _thr(depth.nuclei_concurrency),
    }

    resolved_timeouts = {
        "dns_timeout": _tmo(discovery.dns_timeout),
        "whois_timeout": _tmo(discovery.whois_timeout),
        "port_scan_timeout": _tmo(expansion.port_scan_timeout),
        "screenshot_timeout": _tmo(expansion.screenshot_timeout),
        "dir_fuzz_timeout": _tmo(depth.dir_fuzz_timeout),
        "nuclei_timeout": _tmo(depth.nuclei_timeout),
    }

    discovery_phase = discovery.model_dump()
    expansion_phase = expansion.model_dump()
    depth_phase = depth.model_dump()

    discovery_phase["dns_threads"] = resolved_threads["dns_threads"]
    discovery_phase["dns_timeout"] = resolved_timeouts["dns_timeout"]
    discovery_phase["whois_timeout"] = resolved_timeouts["whois_timeout"]

    expansion_phase["port_scan_rate_limit"] = per_tool_rate_limits["naabu"]
    expansion_phase["port_scan_threads"] = resolved_threads["port_scan_threads"]
    expansion_phase["port_scan_timeout"] = resolved_timeouts["port_scan_timeout"]
    expansion_phase["screenshot_threads"] = resolved_threads["screenshot_threads"]
    expansion_phase["screenshot_timeout"] = resolved_timeouts["screenshot_timeout"]

    depth_phase["dir_fuzz_rate_limit"] = per_tool_rate_limits["ffuf"]
    depth_phase["dir_fuzz_threads"] = resolved_threads["dir_fuzz_threads"]
    depth_phase["dir_fuzz_timeout"] = resolved_timeouts["dir_fuzz_timeout"]
    depth_phase["url_threads"] = resolved_threads["url_threads"]
    depth_phase["nuclei_rate_limit"] = per_tool_rate_limits["nuclei"]
    depth_phase["nuclei_concurrency"] = resolved_threads["nuclei_concurrency"]
    depth_phase["nuclei_timeout"] = resolved_timeouts["nuclei_timeout"]

    phases = {
        "discovery": discovery_phase,
        "expansion": expansion_phase,
        "depth": depth_phase,
    }

    for phase_name, original in (
        ("discovery", discovery.model_dump()),
        ("expansion", expansion.model_dump()),
        ("depth", depth.model_dump()),
    ):
        for key, val in original.items():
            if isinstance(val, bool) and phases[phase_name][key] != val:
                msg = f"Resolved enable flag {phase_name}.{key} diverged from engine."
                raise RuntimeError(msg)

    excluded_subdomains = list(_ctx_get(ctx, "excluded_subdomains") or [])
    excluded_paths = list(_ctx_get(ctx, "excluded_paths") or [])
    excluded_ips = list(_ctx_get(ctx, "excluded_ips") or [])
    included_subdomains = list(_ctx_get(ctx, "included_subdomains") or [])

    follow_redirects_override = _ctx_get(ctx, "follow_redirects_override")
    follow_redirects = (
        follow_redirects_override if follow_redirects_override is not None else None
    )
    http_protocol = _ctx_get(ctx, "http_protocol", "both") or "both"

    config = ResolvedScanConfig(
        target_value=target_value,
        target_type=target_type,
        headers=headers,
        per_tool_rate_limits=per_tool_rate_limits,
        global_rate_limit_ceiling=global_rate_limit_ceiling,
        global_threads=global_threads,
        resolved_threads=resolved_threads,
        resolved_timeouts=resolved_timeouts,
        thread_multiplier=thread_mult,
        timeout_multiplier=timeout_mult,
        phases=phases,
        excluded_subdomains=excluded_subdomains,
        excluded_paths=excluded_paths,
        excluded_ips=excluded_ips,
        included_subdomains=included_subdomains,
        follow_redirects=follow_redirects,
        http_protocol=http_protocol,
        global_http_crawl=engine.global_http_crawl,
        intensity=engine.intensity,
    )
    config._auth_header_names = auth_header_names
    config.proxy_url = proxy_url
    return config
