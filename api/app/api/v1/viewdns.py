from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from app.core.ratelimit import record_failure, too_many_attempts
from shared.models.user import User
from tools.viewdns.models import ViewDNSCacheRead
from tools.viewdns.service import (
    ViewDNSKeyNotConfiguredError,
    ViewDNSLookupError,
    ViewDNSService,
)

router = APIRouter(prefix="/tools/viewdns", tags=["viewdns"])

_LOOKUP_LIMIT = 30
_LOOKUP_WINDOW_SECONDS = 60


async def _throttle_lookup(user: User, lookup: str) -> None:
    key = f"viewdns:lookup:{lookup}:{user.id}"
    await too_many_attempts(key, limit=_LOOKUP_LIMIT)
    await record_failure(key, window_seconds=_LOOKUP_WINDOW_SECONDS)


def get_viewdns_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ViewDNSService:
    return ViewDNSService(session)


@router.get("/ip-history/{domain}", response_model=ViewDNSCacheRead | None)
async def ip_history(
    domain: str,
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
    cached_only: bool = Query(
        False, description="If true, return only cached data without making an API call"
    ),
):
    if not cached_only:
        await _throttle_lookup(_current_user, "ip_history")
    try:
        return await service.ip_history(domain, cached_only=cached_only)
    except ViewDNSKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=str(e),
        ) from e
    except ViewDNSLookupError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ViewDNS lookup failed: {e}",
        ) from e


@router.get("/reverse-ip/{host}", response_model=ViewDNSCacheRead | None)
async def reverse_ip(
    host: str,
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
    cached_only: bool = Query(
        False, description="If true, return only cached data without making an API call"
    ),
):
    if not cached_only:
        await _throttle_lookup(_current_user, "reverse_ip")
    try:
        return await service.reverse_ip(host, cached_only=cached_only)
    except ViewDNSKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=str(e),
        ) from e
    except ViewDNSLookupError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ViewDNS lookup failed: {e}",
        ) from e


@router.get("/reverse-ns/{nameserver}", response_model=ViewDNSCacheRead | None)
async def reverse_ns(
    nameserver: str,
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
    cached_only: bool = Query(
        False, description="If true, return only cached data without making an API call"
    ),
):
    if not cached_only:
        await _throttle_lookup(_current_user, "reverse_ns")
    try:
        return await service.reverse_ns(nameserver, cached_only=cached_only)
    except ViewDNSKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=str(e),
        ) from e
    except ViewDNSLookupError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ViewDNS lookup failed: {e}",
        ) from e


@router.get("/reverse-whois", response_model=ViewDNSCacheRead | None)
async def reverse_whois(
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
    q: str = Query(
        ..., min_length=1, description="Email, domain, name, or company to search"
    ),
    cached_only: bool = Query(
        False, description="If true, return only cached data without making an API call"
    ),
):
    if not cached_only:
        await _throttle_lookup(_current_user, "reverse_whois")
    try:
        return await service.reverse_whois(q, cached_only=cached_only)
    except ViewDNSKeyNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=str(e),
        ) from e
    except ViewDNSLookupError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ViewDNS lookup failed: {e}",
        ) from e
