from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

import app.services.note as note_service
from app.services.note import NoteService
from shared.definitions.notes import (
    MAX_NOTE_TAG_CHARS,
    MAX_NOTE_TAG_SUGGESTIONS,
    MAX_NOTE_TAGS,
    NoteSubject,
)
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import VulnState
from shared.models.note import Note, NoteCreate, NoteFilter, NoteUpdate
from shared.models.user import User
from shared.models.vulnerability import Vulnerability

pytestmark = pytest.mark.api


async def _two_runs(estate, now):
    """The same host seen by two scans of one target."""
    earlier = now - timedelta(days=3)
    await estate.scan("example.com", "first", at=earlier)
    await estate.hosts("first", ["api.example.com", "gone.example.com"], at=earlier)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", ["api.example.com"], at=now)


async def _write(
    estate,
    scan: str,
    host: str,
    tags: list[str] | None = None,
    body: str = "Worth a look",
):
    return await NoteService(estate.session).create(
        NoteCreate(
            target_id=estate.targets["example.com"],
            scan_id=estate.scans[scan],
            dimension=SurfaceDimension.WEB_ASSETS.value,
            asset_key=host,
            asset_label=host,
            body=body,
            tags=tags or [],
        ),
        estate.project_id,
        estate.user_id,
    )


async def _bodies(estate, **filters) -> list[str]:
    service = NoteService(estate.session)
    query = await service.list(estate.project_id, NoteFilter(**filters))
    return sorted(r[0].body for r in (await estate.session.execute(query)).all())


async def test_a_note_follows_its_asset_into_a_later_scan(estate, now):
    await _two_runs(estate, now)
    await _write(estate, "first", "api.example.com")
    service = NoteService(estate.session)

    for name in ("first", "second"):
        query = await service.list(
            estate.project_id, NoteFilter(scan_id=estate.scans[name])
        )
        rows = (await estate.session.execute(query)).all()
        assert [r[0].asset_key for r in rows] == ["api.example.com"], name


async def test_a_note_on_a_host_a_scan_never_saw_stays_out_of_it(estate, now):
    await _two_runs(estate, now)
    await _write(estate, "first", "gone.example.com")

    assert await _bodies(estate, scan_id=estate.scans["first"]) == ["Worth a look"]
    assert await _bodies(estate, scan_id=estate.scans["second"]) == []


async def test_the_target_carries_every_note_its_scans_hold(estate, now):
    await _two_runs(estate, now)
    await _write(estate, "first", "gone.example.com", body="Retired host")
    await _write(estate, "second", "api.example.com", body="No auth")

    bodies = await _bodies(estate, target_ids=[estate.targets["example.com"]])
    assert bodies == ["No auth", "Retired host"]


async def test_a_note_is_saved_without_tags(estate, now):
    await _two_runs(estate, now)
    note = await _write(estate, "second", "api.example.com")

    assert note.tags == []
    stored = await estate.session.get(Note, note.id)
    assert stored.tags == []


async def test_tags_are_stored_as_typed_names(estate, now):
    await _two_runs(estate, now)
    note = await _write(
        estate,
        "second",
        "api.example.com",
        tags=["IDOR", "#Auth", "idor", "  sql   injection ", "", "#", "##api:v2"],
    )

    assert note.tags == ["idor", "auth", "sql-injection", "api:v2"]


async def test_an_update_to_no_tags_clears_them(estate, now):
    await _two_runs(estate, now)
    note = await _write(estate, "second", "api.example.com", tags=["idor"])
    service = NoteService(estate.session)

    kept = await service.update(note.id, NoteUpdate(body="Edited"), estate.project_id)
    assert kept.tags == ["idor"]

    renamed = await service.update(
        note.id, NoteUpdate(tags=["#Auth", "auth"]), estate.project_id
    )
    assert renamed.tags == ["auth"]

    cleared = await service.update(note.id, NoteUpdate(tags=[]), estate.project_id)
    assert cleared.tags == []
    assert (await estate.session.get(Note, note.id)).tags == []


async def test_an_emptied_title_is_removed(estate, now):
    await _two_runs(estate, now)
    service = NoteService(estate.session)
    note = await service.create(
        NoteCreate(
            target_id=estate.targets["example.com"],
            title="  Login  ",
            body="Rate limit is 20/min",
        ),
        estate.project_id,
        estate.user_id,
    )
    assert note.title == "Login"

    kept = await service.update(note.id, NoteUpdate(body="Edited"), estate.project_id)
    assert kept.title == "Login"
    cleared = await service.update(note.id, NoteUpdate(title="  "), estate.project_id)
    assert cleared.title is None


