from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser

router = APIRouter(
    prefix="/media",
    tags=["media"],
)

_MEDIA_ROOT = Path("/app/scan_media")
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@router.get("/screenshot")
async def get_screenshot(
    _current_user: CurrentUser,
    path: Annotated[str, Query(description="Screenshot path relative to media root")],
):
    candidate = (_MEDIA_ROOT / path).resolve()
    if not candidate.is_relative_to(_MEDIA_ROOT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path"
        )
    if candidate.suffix.lower() not in _ALLOWED_SUFFIXES or not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not found"
        )
    return FileResponse(candidate, media_type="image/png")
