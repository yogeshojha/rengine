"""Public program scope for Bugcrowd, Intigriti and YesWeHack.

One JSON file per platform, no key and no account. A file that fails to download
leaves its platform untouched, exactly as the exploitation feeds do.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shared.definitions.bounty_feed import (
    BASE_URL,
    FEEDS,
    SCOPE_KEYS,
    FeedSpec,
    asset_type,
    handle_for,
    payout,
)
from shared.definitions.bounty_programs import (
    SYNC_INTERVAL_HOURS,
    ProgramSource,
    ProgramState,
    SubmissionState,
    scope_state,
    target_for_scope,
)
from shared.logging import get_logger
from shared.models.bounty_program import BountyProgram, BountyScope
from shared.services.bounty_programs import _event, _scope_changes
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

TIMEOUT = 120
MAX_FEED_BYTES = 64 * 1024 * 1024
USER_AGENT = "reNgine"
MAX_INSTRUCTION = 4000


class FeedError(RuntimeError):
    pass


def _download(spec: FeedSpec) -> list[dict]:
    url = f"{BASE_URL}/{spec.file}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            raw = response.read(MAX_FEED_BYTES)
    except urllib.error.HTTPError as exc:
        msg = f"{spec.file} returned {exc.code}"
        raise FeedError(msg) from exc
    except Exception as exc:
        raise FeedError(str(exc)) from exc
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError as exc:
        msg = f"{spec.file} is not valid JSON"
        raise FeedError(msg) from exc
    if isinstance(data, dict):
        data = data.get("programs") or []
    if not isinstance(data, list):
        msg = f"{spec.file} did not contain a program list"
        raise FeedError(msg)
    return data


def _submission_state(entry: dict) -> str:
    """Only report a state the platform actually tells us."""
    if "status" in entry:
        return (
            SubmissionState.OPEN.value
            if str(entry.get("status")).lower() == "open"
            else SubmissionState.CLOSED.value
        )
    if "disabled" in entry:
        return (
            SubmissionState.CLOSED.value
            if entry.get("disabled")
            else SubmissionState.OPEN.value
        )
    return SubmissionState.UNKNOWN.value


def _program_row(spec: FeedSpec, entry: dict, handle: str) -> dict:
    low, high, currency = payout(entry)
    safe_harbor = entry.get("safe_harbor")
    return {
        "platform": spec.platform,
        "source": ProgramSource.FEED.value,
        "handle": handle,
        "name": strip_control(str(entry.get("name") or handle))[:300],
        "url": (str(entry.get("url"))[:500] if entry.get("url") else None),
        "program_state": ProgramState.PUBLIC.value,
        "raw_state": "public",
        "submission_state": _submission_state(entry),
        # a range or a maximum is the only bounty signal these platforms give
        "offers_bounties": bool(high),
        "min_payout": low,
        "max_payout": high,
        "payout_currency": currency,
        "safe_harbor": (str(safe_harbor)[:32] if safe_harbor else None),
        "requires_2fa": entry.get("twoFactorRequired"),
        "joined": False,
        "bookmarked": False,
        "synced_at": utc_now(),
    }


def _scope_rows(spec: FeedSpec, entry: dict, program_id) -> dict:
    rows: dict[tuple[str, str], dict] = {}
    targets = entry.get("targets") or {}
    for key, state in SCOPE_KEYS.items():
        for asset in targets.get(key) or []:
            if not isinstance(asset, dict):
                continue
            identifier = strip_control(str(asset.get(spec.asset_field) or "")).strip()
            if not identifier:
                continue
            kind = asset_type(spec, asset.get("type"))
            resolved = target_for_scope(kind, identifier)
            note = asset.get("description") or asset.get("name")
            rows[(kind, identifier[:1000])] = {
                "program_id": program_id,
                "asset_type": kind,
                "asset_identifier": identifier[:1000],
                "scope_state": scope_state(state == SCOPE_KEYS["in_scope"]).value,
                "eligible_for_bounty": None,
                "max_severity": None,
                "instruction": (
                    strip_control(str(note))[:MAX_INSTRUCTION] if note else None
                ),
                "reference": None,
                "target_value": resolved[0] if resolved else None,
                "target_type": resolved[1] if resolved else None,
                "synced_at": utc_now(),
            }
    return rows


def sync_platform(session: Session, spec: FeedSpec) -> dict:
    """Refresh one platform. Its rows are only touched if the file downloaded."""
    entries = _download(spec)
    existing = {
        p.handle: p
        for p in session.execute(
            select(BountyProgram).where(BountyProgram.platform == spec.platform)
        ).scalars()
    }
    baseline = bool(existing)
    created = updated = assets = 0
    seen: set[str] = set()
    for entry in entries:
        handle = handle_for(spec.platform, entry)
        if not handle or handle in seen:
            continue
        seen.add(handle)
        row = _program_row(spec, entry, handle)
        program = existing.get(handle)
        if program is None:
            program = BountyProgram(**row)
            session.add(program)
            session.flush()
            created += 1
            if baseline:
                session.add(_event(program, "program_added"))
        else:
            # an API row is authoritative; the feed never overwrites one
            if program.source == ProgramSource.API.value:
                continue
            for key, value in row.items():
                setattr(program, key, value)
            updated += 1

        wanted = _scope_rows(spec, entry, program.id)
        before: dict[tuple[str, str], str] = {}
        if program.scopes_synced_at is not None:
            before = {
                (s.asset_type, s.asset_identifier): s.scope_state
                for s in session.execute(
                    select(BountyScope).where(BountyScope.program_id == program.id)
                ).scalars()
            }
            session.add_all(_scope_changes(program, before, wanted))
        session.execute(
            BountyScope.__table__.delete().where(
                BountyScope.__table__.c.program_id == program.id
            )
        )
        session.add_all([BountyScope(**r) for r in wanted.values()])
        program.scopes_synced_at = utc_now()
        assets += len(wanted)
    session.commit()
    return {
        "platform": spec.platform,
        "programs": len(seen),
        "created": created,
        "updated": updated,
        "assets": assets,
    }


def sync_feeds(session: Session) -> dict:
    """Every platform the feed covers. One failure does not stop the others."""
    started = time.monotonic()
    results, errors = [], {}
    for spec in FEEDS:
        try:
            results.append(sync_platform(session, spec))
        except FeedError as exc:
            session.rollback()
            errors[spec.platform] = str(exc)
            logger.warning("bounty feed failed", platform=spec.platform, error=str(exc))
    return {
        "platforms": results,
        "errors": errors,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def feed_settings(session: Session) -> tuple[str, object]:
    row = session.execute(
        text(
            "SELECT bounty_feed_interval, bounty_feed_synced_at FROM instance_settings LIMIT 1"
        )
    ).first()
    return (row[0] if row else "six_hours"), (row[1] if row else None)


def feed_due(session: Session) -> bool:
    interval, last = feed_settings(session)
    hours = SYNC_INTERVAL_HOURS.get(interval)
    if hours is None:
        return False
    return last is None or (utc_now() - last) >= timedelta(hours=hours)


def mark_feed_synced(session: Session) -> None:
    session.execute(text("UPDATE instance_settings SET bounty_feed_synced_at = now()"))
    session.commit()