async def test_the_list_keeps_notes_carrying_every_tag_named(estate, now):
    await _two_runs(estate, now)
    await _write(estate, "second", "api.example.com", ["idor", "auth"], "both")
    await _write(estate, "second", "api.example.com", ["idor"], "idor only")
    await _write(estate, "second", "api.example.com", body="untagged")

    assert await _bodies(estate, tags=["idor"]) == ["both", "idor only"]
    assert await _bodies(estate, tags=["#IDOR", "Auth"]) == ["both"]
    assert await _bodies(estate, tags=["missing"]) == []
    assert await _bodies(estate, tags=[]) == ["both", "idor only", "untagged"]


async def test_note_tags_are_counted_most_used_first(estate, now):
    await _two_runs(estate, now)
    await _write(estate, "second", "api.example.com", ["idor", "auth"])
    await _write(estate, "second", "api.example.com", ["idor", "api_v2"])
    await _write(estate, "second", "api.example.com", ["apiv2"])
    await _write(estate, "first", "gone.example.com", ["idor"])
    other = await type(estate)(estate.session).setup()
    await other.scan("example.org", "theirs", at=now)
    await NoteService(estate.session).create(
        NoteCreate(target_id=other.targets["example.org"], body="x", tags=["idor"]),
        other.project_id,
        other.user_id,
    )
    service = NoteService(estate.session)

    counts = [(t.name, t.count) for t in await service.tags(estate.project_id)]
    assert counts == [("idor", 3), ("api_v2", 1), ("apiv2", 1), ("auth", 1)]

    narrowed = await service.tags(estate.project_id, prefix="#A")
    assert [t.name for t in narrowed] == ["api_v2", "apiv2", "auth"]
    escaped = await service.tags(estate.project_id, prefix="api_")
    assert [t.name for t in escaped] == ["api_v2"]
    assert await service.tags(estate.project_id, prefix="zz") == []


async def test_note_tag_suggestions_are_capped(estate, now):
    await _two_runs(estate, now)
    for n in range(MAX_NOTE_TAG_SUGGESTIONS + 5):
        await _write(estate, "second", "api.example.com", [f"t{n:03d}"])

    tags = await NoteService(estate.session).tags(estate.project_id)
    assert len(tags) == MAX_NOTE_TAG_SUGGESTIONS
    assert tags[0].name == "t000"


async def test_deleting_a_note_removes_it(estate, now):
    await _two_runs(estate, now)
    note = await _write(estate, "second", "api.example.com", ["idor"])
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
    assert await service.tags(estate.project_id) == []


def test_a_tag_takes_letters_digits_and_four_marks():
    created = NoteCreate(
        target_id=uuid.uuid4(), body="x", tags=["café", "नेपाल", "a.b_c-d:e"]
    )
    assert created.tags == ["café", "नेपाल", "a.b_c-d:e"]
    for bad in ("a/b", "<script>", "a,b", "50%", "a#b"):
        with pytest.raises(ValidationError, match="has a character outside"):
            NoteCreate(target_id=uuid.uuid4(), body="x", tags=[bad])


def test_a_tag_over_the_length_cap_is_refused():
    NoteCreate(target_id=uuid.uuid4(), body="x", tags=["a" * MAX_NOTE_TAG_CHARS])
    with pytest.raises(ValidationError, match=f"at most {MAX_NOTE_TAG_CHARS}"):
        NoteCreate(
            target_id=uuid.uuid4(), body="x", tags=["a" * (MAX_NOTE_TAG_CHARS + 1)]
        )


def test_a_note_takes_a_bounded_number_of_tags():
    names = [f"t{n}" for n in range(MAX_NOTE_TAGS)]
    assert len(NoteCreate(target_id=uuid.uuid4(), body="x", tags=names).tags) == 20
    with pytest.raises(ValidationError, match=f"at most {MAX_NOTE_TAGS} tags"):
        NoteUpdate(tags=[*names, "one-more"])
    assert NoteUpdate(tags=[*names, *names]).tags == names


def test_an_asset_note_needs_both_a_dimension_and_an_asset():
    with pytest.raises(ValidationError, match="both a dimension and an asset"):
        NoteCreate(
            target_id=uuid.uuid4(),
            dimension=SurfaceDimension.WEB_ASSETS.value,
            body="half an anchor",
        )


def test_an_empty_body_is_refused():
    with pytest.raises(ValidationError):
        NoteCreate(target_id=uuid.uuid4(), body="   ")


