"""Recon notes: written on an asset, read back from its scan and its target."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import (
    Select,
    String,
    case,
    exists,
    false,
    func,
    literal,
    or_,
    select,
    tuple_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.surface_scope import TABLES
from shared.definitions.notes import (
    ASSET_IDENTITY,
    MAX_NOTE_FACET_VALUES,
    MAX_NOTE_TAG_SUGGESTIONS,
    NOTE_ASSET_SEPARATOR,
    NOTE_STATUSES,
    NOTE_SUBJECTS,
    NoteStatus,
    NoteSubject,
)
from shared.definitions.surface import SurfaceDimension
from shared.models.note import (
    Note,
    NoteAssetFacet,
    NoteCreate,
    NoteFacet,
    NoteFacets,
    NoteFilter,
    NoteRead,
    NoteScanFacet,
    NoteTagCount,
    NoteUpdate,
    note_tag,
)
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.target import Target
from shared.models.user import User
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import element_counts, lead_cache
from shared.utils.datetime import utc_now

_SCAN_NOT_FOUND = "Scan not found"
_NOTE_NOT_FOUND = "Note not found"
_FINDINGS = SurfaceDimension.VULNERABILITIES.value
_SCAN_AT = func.coalesce(Scan.started_at, Scan.created_at)
_LIKE_SPECIAL = str.maketrans({"\\": "\\\\", "%": "\\%", "_": "\\_"})


def _identity(dimension: str, model):
    """This dimension's identity column."""
    if dimension == SurfaceDimension.SERVICES.value:
        host = case(
            (Port.ip.like("%:%"), func.concat(literal("["), Port.ip, literal("]"))),
            else_=Port.ip,
        )
        return func.concat(host, literal(":"), func.cast(Port.number, String))
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


def finding_label(template_name: str, where: str | None) -> str:
    """How a note names the finding it is written on."""
    return f"{template_name} on {where}" if where else template_name


def reason_notes(
    findings: Iterable[Vulnerability], *, state: str, body: str, user_id: UUID
) -> list[Note]:
    """One triage note per finding, for the caller's transaction."""
    return [
        Note(
            project_id=row.project_id,
            target_id=row.target_id,
            scan_id=row.scan_id,
            dimension=_FINDINGS,
            asset_key=row.fingerprint,
            asset_label=finding_label(row.template_name, row.host or row.ip),
            body=body,
            triage_state=state,
            created_by=user_id,
        )
        for row in findings
    ]


def _subject():
    """The dimension a note sits on, or what a note with no asset is written on."""
    return case(
        (Note.dimension.is_not(None), Note.dimension),
        (Note.scan_id.is_not(None), literal(NoteSubject.SCAN.value)),
        else_=literal(NoteSubject.TARGET.value),
    )


def _kind_is(values: list[str]):
    dimensions = [v for v in values if v not in NOTE_SUBJECTS]
    picks = []
    if dimensions:
        picks.append(Note.dimension.in_(dimensions))
    if NoteSubject.SCAN.value in values:
        picks.append(Note.dimension.is_(None) & Note.scan_id.is_not(None))
    if NoteSubject.TARGET.value in values:
        picks.append(Note.dimension.is_(None) & Note.scan_id.is_(None))
    return or_(*picks)


