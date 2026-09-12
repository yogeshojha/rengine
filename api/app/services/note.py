"""Recon notes: written on an asset, read back from its scan and its target."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import (
    Select,
    String,
    delete,
    exists,
    func,
    literal,
    or_,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.surface_scope import TABLES
from shared.definitions.notes import ASSET_IDENTITY, NOTE_STATUSES, NoteStatus
from shared.definitions.surface import SurfaceDimension
from shared.models.note import (
    Note,
    NoteCount,
    NoteCreate,
    NoteRead,
    NoteTag,
    NoteUpdate,
)
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.tag import Tag, TagSummary
from shared.models.target import Target
from shared.models.user import User
from shared.services.asset_query import lead_cache
from shared.utils.datetime import utc_now

_SCAN_NOT_FOUND = "Scan not found"
_NOTE_NOT_FOUND = "Note not found"


def _identity(dimension: str, model):
    """This dimension's identity column."""
    if dimension == SurfaceDimension.SERVICES.value:
        return func.concat(Port.ip, literal(":"), func.cast(Port.number, String))
    return getattr(model, ASSET_IDENTITY[dimension])


def observed_in_scan(scan_id: UUID):
    """The asset this note names was seen by that scan."""
    return or_(
        *[
            (Note.dimension == dimension)
            & exists(
                select(1).where(
                    model.scan_id == scan_id,
                    _identity(dimension, model) == Note.asset_key,
                )
            )
            for dimension, model in TABLES.items()
        ]
    )


class NoteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(
        self,
        project_id: UUID,
        *,
        target_id: UUID | None = None,
        scan_id: UUID | None = None,
        dimension: str | None = None,
        asset_key: str | None = None,
        tag_ids: list[UUID] | None = None,
        statuses: list[str] | None = None,
        search: str | None = None,
    ) -> Select:
        query = (
            select(
                Note,
                Target.target_value,
                User.username,
                func.coalesce(
                    func.jsonb_agg(
                        func.jsonb_build_object(
                            "id",
                            Tag.id,
                            "name",
                            Tag.name,
                            "slug",
                            Tag.slug,
                            "color",
                            Tag.color,
                        )
                    ).filter(Tag.id.isnot(None)),
                    text("'[]'::jsonb"),
                ).label("tags"),
            )
            .join(Target, Target.id == Note.target_id)
            .join(User, User.id == Note.created_by)
            .outerjoin(NoteTag, NoteTag.note_id == Note.id)
            .outerjoin(Tag, Tag.id == NoteTag.tag_id)
            .where(Note.project_id == project_id)
            .group_by(Note.id, Target.target_value, User.username)
        )
        if target_id is not None:
            query = query.where(Note.target_id == target_id)
        if scan_id is not None:
            query = query.where(await self._scan_reach(scan_id, project_id))
        if dimension:
            query = query.where(Note.dimension == dimension)
        if asset_key:
            query = query.where(Note.asset_key == asset_key)
        if statuses:
            query = query.where(Note.status.in_(statuses))
        for tag_id in tag_ids or []:
            carried = aliased(NoteTag)
            query = query.where(
                exists(
                    select(1)
                    .where(carried.note_id == Note.id, carried.tag_id == tag_id)
                    .correlate(Note)
                )
            )
        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                Note.body.ilike(term)
                | Note.title.ilike(term)
                | Note.asset_label.ilike(term)
            )
        return query.order_by(Note.created_at.desc())

    @staticmethod
    def to_read(note: Note, target_value: str, author: str | None, tags) -> NoteRead:
        return NoteRead(
            id=note.id,
            project_id=note.project_id,
            target_id=note.target_id,
            target_value=target_value,
            scan_id=note.scan_id,
            dimension=note.dimension,
            asset_key=note.asset_key,
            asset_label=note.asset_label,
            title=note.title,
            body=note.body,
            status=note.status,
            tags=[TagSummary(**t) for t in tags or []],
            created_by=note.created_by,
            author=author,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    async def counts(
        self,
        project_id: UUID,
        *,
        dimension: str | None = None,
        target_id: UUID | None = None,
        scan_id: UUID | None = None,
    ) -> list[NoteCount]:
        """One row per asset that carries notes."""
        query = select(
            Note.asset_key,
            func.count(),
            func.count().filter(Note.status == NoteStatus.OPEN.value),
        ).where(Note.project_id == project_id, Note.asset_key.isnot(None))
        if dimension:
            query = query.where(Note.dimension == dimension)
        if target_id is not None:
            query = query.where(Note.target_id == target_id)
        if scan_id is not None:
            query = query.where(await self._scan_reach(scan_id, project_id))
        rows = await self.session.execute(query.group_by(Note.asset_key))
        return [
            NoteCount(key=key, total=int(total), open=int(open_))
            for key, total, open_ in rows.all()
        ]

    async def create(
        self, data: NoteCreate, project_id: UUID, created_by: UUID
    ) -> NoteRead:
        target = await self.session.get(Target, data.target_id)
        if target is None or target.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Target not found"
            )
        if data.scan_id is not None:
            scan = await self.session.get(Scan, data.scan_id)
            if scan is None or scan.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=_SCAN_NOT_FOUND
                )
        tags = await self._tags(data.tag_ids, project_id)
        note = Note(
            project_id=project_id,
            target_id=data.target_id,
            scan_id=data.scan_id,
            dimension=data.dimension,
            asset_key=data.asset_key,
            asset_label=data.asset_label or data.asset_key,
            title=data.title,
            body=data.body,
            status=self._status(data.status),
            created_by=created_by,
        )
        self.session.add(note)
        await self.session.flush()
        self.session.add_all([NoteTag(note_id=note.id, tag_id=tag.id) for tag in tags])
        await self.session.commit()
        await lead_cache.bump((note.target_id,))
        await self.session.refresh(note)
        return await self.read(note)

    async def update(
        self, note_id: UUID, data: NoteUpdate, project_id: UUID
    ) -> NoteRead:
        note = await self._own(note_id, project_id)
        if data.title is not None:
            note.title = data.title
        if data.body is not None:
            note.body = data.body
        if data.status is not None:
            note.status = self._status(data.status)
        tags = None
        if data.tag_ids is not None:
            tags = await self._tags(data.tag_ids, project_id)
            await self.session.execute(
                delete(NoteTag).where(NoteTag.note_id == note.id)
            )
            self.session.add_all(
                [NoteTag(note_id=note.id, tag_id=tag.id) for tag in tags]
            )
        note.updated_at = utc_now()
        await self.session.commit()
        await lead_cache.bump((note.target_id,))
        await self.session.refresh(note)
        return await self.read(note)

    async def delete(self, note_id: UUID, project_id: UUID) -> None:
        note = await self._own(note_id, project_id)
        await self.session.delete(note)
        await self.session.commit()
        await lead_cache.bump((note.target_id,))

    async def read(self, note: Note) -> NoteRead:
        row = (
            await self.session.execute(
                (await self.list(note.project_id)).where(Note.id == note.id)
            )
        ).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_NOTE_NOT_FOUND
            )
        return self.to_read(row[0], row[1], row[2], row[3])

    async def _scan_reach(self, scan_id: UUID, project_id: UUID):
        """A scan shows what was written on it, plus notes on assets it observed."""
        scan = await self.session.get(Scan, scan_id)
        if scan is None or scan.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_SCAN_NOT_FOUND
            )
        return or_(
            Note.scan_id == scan_id,
            (Note.target_id == scan.target_id) & observed_in_scan(scan_id),
        )

    async def _own(self, note_id: UUID, project_id: UUID) -> Note:
        note = await self.session.get(Note, note_id)
        if note is None or note.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_NOTE_NOT_FOUND
            )
        return note

    async def _tags(self, tag_ids: list[UUID], project_id: UUID) -> list[Tag]:
        tags = list(
            (
                await self.session.execute(
                    select(Tag).where(Tag.id.in_(tag_ids), Tag.project_id == project_id)
                )
            )
            .scalars()
            .all()
        )
        if len(tags) != len(set(tag_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of those tags is not in this project.",
            )
        return tags

    @staticmethod
    def _status(value: str | None) -> str:
        if value and value not in NOTE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown status '{value}'.",
            )
        return value or NoteStatus.OPEN.value
