from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from tools.viewdns.models import ViewDNSCacheRead
from tools.viewdns.service import (
    ViewDNSKeyNotConfiguredError,
    ViewDNSLookupError,
    ViewDNSService,
)

router = APIRouter(prefix="/tools/viewdns", tags=["viewdns"])


def get_viewdns_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ViewDNSService:
    return ViewDNSService(session)


@router.get("/ip-history/{domain}", response_model=ViewDNSCacheRead)
async def ip_history(
    domain: str,
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
):
    try:
        return await service.ip_history(domain)
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


@router.get("/reverse-ip/{host}", response_model=ViewDNSCacheRead)
async def reverse_ip(
    host: str,
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
):
    try:
        return await service.reverse_ip(host)
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


@router.get("/reverse-ns/{nameserver}", response_model=ViewDNSCacheRead)
async def reverse_ns(
    nameserver: str,
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
):
    try:
        return await service.reverse_ns(nameserver)
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


@router.get("/reverse-whois", response_model=ViewDNSCacheRead)
async def reverse_whois(
    _current_user: CurrentUser,
    service: Annotated[ViewDNSService, Depends(get_viewdns_service)],
    q: str = Query(
        ..., min_length=1, description="Email, domain, name, or company to search"
    ),
):
    try:
        return await service.reverse_whois(q)
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
