"""Look up and record the address a scan's traffic leaves from."""

from __future__ import annotations

import ipaddress
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.definitions.source_ip import (
    FAMILY_ORDER,
    PHASE_ORDER,
    TIMEOUT_SECONDS,
    TRACE_URLS,
    AddressFamily,
    SourceIpFailure,
    SourceIpState,
)
from shared.logging import get_logger
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings

logger = get_logger(__name__)


def lookups_enabled(session: Session | None) -> bool:
    if session is None:
        return False
    value = session.scalar(
        select(InstanceSettings.source_ip_lookups).where(
            InstanceSettings.singleton_key == SINGLETON_KEY
        )
    )
    return True if value is None else bool(value)


def initial(enabled: bool) -> dict:
    state = SourceIpState.MEASURED if enabled else SourceIpState.OFF
    return {"state": state.value, "checks": []}


def wants_check(stored: dict | None, phase: str) -> bool:
    if not stored or stored.get("state") != SourceIpState.MEASURED.value:
        return False
    return all(c.get("phase") != phase for c in stored.get("checks") or [])


def parse_trace(text: str) -> str | None:
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key.strip() != "ip":
            continue
        try:
            return ipaddress.ip_address(value.strip()).compressed
        except ValueError:
            return None
    return None


def failure_of(exc: Exception, *, proxied: bool) -> SourceIpFailure:
    if isinstance(exc, httpx.TimeoutException):
        return SourceIpFailure.TIMEOUT
    if isinstance(exc, (httpx.ProxyError, httpx.UnsupportedProtocol)):
        return SourceIpFailure.PROXY
    if proxied and isinstance(exc, httpx.ConnectError):
        return SourceIpFailure.PROXY
    return SourceIpFailure.UNREACHABLE


def _ask(url: str, proxy: str | None) -> tuple[str | None, SourceIpFailure | None]:
    try:
        with httpx.Client(
            proxy=proxy, timeout=TIMEOUT_SECONDS, trust_env=False
        ) as client:
            response = client.get(url)
    except Exception as exc:
        return None, failure_of(exc, proxied=proxy is not None)
    address = parse_trace(response.text) if response.is_success else None
    if address is None:
        return None, SourceIpFailure.NO_ADDRESS
    return address, None


def lookup(proxy: str | None) -> dict:
    """Ask the trace endpoint over both families at once."""
    with ThreadPoolExecutor(max_workers=len(TRACE_URLS)) as pool:
        answers = dict(
            zip(
                TRACE_URLS,
                pool.map(lambda url: _ask(url, proxy), TRACE_URLS.values()),
                strict=True,
            )
        )
    found: dict[str, str | None] = dict.fromkeys(FAMILY_ORDER)
    for address, _ in answers.values():
        if address is None:
            continue
        family = (
            AddressFamily.IPV6
            if isinstance(ipaddress.ip_address(address), ipaddress.IPv6Address)
            else AddressFamily.IPV4
        )
        found[family.value] = found[family.value] or address
    failure = None
    if not any(found.values()):
        failure = (
            answers[AddressFamily.IPV4.value][1] or SourceIpFailure.UNREACHABLE
        ).value
    return {**found, "failure": failure}


def record(
    stored: dict | None, phase: str, result: dict, *, proxied: bool, at: datetime
) -> dict:
    check = {
        "phase": phase,
        "checked_at": at.isoformat(),
        "proxied": proxied,
        **{family: result.get(family) for family in FAMILY_ORDER},
        "failure": result.get("failure"),
    }
    base = stored or initial(True)
    others = [c for c in base.get("checks") or [] if c.get("phase") != phase]
    checks = sorted([*others, check], key=lambda c: PHASE_ORDER.index(c["phase"]))
    return {**base, "checks": checks}


def addresses(stored: dict | None) -> list[str]:
    """Distinct addresses in phase and family order."""
    seen: list[str] = []
    for check in (stored or {}).get("checks") or []:
        for family in FAMILY_ORDER:
            value = check.get(family)
            if value and value not in seen:
                seen.append(value)
    return seen