def _asset_pairs(values: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for value in values:
        dimension, sep, key = value.partition(NOTE_ASSET_SEPARATOR)
        if sep and dimension and key:
            pairs.append((dimension, key))
    return pairs


def _asset_is(values: list[str]):
    pairs = _asset_pairs(values)
    if not pairs:
        return false()
    return tuple_(Note.dimension, Note.asset_key).in_(pairs)


def _contains(column, term: str):
    return column.ilike(f"%{term.translate(_LIKE_SPECIAL)}%")


def _ranked(query: Select, held, chosen) -> Select:
    """Facet rows by count, chosen values first."""
    first = [case((chosen, 0), else_=1)] if chosen is not None else []
    return query.order_by(*first, func.count().desc(), held).limit(
        MAX_NOTE_FACET_VALUES
    )


class NoteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _select() -> Select:
        finding = (
            select(Vulnerability.id)
            .where(
                Vulnerability.scan_id == Note.scan_id,
                Vulnerability.fingerprint == Note.asset_key,
            )
            .limit(1)
            .scalar_subquery()
        )
        return (
            select(
                Note,
                Target.target_value,
                User.username,
                _SCAN_AT.label("scan_at"),
                case((Note.dimension == _FINDINGS, finding), else_=None).label(
                    "finding_id"
                ),
            )
            .join(Target, Target.id == Note.target_id)
            .join(User, User.id == Note.created_by)
            .outerjoin(Scan, Scan.id == Note.scan_id)
        )

    async def list(self, project_id: UUID, f: NoteFilter | None = None) -> Select:
        conditions = await self._conditions(project_id, f or NoteFilter())
        return (
            self._select()
            .where(*conditions)
            .order_by(Note.created_at.desc(), Note.id.desc())
        )

    async def _conditions(
        self, project_id: UUID, f: NoteFilter, skip: str | None = None
    ) -> list:
        """Every filter the request names, less the facet being counted."""
        out = [Note.project_id == project_id]
        if f.target_ids and skip != "targets":
            out.append(Note.target_id.in_(f.target_ids))
        if f.scan_id is not None:
            out.append(await self._scan_reach(f.scan_id, project_id))
        if f.scans and skip != "scans":
            out.append(Note.scan_id.in_(f.scans))
        if f.dimensions and skip != "dimensions":
            out.append(_kind_is(f.dimensions))
        if f.asset_key:
            out.append(Note.asset_key == f.asset_key)
        if f.assets and skip != "assets":
            out.append(_asset_is(f.assets))
        tags = list(dict.fromkeys(t for t in map(note_tag, f.tags) if t))
        if tags:
            out.append(Note.tags.contains(tags))
        if f.statuses and skip != "statuses":
            out.append(Note.status.in_(f.statuses))
        if f.authors and skip != "authors":
            out.append(Note.created_by.in_(f.authors))
        if f.triage and skip != "triage":
            out.append(Note.triage_state.in_(f.triage))
        term = (f.search or "").strip()
        if term:
            out.append(or_(_contains(Note.body, term), _contains(Note.title, term)))
        return out

    async def facets(
        self, project_id: UUID, f: NoteFilter, *, asset_query: str | None = None
    ) -> NoteFacets:
        """Each facet's values, counted under every other filter in the request."""

        async def rows(skip: str, query: Select) -> list:
            where = await self._conditions(project_id, f, skip)
            return (await self.session.execute(query.where(*where))).all()

        everything = await self._conditions(project_id, f)
        total = await self.session.scalar(select(func.count()).where(*everything))

        target_rows = await rows(
            "targets",
            _ranked(
                select(Note.target_id, Target.target_value, func.count())
                .join(Target, Target.id == Note.target_id)
                .group_by(Note.target_id, Target.target_value),
                Target.target_value,
                Note.target_id.in_(f.target_ids) if f.target_ids else None,
            ),
        )

        kind = _subject()
        kind_rows = await rows(
            "dimensions",
            select(kind, func.count()).group_by(kind).order_by(func.count().desc()),
        )

        label = func.max(Note.asset_label)
        asset_query = (asset_query or "").strip()
        picked = _asset_is(f.assets) if f.assets else None
        assets = (
            select(Note.dimension, Note.asset_key, label, func.count())
            .where(Note.dimension.is_not(None))
            .group_by(Note.dimension, Note.asset_key)
        )
        if asset_query:
            found = or_(
                _contains(Note.asset_label, asset_query),
                _contains(Note.asset_key, asset_query),
            )
            assets = assets.having(
                func.bool_or(or_(found, picked) if picked is not None else found)
            )
        asset_rows = await rows(
            "assets",
            _ranked(
                assets,
                label,
                func.bool_or(picked) if picked is not None else None,
            ),
        )

        scan_rows = await rows(
            "scans",
            _ranked(
                select(Note.scan_id, Target.target_value, _SCAN_AT, func.count())
                .join(Scan, Scan.id == Note.scan_id)
                .join(Target, Target.id == Scan.target_id)
                .group_by(Note.scan_id, Target.target_value, _SCAN_AT),
                _SCAN_AT.desc(),
                Note.scan_id.in_(f.scans) if f.scans else None,
            ),
        )

        tag_counts = element_counts(
            select(Note).where(*everything), Note.tags
        ).subquery("counts")
        tag_rows = (
            await self.session.execute(
                select(tag_counts.c.value, tag_counts.c.n)
                .order_by(tag_counts.c.n.desc(), tag_counts.c.value)
                .limit(MAX_NOTE_FACET_VALUES)
            )
        ).all()

        author_rows = await rows(
            "authors",
            _ranked(
                select(Note.created_by, User.username, func.count())
                .join(User, User.id == Note.created_by)
                .group_by(Note.created_by, User.username),
                User.username,
                Note.created_by.in_(f.authors) if f.authors else None,
            ),
        )
        status_rows = await rows(
            "statuses",
            select(Note.status, func.count())
            .group_by(Note.status)
            .order_by(Note.status),
        )
        triage_rows = await rows(
            "triage",
            select(Note.triage_state, func.count())
            .where(Note.triage_state.is_not(None))
            .group_by(Note.triage_state)
            .order_by(Note.triage_state),
        )

        return NoteFacets(
            total=int(total or 0),
            targets=[
                NoteFacet(value=str(tid), label=value, count=n)
                for tid, value, n in target_rows
            ],
            dimensions=[NoteFacet(value=k, count=n) for k, n in kind_rows],
            assets=[
                NoteAssetFacet(
                    value=f"{dimension}{NOTE_ASSET_SEPARATOR}{key}",
                    label=shown or key,
                    dimension=dimension,
                    count=n,
                )
                for dimension, key, shown, n in asset_rows
            ],
            scans=[
                NoteScanFacet(value=str(sid), target_value=value, at=at, count=n)
                for sid, value, at, n in scan_rows
            ],
            tags=[NoteFacet(value=name, count=int(n)) for name, n in tag_rows],
            authors=[
                NoteFacet(value=str(uid), label=name, count=n)
                for uid, name, n in author_rows
            ],
            statuses=[NoteFacet(value=s, count=n) for s, n in status_rows],
            triage=[NoteFacet(value=s, count=n) for s, n in triage_rows],
        )

    async def tags(
        self, project_id: UUID, *, prefix: str | None = None
    ) -> list[NoteTagCount]:
        """The project's note tags, most used first."""
        counts = element_counts(
            select(Note).where(Note.project_id == project_id), Note.tags
        ).subquery("counts")
        query = select(counts.c.value, counts.c.n)
        start = note_tag(prefix or "")
        if start:
            query = query.where(counts.c.value.startswith(start, autoescape=True))
        rows = await self.session.execute(
            query.order_by(counts.c.n.desc(), counts.c.value).limit(
                MAX_NOTE_TAG_SUGGESTIONS
            )
        )
        return [NoteTagCount(name=name, count=n) for name, n in rows.all()]

    @staticmethod
    def to_read(
        note: Note,
        target_value: str,
        author: str | None,
        scan_at=None,
        finding_id: UUID | None = None,
    ) -> NoteRead:
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
            tags=list(note.tags or []),
            triage_state=note.triage_state,
            created_by=note.created_by,
            author=author,
            created_at=note.created_at,
            updated_at=note.updated_at,
            scan_at=scan_at,
            finding_id=finding_id,
        )

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
        note = Note(
            project_id=project_id,
            target_id=data.target_id,
            scan_id=data.scan_id,
            dimension=data.dimension,
            asset_key=data.asset_key,
            asset_label=data.asset_label or data.asset_key,
            title=(data.title or "").strip() or None,
            body=data.body,
            status=self._status(data.status),
            tags=data.tags,
            triage_state=data.triage_state,
            created_by=created_by,
        )
        self.session.add(note)
        await self.session.commit()
        await lead_cache.bump((note.target_id,))
        await self.session.refresh(note)
        return await self.read(note)

    async def update(
        self, note_id: UUID, data: NoteUpdate, project_id: UUID
    ) -> NoteRead:
        note = await self._own(note_id, project_id)
        if data.title is not None:
            note.title = data.title.strip() or None
        if data.body is not None:
            note.body = data.body
        if data.status is not None:
            note.status = self._status(data.status)
        if data.tags is not None:
            note.tags = data.tags
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

    async def get(self, note_id: UUID, project_id: UUID) -> NoteRead:
        return await self.read(await self._own(note_id, project_id))

    async def read(self, note: Note) -> NoteRead:
        row = (
            await self.session.execute(self._select().where(Note.id == note.id))
        ).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_NOTE_NOT_FOUND
            )
        return self.to_read(*row)

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

    @staticmethod
    def _status(value: str | None) -> str:
        if value and value not in NOTE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown status '{value}'.",
            )
        return value or NoteStatus.OPEN.value
