from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.services.note import NoteService
from shared.definitions.notes import NoteStatus
from shared.definitions.surface import SurfaceDimension
from shared.models.note import Note, NoteCreate, NoteUpdate
from shared.models.tag import Tag


async def _tag(estate, name: str = "lead") -> Tag:
    tag = Tag(
        id=uuid.uuid4(),
        name=name,
        slug=name,
        color="#6B7280",
        project_id=estate.project_id,
        created_by=estate.user_id,
    )
    estate.session.add(tag)
    await estate.session.flush()
    return tag


async def _two_runs(estate, now):
    """The same host seen by two scans of one target."""
    earlier = now - timedelta(days=3)
    await estate.scan("example.com", "first", at=earlier)
    await estate.hosts("first", ["api.example.com", "gone.example.com"], at=earlier)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", ["api.example.com"], at=now)
    return estate


async def _write(estate, scan: str, host: str, tag: Tag, body: str = "Worth a look"):
    return await NoteService(estate.session).create(
        NoteCreate(
            target_id=estate.targets["example.com"],
            scan_id=estate.scans[scan],
            dimension=SurfaceDimension.WEB_ASSETS.value,
            asset_key=host,
            asset_label=host,
            body=body,
            tag_ids=[tag.id],
        ),
        estate.project_id,
        estate.user_id,
    )


async def test_a_note_follows_its_asset_into_a_later_scan(estate, now):
    await _two_runs(estate, now)
    tag = await _tag(estate)
    await _write(estate, "first", "api.example.com", tag)
    service = NoteService(estate.session)

    for name in ("first", "second"):
        query = await service.list(estate.project_id, scan_id=estate.scans[name])
        rows = (await estate.session.execute(query)).all()
        assert [r[0].asset_key for r in rows] == ["api.example.com"], name


async def test_a_note_on_a_host_a_scan_never_saw_stays_out_of_it(estate, now):
    await _two_runs(estate, now)
    tag = await _tag(estate)
    await _write(estate, "first", "gone.example.com", tag)
    service = NoteService(estate.session)

    first = (
        await estate.session.execute(
            await service.list(estate.project_id, scan_id=estate.scans["first"])
        )
    ).all()
    second = (
        await estate.session.execute(
            await service.list(estate.project_id, scan_id=estate.scans["second"])
        )
    ).all()
    assert len(first) == 1
    assert second == []


async def test_the_target_carries_every_note_its_scans_hold(estate, now):
    await _two_runs(estate, now)
    tag = await _tag(estate)
    await _write(estate, "first", "gone.example.com", tag, body="Retired host")
    await _write(estate, "second", "api.example.com", tag, body="No auth")
    service = NoteService(estate.session)

    rows = (
        await estate.session.execute(
            await service.list(
                estate.project_id, target_id=estate.targets["example.com"]
            )
        )
    ).all()
    assert len(rows) == 2


async def test_the_count_equals_the_rows_it_opens(estate, now):
    await _two_runs(estate, now)
    tag = await _tag(estate)
    await _write(estate, "second", "api.example.com", tag)
    await _write(estate, "second", "api.example.com", tag, body="And another")
    service = NoteService(estate.session)

    counts = await service.counts(
        estate.project_id, dimension=SurfaceDimension.WEB_ASSETS.value
    )
    assert [(c.key, c.total, c.open) for c in counts] == [("api.example.com", 2, 2)]

    rows = (
        await estate.session.execute(
            await service.list(
                estate.project_id,
                dimension=SurfaceDimension.WEB_ASSETS.value,
                asset_key="api.example.com",
            )
        )
    ).all()
    assert len(rows) == counts[0].total


async def test_resolving_a_note_leaves_the_total_and_lowers_the_open_count(estate, now):
    await _two_runs(estate, now)
    tag = await _tag(estate)
    note = await _write(estate, "second", "api.example.com", tag)
    service = NoteService(estate.session)

    await service.update(
        note.id, NoteUpdate(status=NoteStatus.RESOLVED.value), estate.project_id
    )
    counts = await service.counts(
        estate.project_id, dimension=SurfaceDimension.WEB_ASSETS.value
    )
    assert counts[0].total == 1
    assert counts[0].open == 0


async def test_a_tag_outside_the_project_is_refused(estate, now):
    await _two_runs(estate, now)
    stranger = Tag(
        id=uuid.uuid4(),
        name="other",
        slug="other",
        color="#6B7280",
        project_id=uuid.uuid4(),
        created_by=estate.user_id,
    )

    with pytest.raises(HTTPException, match="not in this project"):
        await _write(estate, "second", "api.example.com", stranger)


async def test_deleting_a_note_removes_its_tag_links(estate, now):
    await _two_runs(estate, now)
    tag = await _tag(estate)
    note = await _write(estate, "second", "api.example.com", tag)
    service = NoteService(estate.session)

    await service.delete(note.id, estate.project_id)
    left = (
        (
            await estate.session.execute(
                select(Note).where(Note.project_id == estate.project_id)
            )
        )
        .scalars()
        .all()
    )
    assert left == []


def test_a_note_without_a_tag_is_refused():
    with pytest.raises(ValidationError):
        NoteCreate(target_id=uuid.uuid4(), body="no tags", tag_ids=[])


def test_an_asset_note_needs_both_a_dimension_and_an_asset():
    with pytest.raises(ValidationError, match="both a dimension and an asset"):
        NoteCreate(
            target_id=uuid.uuid4(),
            dimension=SurfaceDimension.WEB_ASSETS.value,
            body="half an anchor",
            tag_ids=[uuid.uuid4()],
        )


def test_an_empty_body_is_refused():
    with pytest.raises(ValidationError):
        NoteCreate(target_id=uuid.uuid4(), body="   ", tag_ids=[uuid.uuid4()])


def test_an_update_cannot_strip_the_last_tag():
    with pytest.raises(ValidationError, match="at least one tag"):
        NoteUpdate(tag_ids=[])