def test_ask_citation_marks_are_not_stored_in_a_note():
    created = NoteCreate(
        target_id=uuid.uuid4(),
        body="Apache 2.4.41 [[1]][[2]], see arr[1] and [[x]].",
    )
    assert created.body == "Apache 2.4.41, see arr[1] and [[x]]."
    assert NoteUpdate(body="No findings [[1]].").body == "No findings."


def test_a_body_of_citation_marks_alone_is_refused():
    with pytest.raises(ValidationError, match="body is required"):
        NoteCreate(target_id=uuid.uuid4(), body="[[1]] [[2]]")


# ---------- filters and facets ----------

_FACET_FIELDS = {
    "targets": "target_ids",
    "dimensions": "dimensions",
    "assets": "assets",
    "scans": "scans",
    "authors": "authors",
    "statuses": "statuses",
    "triage": "triage",
}


async def _count(service, project_id, f: NoteFilter) -> int:
    query = await service.list(project_id, f)
    return await service.session.scalar(
        select(func.count()).select_from(query.subquery())
    )


async def _keeps_the_promise(estate, f: NoteFilter) -> int:
    """Every facet count equals the rows its value opens."""
    service = NoteService(estate.session)
    facets = await service.facets(estate.project_id, f)
    assert facets.total == await _count(service, estate.project_id, f)
    checked = 0
    for name, field in _FACET_FIELDS.items():
        for facet in getattr(facets, name):
            value = (
                uuid.UUID(facet.value)
                if field in ("target_ids", "scans", "authors")
                else facet.value
            )
            narrowed = f.model_copy(update={field: [value]})
            assert facet.count == await _count(service, estate.project_id, narrowed), (
                name,
                facet.value,
            )
            checked += 1
    for facet in facets.tags:
        narrowed = f.model_copy(update={"tags": [*f.tags, facet.value]})
        assert facet.count == await _count(service, estate.project_id, narrowed)
        checked += 1
    return checked


