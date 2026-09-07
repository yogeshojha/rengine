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
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shared.definitions.bounty_programs import (
    BountyPlatform,
    asset_type_spec,
    program_state,
    scope_state,
    submission_state,
    target_for_scope,
)
from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.api_key import APIKey
from shared.models.bounty_program import BountyProgram, BountyScope
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
    created = updated = 0
    seen: set[str] = set()
    for entry in entries:
        row = _program_row(entry)
        if not row["handle"] or row["handle"] in seen:
            continue
        seen.add(row["handle"])
        current = existing.get((row["platform"], row["handle"]))
        if current is None:
            session.add(BountyProgram(**row))
            created += 1
            continue
        for key, value in row.items():
            setattr(current, key, value)
        updated += 1
    session.commit()
    return {
        "programs": len(seen),
        "created": created,
        "updated": updated,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def sync_scopes(session: Session, program: BountyProgram, auth: tuple[str, str]) -> int:
    """Replace one program's scope rows with what the platform reports now."""
    entries = fetch_scopes(program.handle, auth)
    rows = [r for r in (_scope_row(program.id, e) for e in entries) if r]
    # a program restates its whole scope, so the set is replaced not merged
    session.execute(delete(BountyScope).where(BountyScope.program_id == program.id))
    deduped: dict[tuple[str, str], dict] = {}
    for row in rows:
        deduped[(row["asset_type"], row["asset_identifier"])] = row
    session.add_all([BountyScope(**row) for row in deduped.values()])
    program.scopes_synced_at = utc_now()
    session.commit()
    return len(deduped)


def unreachable_summary(scopes: list[BountyScope]) -> dict[str, int]:
    """What the program lists that no scan can reach, counted by asset type label."""
    counts: dict[str, int] = {}
    for scope in scopes:
        if scope.target_value:
            continue
        label = asset_type_spec(scope.asset_type).label
        counts[label] = counts.get(label, 0) + 1
    return counts
