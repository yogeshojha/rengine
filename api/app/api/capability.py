from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.instance_settings import InstanceSettingsService
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS, CAP_PROGRAM_WATCHES

_REFUSAL = {
    CAP_BOUNTY_PROGRAMS: "Bug bounty programs require bug bounty mode.",
    CAP_PROGRAM_WATCHES: "Program watches require bug bounty mode.",
}


async def require_capability(session: AsyncSession, cap: str) -> None:
    if not await InstanceSettingsService(session).has_capability(cap):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_REFUSAL[cap])
