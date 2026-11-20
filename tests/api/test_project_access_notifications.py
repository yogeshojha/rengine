"""Project access on notes, notifications, the event stream, tripwires, exports and reports."""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.api import access as access_api
from app.api.deps import (
    get_current_active_user,
    get_stream_user,
    get_token_from_request,
)
from app.api.v1.events import validate_channels
from app.config import API_V1_PREFIX
from app.core.database import get_session
from app.main import app
from shared.enums.notification import NotificationSeverity, NotificationType
from shared.enums.sse import SSEChannel
from shared.models.note import Note
from shared.models.notification import Notification
from shared.models.tripwire import Tripwire
from shared.services import notification_sync
from shared.services.notification import NotificationManager
from shared.services.project_access import EVERY_PROJECT

pytestmark = pytest.mark.api


@pytest.fixture
async def world(flush_only, estate):
    other = await estate.sibling("Other")
    member = await estate.member(estate.project_id)
    return estate, other, member


@pytest.fixture
async def client(world):
    estate, _, member = world

    async def session():
        yield estate.session

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_current_active_user] = lambda: member
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


async def _notifications(estate, other) -> dict[str, uuid.UUID]:
    rows = {
        "mine": Notification(
            type=NotificationType.SCAN,
            severity=NotificationSeverity.INFO,
            title="mine",
            message="m",
            project_id=estate.project_id,
        ),
        "theirs": Notification(
            type=NotificationType.SCAN,
            severity=NotificationSeverity.INFO,
            title="theirs",
            message="t",
            project_id=other.project_id,
        ),
        "global": Notification(
            type=NotificationType.SYSTEM,
            severity=NotificationSeverity.INFO,
            title="global",
            message="g",
        ),
    }
    estate.session.add_all(rows.values())
    await estate.session.flush()
    return {name: row.uid for name, row in rows.items()}


# ---------- notifications ----------


async def test_a_member_lists_their_projects_and_instance_notifications(world):
    estate, other, member = world
    await _notifications(estate, other)

    def titles(access):
        return estate.session.scalars(
            NotificationManager.receipt_join(
                NotificationManager.in_scope(select(Notification.title), access),
                member.id,
            )
        )

    assert set((await titles(frozenset({estate.project_id}))).all()) == {
        "mine",
        "global",
    }
    assert set((await titles(frozenset())).all()) == {"global"}
    assert set((await titles(EVERY_PROJECT)).all()) == {"mine", "theirs", "global"}


async def test_a_member_cannot_read_or_dismiss_another_projects_notification(world):
    estate, other, member = world
    ids = await _notifications(estate, other)
    mine = frozenset({estate.project_id})

    assert not await NotificationManager.mark_as_read(
        estate.session, ids["theirs"], member.id, mine
    )
    assert not await NotificationManager.dismiss(
        estate.session, ids["theirs"], member.id, mine
    )
    assert await NotificationManager.mark_as_read(
        estate.session, ids["mine"], member.id, mine
    )
    assert await NotificationManager.dismiss(
        estate.session, ids["global"], member.id, mine
    )


async def test_read_all_stamps_only_what_the_member_sees(world):
    estate, other, member = world
    await _notifications(estate, other)

    count = await NotificationManager.mark_all_as_read(
        estate.session, member.id, frozenset({estate.project_id})
    )

    assert count == 2


async def test_the_notification_routes_refuse_another_projects_row(world, client):
    estate, other, _ = world
    ids = await _notifications(estate, other)

    read = await client.patch(f"{API_V1_PREFIX}/notifications/{ids['theirs']}/read")
    dismissed = await client.delete(f"{API_V1_PREFIX}/notifications/{ids['theirs']}")
    listed = await client.get(f"{API_V1_PREFIX}/notifications")
    named = await client.get(
        f"{API_V1_PREFIX}/notifications", params={"project_id": str(other.project_id)}
    )

    assert read.status_code == 404
    assert dismissed.status_code == 404
    assert {n["title"] for n in listed.json()["items"]} == {"mine", "global"}
    assert named.status_code == 404


async def test_a_notification_is_served_by_its_opaque_id(world, client):
    estate, other, _ = world
    ids = await _notifications(estate, other)
    serial = await estate.session.scalar(
        select(Notification.id).where(Notification.uid == ids["mine"])
    )

    listed = (await client.get(f"{API_V1_PREFIX}/notifications")).json()["items"]
    by_serial = await client.patch(f"{API_V1_PREFIX}/notifications/{serial}/read")
    by_uid = await client.patch(f"{API_V1_PREFIX}/notifications/{ids['mine']}/read")

    assert {n["id"] for n in listed} == {str(ids["mine"]), str(ids["global"])}
    assert by_serial.status_code == 422
    assert by_uid.status_code == 200


# ---------- realtime ----------


