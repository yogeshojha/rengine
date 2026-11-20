from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.access import Access, not_found, project_of
from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.definitions.retention import MEDIA_ROOT
from shared.models.scan import Scan
from shared.services.project_access import may_open

router = APIRouter(
    prefix="/media",
    tags=["media"],
)

_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _scan_of(relative: tuple[str, ...]) -> UUID | None:
    try:
        return UUID(relative[0]) if len(relative) > 1 else None
    except ValueError:
        return None


@router.get("/screenshot")
async def get_screenshot(
    _current_user: CurrentUser,
    access: Access,
    session: Annotated[AsyncSession, Depends(get_session)],
    path: Annotated[str, Query(description="Screenshot path relative to media root")],
):
    candidate = (MEDIA_ROOT / path).resolve()
    if not candidate.is_relative_to(MEDIA_ROOT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path."
        )
    scan_id = _scan_of(candidate.relative_to(MEDIA_ROOT).parts)
    if scan_id is None or not may_open(
        access, await project_of(session, Scan, scan_id)
    ):
        raise not_found(noun="Screenshot")
    media_type = _TYPES.get(candidate.suffix.lower())
    if media_type is None or not candidate.is_file():
        raise not_found(noun="Screenshot")
    return FileResponse(candidate, media_type=media_type)
