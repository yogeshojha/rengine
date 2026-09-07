"""HackerOne programs and their structured scopes: fetch, store, and resolve to targets.

Measured limits are 600 reads/minute, so the pacer only has to survive a burst; the
client backs off on 429 and never touches a write endpoint.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from shared.definitions.bounty_programs import (
    DEFAULT_SYNC_INTERVAL,
    MAX_EVENT_DETAIL,
    SYNC_INTERVAL_HOURS,
    BountyEvent,
    BountyPlatform,
    ScopeState,
    SubmissionState,
    asset_type_spec,
    program_state,
    scope_state,
    submission_state,
    target_for_scope,
)
from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.api_key import APIKey
from shared.models.bounty_program import BountyEventRow, BountyProgram, BountyScope
from shared.utils.crypto import try_decrypt
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

BASE_URL = "https://api.hackerone.com/v1/hackers"
TIMEOUT = 30
PAGE_SIZE = 100
MAX_PAGES = 200
HTTP_TOO_MANY = 429
HTTP_UNAUTHORIZED = 401
RETRY_AFTER_DEFAULT = 5
MAX_RETRIES = 3
MAX_INSTRUCTION = 4000
# a truncated URL is a broken link, so an absurd one is dropped instead
MAX_PICTURE_URL = 4000


# two syncs deleting the same scope rows block each other badly: a no-change
# yeswehack pass measured 0.5s alone and 120.5s against a concurrent run
SYNC_LOCK_KEY = 0x624F0001
FEED_LOCK_KEY = 0x624F0002


@contextmanager
def sync_lock(session: Session, key: int) -> Iterator[bool]:
    """Session-level advisory lock, so it survives the per-program commits."""
    held = bool(
        session.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
        ).scalar_one()
    )
    try:
        yield held
    finally:
        if held:
            session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
            session.commit()


class HackerOneError(RuntimeError):
    pass


class CredentialsError(HackerOneError):
    pass


def credentials(session: Session) -> tuple[str, str] | None:
    """The instance's HackerOne API username and token, or None when not configured."""
    row = session.execute(
        select(APIKey).where(
            APIKey.provider == APIProvider.HACKERONE,
            APIKey.is_enabled == True,  # noqa: E712
        )
    ).scalar_one_or_none()
    if not row:
        return None
    username = (row.key_meta or {}).get("username")
    token = try_decrypt(row.key_value) or row.key_value
    if not username or not token:
        return None
    return str(username), str(token)


def _request(path: str, params: dict | None, auth: tuple[str, str]) -> dict:
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return _get(url, auth)


def _get(url: str, auth: tuple[str, str]) -> dict:
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {token}",
            "User-Agent": "reNgine",
        },
    )
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code == HTTP_UNAUTHORIZED:
                msg = "HackerOne rejected the API username or token"
                raise CredentialsError(msg) from exc
            if exc.code == HTTP_TOO_MANY and attempt < MAX_RETRIES - 1:
                delay = _int(exc.headers.get("Retry-After")) or RETRY_AFTER_DEFAULT
                logger.info("hackerone rate limited, waiting", seconds=delay)
                time.sleep(min(delay, 60))
                continue
            msg = f"HackerOne returned {exc.code}"
            raise HackerOneError(msg) from exc
        except Exception as exc:
            raise HackerOneError(str(exc)) from exc
    msg = "HackerOne rate limit did not clear"
    raise HackerOneError(msg)


def _paged(path: str, auth: tuple[str, str]) -> list[dict]:
    """Every page of a collection, following the API's own next link."""
    rows: list[dict] = []
    payload = _request(path, {"page[size]": PAGE_SIZE}, auth)
    for _ in range(MAX_PAGES):
        rows.extend(payload.get("data") or [])
        next_url = (payload.get("links") or {}).get("next")
        if not next_url:
            break
        payload = _get(next_url, auth)
    return rows


