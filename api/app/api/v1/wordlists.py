from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.definitions.wordlists import (
    KIND_LABELS,
    MAX_WORDLIST_BYTES,
    WordlistKind,
    WordlistOrigin,
    slugify,
)
from shared.models.wordlist import (
    Wordlist,
    WordlistRead,
    WordlistRejection,
    WordlistUpdate,
    WordlistUploadRequest,
    WordlistUploadResult,
)
from shared.services.wordlists import (
    WordlistError,
    clean_words,
    delete_custom,
    resolve_path,
    store_custom,
)
from shared.utils.datetime import utc_now

router = APIRouter(prefix="/wordlists", tags=["wordlists"])


async def _index_builtin(session: AsyncSession) -> None:
    """Shipped lists are indexed on read so the picker never starts empty."""
    from shared.definitions.wordlists import BUILTIN_WORDLISTS  # noqa: PLC0415
    from shared.services.wordlists import builtin_root  # noqa: PLC0415

    root = builtin_root()
    now = utc_now()
    changed = False
    for spec in BUILTIN_WORDLISTS:
        path = root / spec.filename
        if not path.is_file():
            continue
        words = len(clean_words(path.read_text(encoding="utf-8", errors="replace")))
        row = await session.scalar(select(Wordlist).where(Wordlist.slug == spec.slug))
        values = {
            "name": spec.name,
            "description": spec.description,
            "origin": WordlistOrigin.BUILTIN.value,
            "kind": spec.kind,
            "filename": spec.filename,
            "words": words,
            "bytes": path.stat().st_size,
            "updated_at": now,
        }
        if row is None:
            session.add(Wordlist(slug=spec.slug, **values))
            changed = True
        elif row.words != words or row.bytes != values["bytes"]:
            for key, value in values.items():
                setattr(row, key, value)
            session.add(row)
            changed = True
    if changed:
        await session.commit()


@router.get("/kinds", response_model=dict[str, str])
async def wordlist_kinds(_current_user: CurrentUser):
    return KIND_LABELS


@router.get("", response_model=list[WordlistRead])
async def list_wordlists(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    kind: Annotated[
        str | None, Query(description="Filter by what the words are")
    ] = None,
):
    await _index_builtin(session)
    query = select(Wordlist).order_by(Wordlist.origin, Wordlist.name)
    if kind:
        query = query.where(Wordlist.kind == kind)
    rows = (await session.execute(query)).scalars().all()
    return [WordlistRead.model_validate(row, from_attributes=True) for row in rows]


@router.post(
    "", response_model=WordlistUploadResult, status_code=status.HTTP_201_CREATED
)
async def upload_wordlists(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: WordlistUploadRequest,
):
    kind = body.kind if body.kind in KIND_LABELS else WordlistKind.SUBDOMAIN.value
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
            filename, words = store_custom(item.filename, item.content)
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
                    reason=f"The name {slug!r} is already used by another wordlist.",
                )
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
    out: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            word = line.strip()
            if word and not word.startswith("#"):
                out.append(word)
            if len(out) >= limit:
                break
    return out


@router.patch("/{wordlist_id}", response_model=WordlistRead)
async def update_wordlist(
    _current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    wordlist_id: Annotated[UUID, Path(description="Wordlist ID")],
    data: WordlistUpdate,
):
    row = await _get(session, wordlist_id)
    if row.origin == WordlistOrigin.BUILTIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A shipped wordlist cannot be edited.",
        )
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(row, key, value)
    row.updated_at = utc_now()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return WordlistRead.model_validate(row, from_attributes=True)


@router.delete("/{wordlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wordlist(
    _current_user: CurrentUser,
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