def test_the_stream_drops_a_channel_of_a_closed_project():
    mine, theirs = uuid.uuid4(), uuid.uuid4()
    requested = [
        SSEChannel.BROADCAST.value,
        SSEChannel.project(str(mine)),
        SSEChannel.project(str(theirs)),
        f"{SSEChannel.PROJECT}:not-a-uuid",
    ]

    assert validate_channels(requested, frozenset({mine})) == [
        SSEChannel.BROADCAST.value,
        SSEChannel.project(str(mine)),
    ]
    assert validate_channels(requested, EVERY_PROJECT) == requested[:3]


async def test_the_stream_refuses_a_request_for_closed_projects_alone(world):
    _, other, member = world
    app.dependency_overrides[get_stream_user] = lambda: member
    app.dependency_overrides[access_api.get_stream_access] = lambda: frozenset()
    app.dependency_overrides[get_token_from_request] = lambda: "token"
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            response = await c.get(
                f"{API_V1_PREFIX}/events/stream",
                params={"channels": SSEChannel.project(str(other.project_id))},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


async def test_a_project_notification_goes_out_on_its_project_channel(
    world, monkeypatch
):
    estate, _, _ = world
    sent: list[str] = []
    frames: list[dict] = []

    def capture(_self, channel, **kwargs):
        sent.append(channel)
        frames.append(kwargs["data"])

    monkeypatch.setattr(notification_sync.SyncEventPublisher, "publish", capture)
    publisher = notification_sync.SyncNotificationPublisher()

    def publish(sync, project_id):
        publisher.publish(
            sync,
            NotificationType.SCAN,
            NotificationSeverity.INFO,
            "Scan completed",
            "m",
            project_id=project_id,
            dispatch=False,
            commit=False,
        )

    await estate.session.run_sync(publish, estate.project_id)
    await estate.session.run_sync(publish, None)

    assert sent == [
        SSEChannel.project(str(estate.project_id)),
        SSEChannel.BROADCAST.value,
    ]
    published = await estate.session.execute(
        select(Notification.uid, Notification.id).where(
            Notification.uid.in_([uuid.UUID(f["id"]) for f in frames])
        )
    )
    assert len(published.all()) == 2


# ---------- row-id routes ----------


async def _rows_of(other) -> dict[str, uuid.UUID]:
    session = other.session
    target = await other.target("qzcanary.example")
    note = Note(
        project_id=other.project_id,
        target_id=target,
        body="qzcanary",
        created_by=other.user_id,
    )
    tripwire = Tripwire(
        project_id=other.project_id,
        name="qzcanary",
        dimension="web_assets",
        query="status:200",
        created_by=other.user_id,
    )
    session.add_all([note, tripwire])
    await session.flush()
    return {"note": note.id, "tripwire": tripwire.id}


@pytest.mark.parametrize("project", ["mine", "theirs"])
async def test_a_row_of_another_project_answers_404(world, client, project):
    estate, other, _ = world
    ids = await _rows_of(other)
    pid = estate.project_id if project == "mine" else other.project_id
    params = {"project_id": str(pid)}

    responses = [
        await client.get(f"{API_V1_PREFIX}/notes/{ids['note']}", params=params),
        await client.patch(
            f"{API_V1_PREFIX}/notes/{ids['note']}", params=params, json={"body": "x"}
        ),
        await client.delete(f"{API_V1_PREFIX}/notes/{ids['note']}", params=params),
        await client.patch(
            f"{API_V1_PREFIX}/tripwires/{ids['tripwire']}",
            params=params,
            json={"name": "x"},
        ),
        await client.delete(
            f"{API_V1_PREFIX}/tripwires/{ids['tripwire']}", params=params
        ),
        await client.get(
            f"{API_V1_PREFIX}/tripwires/{ids['tripwire']}/runs", params=params
        ),
        await client.get(f"{API_V1_PREFIX}/exports/{uuid.uuid4()}", params=params),
        await client.get(f"{API_V1_PREFIX}/reports/{uuid.uuid4()}", params=params),
    ]

    assert [r.status_code for r in responses] == [404] * len(responses)
    assert all("qzcanary" not in r.text for r in responses)
    assert await estate.session.get(Note, ids["note"]) is not None
    assert await estate.session.get(Tripwire, ids["tripwire"]) is not None


async def test_a_list_named_for_another_project_answers_404(world, client):
    _, other, _ = world
    params = {"project_id": str(other.project_id)}

    for path in (
        "/notes",
        "/tripwires",
        "/exports",
        "/reports",
        "/reports/templates",
    ):
        response = await client.get(API_V1_PREFIX + path, params=params)
        assert response.status_code == 404, path
        assert response.json()["detail"] == "Project not found."


async def test_the_unknown_and_the_closed_project_answer_alike(world, client):
    _, other, _ = world

    closed = await client.get(
        f"{API_V1_PREFIX}/reports", params={"project_id": str(other.project_id)}
    )
    unknown = await client.get(
        f"{API_V1_PREFIX}/reports", params={"project_id": str(uuid.uuid4())}
    )

    assert closed.status_code == unknown.status_code == 404
    assert closed.json() == unknown.json()