async def _estate_of_notes(estate, now):
    await _two_runs(estate, now)
    await estate.vulns("second", [("sqli", "high")], at=now, host="api.example.com")
    await estate.scan("example.org", "other", at=now)
    colleague = User(
        id=uuid.uuid4(),
        username=f"c{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    estate.session.add(colleague)
    await estate.session.flush()
    service = NoteService(estate.session)
    example = estate.targets["example.com"]

    async def write(by=estate.user_id, **fields):
        return await service.create(NoteCreate(**fields), estate.project_id, by)

    await _write(estate, "second", "api.example.com", ["idor", "auth"], "IDOR on users")
    await _write(estate, "first", "gone.example.com", ["idor"], "Retired host")
    await write(
        target_id=example,
        scan_id=estate.scans["second"],
        dimension=SurfaceDimension.VULNERABILITIES.value,
        asset_key="sqli",
        asset_label="Sqli on api.example.com",
        body="WAF strips the payload",
        triage_state=VulnState.FALSE_POSITIVE.value,
    )
    await write(
        by=colleague.id,
        target_id=example,
        scan_id=estate.scans["second"],
        dimension=SurfaceDimension.ENDPOINTS.value,
        asset_key="sig-1",
        asset_label="https://api.example.com/v2/users?id=1",
        body="Returns 50% of the records",
        tags=["auth"],
    )
    resolved = await write(
        by=colleague.id, target_id=example, body="Scope agreed with the owner"
    )
    await service.update(resolved.id, NoteUpdate(status="resolved"), estate.project_id)
    await write(
        target_id=estate.targets["example.org"],
        scan_id=estate.scans["other"],
        title="Payload notes",
        body="Second target",
    )
    return colleague


async def test_every_facet_count_opens_its_rows(estate, now):
    await _estate_of_notes(estate, now)
    assert await _keeps_the_promise(estate, NoteFilter()) > 10
    await _keeps_the_promise(estate, NoteFilter(statuses=["open"]))
    await _keeps_the_promise(estate, NoteFilter(tags=["idor"]))
    await _keeps_the_promise(
        estate, NoteFilter(dimensions=[SurfaceDimension.WEB_ASSETS.value])
    )
    await _keeps_the_promise(estate, NoteFilter(search="payload"))
    await _keeps_the_promise(
        estate,
        NoteFilter(
            target_ids=[estate.targets["example.com"]],
            triage=[VulnState.FALSE_POSITIVE.value],
        ),
    )


async def test_facets_name_what_each_value_is(estate, now):
    colleague = await _estate_of_notes(estate, now)
    facets = await NoteService(estate.session).facets(estate.project_id, NoteFilter())

    assert facets.total == 6
    assert {(f.label, f.count) for f in facets.targets} == {
        ("example.com", 5),
        ("example.org", 1),
    }
    assert {(f.value, f.count) for f in facets.dimensions} == {
        (SurfaceDimension.WEB_ASSETS.value, 2),
        (SurfaceDimension.VULNERABILITIES.value, 1),
        (SurfaceDimension.ENDPOINTS.value, 1),
        (NoteSubject.TARGET.value, 1),
        (NoteSubject.SCAN.value, 1),
    }
    assets = {f.value: (f.label, f.dimension) for f in facets.assets}
    assert assets[f"{SurfaceDimension.VULNERABILITIES.value}:sqli"] == (
        "Sqli on api.example.com",
        SurfaceDimension.VULNERABILITIES.value,
    )
    assert {(f.target_value, f.count) for f in facets.scans} == {
        ("example.com", 3),
        ("example.com", 1),
        ("example.org", 1),
    }
    assert {(f.label, f.count) for f in facets.authors} == {
        (f"t{estate.user_id.hex[:8]}", 4),
        (colleague.username, 2),
    }
    assert {(f.value, f.count) for f in facets.statuses} == {
        ("open", 5),
        ("resolved", 1),
    }
    assert [(f.value, f.count) for f in facets.triage] == [
        (VulnState.FALSE_POSITIVE.value, 1)
    ]
    assert [(f.value, f.count) for f in facets.tags] == [("auth", 2), ("idor", 2)]


async def test_the_search_reads_body_and_title_literally(estate, now):
    await _estate_of_notes(estate, now)

    assert await _bodies(estate, search="PAYLOAD") == [
        "Second target",
        "WAF strips the payload",
    ]
    assert await _bodies(estate, search="50%") == ["Returns 50% of the records"]
    assert await _bodies(estate, search="5_%") == []
    assert await _bodies(estate, search="api.example.com") == []


async def test_a_scan_filter_is_the_scan_a_note_was_written_in(estate, now):
    await _estate_of_notes(estate, now)

    written = await _bodies(estate, scans=[estate.scans["first"]])
    assert written == ["Retired host"]
    reach = await _bodies(estate, scan_id=estate.scans["first"])
    assert reach == ["IDOR on users", "Retired host"]


async def test_an_asset_filter_names_its_dimension(estate, now):
    await _estate_of_notes(estate, now)
    web = SurfaceDimension.WEB_ASSETS.value

    assert await _bodies(estate, assets=[f"{web}:api.example.com"]) == ["IDOR on users"]
    assert await _bodies(estate, assets=["api.example.com"]) == []
    assert await _bodies(
        estate,
        dimensions=[NoteSubject.TARGET.value, NoteSubject.SCAN.value],
    ) == ["Scope agreed with the owner", "Second target"]


async def test_the_asset_facet_searches_and_keeps_a_pick(estate, now, monkeypatch):
    await _estate_of_notes(estate, now)
    service = NoteService(estate.session)
    web = SurfaceDimension.WEB_ASSETS.value

    found = await service.facets(estate.project_id, NoteFilter(), asset_query="GONE")
    assert [f.value for f in found.assets] == [f"{web}:gone.example.com"]

    monkeypatch.setattr(note_service, "MAX_NOTE_FACET_VALUES", 1)
    picked = f"{web}:gone.example.com"
    kept = await service.facets(estate.project_id, NoteFilter(assets=[picked]))
    assert [f.value for f in kept.assets] == [picked]


async def test_a_note_reads_its_finding_and_scan(estate, now):
    await _estate_of_notes(estate, now)
    service = NoteService(estate.session)
    rows = (
        await estate.session.execute(
            await service.list(
                estate.project_id,
                NoteFilter(triage=[VulnState.FALSE_POSITIVE.value]),
            )
        )
    ).all()
    note = service.to_read(*rows[0])
    finding = await estate.session.scalar(
        select(Vulnerability.id).where(
            Vulnerability.scan_id == estate.scans["second"],
            Vulnerability.fingerprint == "sqli",
        )
    )
    assert note.triage_state == VulnState.FALSE_POSITIVE.value
    assert note.finding_id == finding
    assert note.scan_at is not None

    web = (
        await estate.session.execute(
            await service.list(
                estate.project_id,
                NoteFilter(
                    assets=[f"{SurfaceDimension.WEB_ASSETS.value}:api.example.com"]
                ),
            )
        )
    ).all()
    assert service.to_read(*web[0]).finding_id is None
