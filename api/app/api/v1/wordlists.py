from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser
from app.core.database import get_session
from shared.definitions.wordlists import (
    KIND_LABELS,
    MAX_WORDLIST_BYTES,
    WordlistOrigin,
    slugify,
)
from shared.models.wordlist import (
    Wordlist,
    WordlistRead,
    WordlistRejection,
    WordlistUploadRequest,
    WordlistUploadResult,
)
from shared.services.wordlists import (
    WordlistError,
    delete_custom,
    ensure_builtin,
    prepare_custom,
    read_lines,
    resolve_path,
    write_custom,
)
from shared.utils.datetime import utc_now

router = APIRouter(prefix="/wordlists", tags=["wordlists"])


@router.get("", response_model=list[WordlistRead])
async def list_wordlists(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await session.run_sync(ensure_builtin)
    query = select(Wordlist).order_by(Wordlist.origin, Wordlist.name)
    rows = (await session.execute(query)).scalars().all()
    return [WordlistRead.model_validate(row, from_attributes=True) for row in rows]


@router.post(
    "", response_model=WordlistUploadResult, status_code=status.HTTP_201_CREATED
)
async def upload_wordlists(
    current_user: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: WordlistUploadRequest,
):
    kind = body.kind
    if kind not in KIND_LABELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown wordlist kind. Kinds: {', '.join(sorted(KIND_LABELS))}.",
        )
    result = WordlistUploadResult()
    for item in body.files:
        if len(item.content.encode("utf-8", errors="ignore")) > MAX_WORDLIST_BYTES:
            result.rejected.append(
                WordlistRejection(
                    filename=item.filename,
                    reason=f"Larger than the {MAX_WORDLIST_BYTES // (1024 * 1024)} MB limit.",
                )
            )
            continue
        try:
            filename, words = prepare_custom(item.filename, item.content)
        except (WordlistError, OSError) as exc:
            result.rejected.append(
                WordlistRejection(filename=item.filename, reason=str(exc))
            )
            continue

        slug = slugify(item.name or item.filename.rsplit(".", 1)[0]) or "wordlist"
        row = await session.scalar(
            select(Wordlist).where(
                Wordlist.origin == WordlistOrigin.CUSTOM.value,
                Wordlist.filename == filename,
            )
        )
        taken = await session.scalar(
            select(Wordlist).where(Wordlist.slug == slug, Wordlist.filename != filename)
        )
        if taken is not None:
            result.rejected.append(
                WordlistRejection(
                    filename=item.filename,
                    reason=f"The name {slug!r} is used by another wordlist.",
                )
            )
            continue
        try:
            write_custom(filename, words)
        except (WordlistError, OSError) as exc:
            result.rejected.append(
                WordlistRejection(filename=item.filename, reason=str(exc))
            )
            continue

        values = {
            "slug": slug,
            "name": item.name or item.filename,
            "description": item.description or "",
            "origin": WordlistOrigin.CUSTOM.value,
            "kind": kind,
            "filename": filename,
            "words": len(words),
            "bytes": sum(len(w) + 1 for w in words),
            "updated_at": utc_now(),
        }
        if row is None:
            row = Wordlist(uploaded_by=current_user.id, **values)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        result.stored.append(WordlistRead.model_validate(row, from_attributes=True))
    return result


async def _get(session: AsyncSession, wordlist_id: UUID) -> Wordlist:
    row = await session.get(Wordlist, wordlist_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wordlist not found"
        )
    return row


@router.get("/{wordlist_id}/preview", response_model=list[str])
async def preview_wordlist(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    wordlist_id: Annotated[UUID, Path(description="Wordlist ID")],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    row = await _get(session, wordlist_id)
    try:
        path = resolve_path(row)
    except WordlistError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The file for this wordlist is missing.",
        )
    return read_lines(path, limit)


@router.delete("/{wordlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wordlist(
    _admin: CurrentSuperuser,
    session: Annotated[AsyncSession, Depends(get_session)],
    wordlist_id: Annotated[UUID, Path(description="Wordlist ID")],
):
    row = await _get(session, wordlist_id)
    try:
        delete_custom(row)
    except WordlistError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.delete(row)
    await session.commit()