def _int(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _float(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _dt(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_programs(auth: tuple[str, str]) -> list[dict]:
    """Every program the token can see, public and private."""
    return _paged("/programs", auth)


def fetch_scopes(handle: str, auth: tuple[str, str]) -> list[dict]:
    """In-scope and out-of-scope assets for one program."""
    quoted = urllib.parse.quote(handle, safe="")
    return _paged(f"/programs/{quoted}/structured_scopes", auth)


def verify(auth: tuple[str, str]) -> dict:
    """One cheap call down the same path a sync uses, to prove the credentials work."""
    payload = _request("/programs", {"page[size]": 1}, auth)
    rows = payload.get("data") or []
    sample = ((rows[0] if rows else {}).get("attributes") or {}).get("handle")
    return {"programs_visible": len(rows), "sample_handle": sample}


def _url(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value if value and len(value) <= MAX_PICTURE_URL else None


def _program_row(entry: dict) -> dict:
    attrs = entry.get("attributes") or {}
    handle = strip_control(str(attrs.get("handle") or ""))[:200]
    return {
        "platform": BountyPlatform.HACKERONE.value,
        "handle": handle,
        "name": strip_control(str(attrs.get("name") or handle))[:300],
        "url": f"https://hackerone.com/{handle}" if handle else None,
        "profile_picture": _url(attrs.get("profile_picture")),
        "program_state": program_state(attrs.get("state")).value,
        "raw_state": (str(attrs["state"])[:32] if attrs.get("state") else None),
        "joined": bool(attrs.get("last_invitation_accepted_at_for_user")),
        "joined_at": _dt(attrs.get("last_invitation_accepted_at_for_user")),
        "submission_state": submission_state(attrs.get("submission_state")).value,
        "offers_bounties": bool(attrs.get("offers_bounties")),
        "open_scope": attrs.get("open_scope"),
        "gold_standard_safe_harbor": attrs.get("gold_standard_safe_harbor"),
        "currency": (str(attrs["currency"])[:16] if attrs.get("currency") else None),
        "started_accepting_at": _dt(attrs.get("started_accepting_at")),
        "bookmarked": bool(attrs.get("bookmarked")),
        "reports_for_user": _int(attrs.get("number_of_reports_for_user")),
        "earnings_for_user": _float(attrs.get("bounty_earned_for_user")),
        "synced_at": utc_now(),
    }


def _scope_row(program_id, entry: dict) -> dict | None:
    attrs = entry.get("attributes") or {}
    asset_type = str(attrs.get("asset_type") or "").upper()
    identifier = strip_control(str(attrs.get("asset_identifier") or "")).strip()
    if not identifier:
        return None
    resolved = target_for_scope(asset_type, identifier)
    instruction = attrs.get("instruction")
    return {
        "program_id": program_id,
        "asset_type": asset_type[:48] or "UNKNOWN",
        "asset_identifier": identifier[:1000],
        "scope_state": scope_state(attrs.get("eligible_for_submission")).value,
        "eligible_for_bounty": attrs.get("eligible_for_bounty"),
        "max_severity": (
            str(attrs.get("max_severity"))[:16] if attrs.get("max_severity") else None
        ),
        "instruction": (
            strip_control(str(instruction))[:MAX_INSTRUCTION] if instruction else None
        ),
        "reference": (
            strip_control(str(attrs.get("reference")))[:500]
            if attrs.get("reference")
            else None
        ),
        "target_value": resolved[0] if resolved else None,
        "target_type": resolved[1] if resolved else None,
        "synced_at": utc_now(),
    }


def _event(program: BountyProgram, kind: str, **extra) -> BountyEventRow:
    return BountyEventRow(
        platform=program.platform,
        program_id=program.id,
        handle=program.handle,
        program_name=program.name,
        kind=kind,
        **extra,
    )


def _program_changes(current: BountyProgram, row: dict) -> list[str]:
    """What moved on a program the library already knew about."""
    kinds: list[str] = []
    if current.submission_state != row["submission_state"]:
        kinds.append(
            BountyEvent.SUBMISSIONS_OPENED.value
            if row["submission_state"] == SubmissionState.OPEN.value
            else BountyEvent.SUBMISSIONS_CLOSED.value
        )
    if (
        current.program_state != row["program_state"]
        and row["program_state"] == "public"
    ):
        kinds.append(BountyEvent.PROGRAM_WENT_PUBLIC.value)
    if row["offers_bounties"] and not current.offers_bounties:
        kinds.append(BountyEvent.BOUNTIES_STARTED.value)
    return kinds


def sync_programs(session: Session, auth: tuple[str, str]) -> dict[str, int]:
    """Refresh the program list; scopes are fetched per program on demand."""
    started = time.monotonic()
    entries = fetch_programs(auth)
    existing = {
        (p.platform, p.handle): p
        for p in session.execute(
            select(BountyProgram).where(
                BountyProgram.platform == BountyPlatform.HACKERONE.value
            )
        ).scalars()
    }
    # a first library sync is a baseline, not 630 new programs
    baseline = bool(existing)
    created = updated = 0
    seen: set[str] = set()
    events: list[BountyEventRow] = []
    for entry in entries:
        row = _program_row(entry)
        if not row["handle"] or row["handle"] in seen:
            continue
        seen.add(row["handle"])
        current = existing.get((row["platform"], row["handle"]))
        if current is None:
            program = BountyProgram(**row)
            session.add(program)
            session.flush()
            created += 1
            if baseline:
                events.append(_event(program, BountyEvent.PROGRAM_ADDED.value))
            continue
        for kind in _program_changes(current, row):
            events.append(_event(current, kind))
        for key, value in row.items():
            setattr(current, key, value)
        updated += 1
    session.add_all(events)
    session.commit()
    return {
        "programs": len(seen),
        "created": created,
        "updated": updated,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "events": len(events),
    }


_SCOPE_TRANSITIONS = {
    (ScopeState.IN_SCOPE.value, ScopeState.OUT_OF_SCOPE.value): (
        BountyEvent.WENT_OUT_OF_SCOPE.value
    ),
    (ScopeState.OUT_OF_SCOPE.value, ScopeState.IN_SCOPE.value): (
        BountyEvent.CAME_INTO_SCOPE.value
    ),
}


def _scope_changes(
    program: BountyProgram, before: dict[tuple[str, str], str], after: dict
) -> list[BountyEventRow]:
    """Added, removed and flipped assets — never on a program's first read."""
    events: list[BountyEventRow] = []
    for key, row in after.items():
        asset_type, identifier = key
        was = before.get(key)
        if was is None:
            kind = BountyEvent.SCOPE_ADDED.value
        else:
            kind = _SCOPE_TRANSITIONS.get((was, row["scope_state"]))
            if kind is None:
                continue
        events.append(
            _event(
                program,
                kind,
                asset_type=asset_type,
                asset_identifier=identifier,
                detail=(row.get("instruction") or None)
                and row["instruction"][:MAX_EVENT_DETAIL],
            )
        )
    for key in before.keys() - after.keys():
        events.append(
            _event(
                program,
                BountyEvent.SCOPE_REMOVED.value,
                asset_type=key[0],
                asset_identifier=key[1],
            )
        )
    return events


def sync_scopes(session: Session, program: BountyProgram, auth: tuple[str, str]) -> int:
    """Replace one program's scope rows with what the platform reports now."""
    entries = fetch_scopes(program.handle, auth)
    rows = [r for r in (_scope_row(program.id, e) for e in entries) if r]
    deduped: dict[tuple[str, str], dict] = {}
    for row in rows:
        deduped[(row["asset_type"], row["asset_identifier"])] = row

    # a program read for the first time is a baseline, not a scope change
    before: dict[tuple[str, str], str] = {}
    if program.scopes_synced_at is not None:
        before = {
            (s.asset_type, s.asset_identifier): s.scope_state
            for s in session.execute(
                select(BountyScope).where(BountyScope.program_id == program.id)
            ).scalars()
        }
        session.add_all(_scope_changes(program, before, deduped))

    # a program restates its whole scope, so the set is replaced not merged
    session.execute(delete(BountyScope).where(BountyScope.program_id == program.id))
    session.add_all([BountyScope(**row) for row in deduped.values()])
    program.scopes_synced_at = utc_now()
    session.commit()
    return len(deduped)


def sync_settings(session: Session) -> tuple[str, datetime | None]:
    row = session.execute(
        text(
            "SELECT bounty_sync_interval, bounty_synced_at FROM instance_settings LIMIT 1"
        )
    ).first()
    if not row:
        return DEFAULT_SYNC_INTERVAL, None
    return (row[0] or DEFAULT_SYNC_INTERVAL), row[1]


def sync_due(session: Session) -> bool:
    """Whether the schedule says to sync now. A manual refresh never asks."""
    interval, last = sync_settings(session)
    hours = SYNC_INTERVAL_HOURS.get(interval)
    if hours is None:
        return False
    return last is None or (utc_now() - last) >= timedelta(hours=hours)


def mark_synced(session: Session) -> None:
    session.execute(text("UPDATE instance_settings SET bounty_synced_at = now()"))
    session.commit()


def unreachable_summary(scopes: list[BountyScope]) -> dict[str, int]:
    """What the program lists that no scan can reach, counted by asset type label."""
    counts: dict[str, int] = {}
    for scope in scopes:
        if scope.target_value:
            continue
        label = asset_type_spec(scope.asset_type).label
        counts[label] = counts.get(label, 0) + 1
    return counts
