from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from tools.ripestat.models import RIPEStatResult
from tools.ripestat.service import RIPEStatLookupError, RIPEStatService

router = APIRouter(prefix="/tools/ripestat", tags=["ripestat"])


def get_ripestat_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RIPEStatService:
    return RIPEStatService(session)


def _handle_lookup_error(e: RIPEStatLookupError):
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"RIPEstat lookup failed: {e}",
    ) from e


@router.get("/prefixes/{asn}", response_model=RIPEStatResult | None)
async def announced_prefixes(
    asn: str,
    _current_user: CurrentUser,
    service: Annotated[RIPEStatService, Depends(get_ripestat_service)],
    cached_only: bool = Query(False),
):
    """Get all prefixes announced by an ASN with BGP visibility timelines."""
    try:
        return await service.announced_prefixes(asn, cached_only=cached_only)
    except RIPEStatLookupError as e:
        _handle_lookup_error(e)


@router.get("/neighbours/{asn}", response_model=RIPEStatResult | None)
async def asn_neighbours(
    asn: str,
    _current_user: CurrentUser,
    service: Annotated[RIPEStatService, Depends(get_ripestat_service)],
    cached_only: bool = Query(False),
):
    """Get upstream, downstream, and peer ASNs."""
    try:
        return await service.asn_neighbours(asn, cached_only=cached_only)
    except RIPEStatLookupError as e:
        _handle_lookup_error(e)


@router.get("/overview/{asn}", response_model=RIPEStatResult | None)
async def as_overview(
    asn: str,
    _current_user: CurrentUser,
    service: Annotated[RIPEStatService, Depends(get_ripestat_service)],
    cached_only: bool = Query(False),
):
    """Get ASN holder name, RIR, and announcement status."""
    try:
        return await service.as_overview(asn, cached_only=cached_only)
    except RIPEStatLookupError as e:
        _handle_lookup_error(e)


@router.get("/network-info/{ip}", response_model=RIPEStatResult | None)
async def network_info(
    ip: str,
    _current_user: CurrentUser,
    service: Annotated[RIPEStatService, Depends(get_ripestat_service)],
    cached_only: bool = Query(False),
):
    """Resolve an IP to its containing prefix and announcing ASN."""
    try:
        return await service.network_info(ip, cached_only=cached_only)
    except RIPEStatLookupError as e:
        _handle_lookup_error(e)


@router.get("/abuse-contact", response_model=RIPEStatResult | None)
async def abuse_contact(
    _current_user: CurrentUser,
    service: Annotated[RIPEStatService, Depends(get_ripestat_service)],
    resource: str = Query(..., min_length=1, description="ASN, IP, or prefix"),
    cached_only: bool = Query(False),
):
    """Get abuse contact emails for any resource."""
    try:
        return await service.abuse_contact(resource, cached_only=cached_only)
    except RIPEStatLookupError as e:
        _handle_lookup_error(e)


@router.get("/prefix-overview", response_model=RIPEStatResult | None)
async def prefix_overview(
    _current_user: CurrentUser,
    service: Annotated[RIPEStatService, Depends(get_ripestat_service)],
    prefix: str = Query(
        ..., min_length=1, description="CIDR prefix, e.g. 49.244.0.0/18"
    ),
    cached_only: bool = Query(False),
):
    """Get which ASNs announce a given prefix."""
    try:
        return await service.prefix_overview(prefix, cached_only=cached_only)
    except RIPEStatLookupError as e:
        _handle_lookup_error(e)


@router.get("/related-prefixes", response_model=RIPEStatResult | None)
async def related_prefixes(
    _current_user: CurrentUser,
    service: Annotated[RIPEStatService, Depends(get_ripestat_service)],
    prefix: str = Query(..., min_length=1, description="CIDR prefix"),
    cached_only: bool = Query(False),
):
    """Get overlapping and hierarchically related prefixes."""
    try:
        return await service.related_prefixes(prefix, cached_only=cached_only)
    except RIPEStatLookupError as e:
        _handle_lookup_error(e)
