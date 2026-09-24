"""HackerOne: programs and structured scopes from the hacker API."""

from __future__ import annotations

import urllib.parse
from typing import ClassVar

from sqlalchemy.orm import Session

from shared.definitions.bounty_programs import (
    BountyPlatform,
    ProgramSource,
    program_state,
    scope_state,
    submission_state,
    target_for_scope,
)
from shared.definitions.bounty_reports import (
    MAX_CURRENCY,
    MAX_REPORT_TITLE,
    MAX_WEAKNESS,
    report_severity,
)
from shared.enums.api_key import APIProvider
from shared.models.bounty_program import BountyProgram
from shared.services.bounty_providers.base import (
    MAX_INSTRUCTION,
    BountyProvider,
    JsonClient,
    ReportFetch,
    ScopeFetch,
    api_key_row,
    as_datetime,
    as_float,
    as_int,
    as_url,
    decrypted,
)
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

BASE_URL = "https://api.hackerone.com/v1/hackers"
PAGE_SIZE = 100
MAX_PAGES = 200
PAYOUT_CURRENCY = "USD"


class HackerOneProvider(BountyProvider):
    platform: ClassVar[str] = BountyPlatform.HACKERONE.value
    api_provider: ClassVar[APIProvider] = APIProvider.HACKERONE
    label: ClassVar[str] = "HackerOne"

    def __init__(self, username: str, token: str) -> None:
        self.username = username
        self.client = JsonClient(
            label=self.label,
            headers={"Authorization": _basic(username, token)},
        )

    @classmethod
    def from_session(cls, session: Session) -> HackerOneProvider | None:
        row = api_key_row(session, cls.api_provider)
        if not row:
            return None
        username = (row.key_meta or {}).get("username")
        token = decrypted(row)
        if not username or not token:
            return None
        return cls(str(username), token)

    def account(self) -> str | None:
        return self.username

    def _paged(self, path: str) -> list[dict]:
        rows: list[dict] = []
        payload = self.client.get(f"{BASE_URL}{path}", {"page[size]": PAGE_SIZE})
        for _ in range(MAX_PAGES):
            rows.extend(payload.get("data") or [])
            next_url = (payload.get("links") or {}).get("next")
            if not next_url:
                break
            payload = self.client.get(next_url)
        return rows

    def programs(self) -> list[dict]:
        return [_program_row(e) for e in self._paged("/programs")]

    def scopes(self, program: BountyProgram) -> ScopeFetch:
        quoted = urllib.parse.quote(program.handle, safe="")
        entries = self._paged(f"/programs/{quoted}/structured_scopes")
        return ScopeFetch(entries=[r for r in (_scope_row(e) for e in entries) if r])

    def own_reports(self) -> ReportFetch:
        entries = self._paged("/me/reports")
        earnings = self._paged("/payments/earnings")
        return ReportFetch(
            reports=[r for r in (_report_row(e) for e in entries) if r],
            awards=[a for a in (_award_row(e) for e in earnings) if a],
            account=_account(entries),
        )

    def verify(self) -> dict:
        payload = self.client.get(f"{BASE_URL}/programs", {"page[size]": 1})
        rows = payload.get("data") or []
        sample = ((rows[0] if rows else {}).get("attributes") or {}).get("handle")
        return {
            "account": self.username,
            "programs_visible": len(rows),
            "sample_handle": sample,
        }


def _basic(username: str, token: str) -> str:
    import base64  # noqa: PLC0415

    return "Basic " + base64.b64encode(f"{username}:{token}".encode()).decode()


def _program_row(entry: dict) -> dict:
    attrs = entry.get("attributes") or {}
    handle = strip_control(str(attrs.get("handle") or ""))[:200]
    return {
        "platform": BountyPlatform.HACKERONE.value,
        "source": ProgramSource.API.value,
        "external_id": (str(entry["id"])[:100] if entry.get("id") else None),
        "handle": handle,
        "name": strip_control(str(attrs.get("name") or handle))[:300],
        "url": f"https://hackerone.com/{handle}" if handle else None,
        "profile_picture": as_url(attrs.get("profile_picture")),
        "program_state": program_state(attrs.get("state")).value,
        "raw_state": (str(attrs["state"])[:32] if attrs.get("state") else None),
        "joined": bool(attrs.get("last_invitation_accepted_at_for_user")),
        "joined_at": as_datetime(attrs.get("last_invitation_accepted_at_for_user")),
        "submission_state": submission_state(attrs.get("submission_state")).value,
        "offers_bounties": bool(attrs.get("offers_bounties")),
        "open_scope": attrs.get("open_scope"),
        "gold_standard_safe_harbor": attrs.get("gold_standard_safe_harbor"),
        "currency": (str(attrs["currency"])[:16] if attrs.get("currency") else None),
        "started_accepting_at": as_datetime(attrs.get("started_accepting_at")),
        "bookmarked": bool(attrs.get("bookmarked")),
        "reports_for_user": as_int(attrs.get("number_of_reports_for_user")),
        "earnings_for_user": as_float(attrs.get("bounty_earned_for_user")),
        "synced_at": utc_now(),
    }


def _scope_row(entry: dict) -> dict | None:
    attrs = entry.get("attributes") or {}
    asset_type = str(attrs.get("asset_type") or "").upper()
    identifier = strip_control(str(attrs.get("asset_identifier") or "")).strip()
    if not identifier:
        return None
    resolved = target_for_scope(asset_type, identifier)
    instruction = attrs.get("instruction")
    return {
        "asset_type": asset_type[:48] or "UNKNOWN",
        "asset_identifier": identifier[:1000],
        "scope_state": scope_state(attrs.get("eligible_for_submission")).value,
        "eligible_for_bounty": attrs.get("eligible_for_bounty"),
        "max_severity": (
            str(attrs.get("max_severity"))[:16] if attrs.get("max_severity") else None
        ),
        "tier": None,
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


def _related(entry: dict, name: str) -> dict:
    data = ((entry.get("relationships") or {}).get(name) or {}).get("data")
    return data if isinstance(data, dict) else {}


def _attr(entry: dict, name: str) -> dict:
    return _related(entry, name).get("attributes") or {}


def _text(raw: object, limit: int) -> str | None:
    value = strip_control(str(raw or "")).strip()
    return value[:limit] or None


def _report_row(entry: dict) -> dict | None:
    attrs = entry.get("attributes") or {}
    if not entry.get("id"):
        return None
    severity = _attr(entry, "severity")
    scope = _attr(entry, "structured_scope")
    return {
        "external_id": str(entry["id"])[:100],
        "program_handle": _text(_attr(entry, "program").get("handle"), 200),
        "title": _text(attrs.get("title"), MAX_REPORT_TITLE) or f"#{entry['id']}",
        "state": str(attrs.get("state") or "")[:32],
        "severity": report_severity(severity.get("rating")),
        "severity_score": as_float(severity.get("score")),
        "weakness": _text(_attr(entry, "weakness").get("name"), MAX_WEAKNESS),
        "asset_type": _text(scope.get("asset_type"), 48),
        "asset_identifier": _text(scope.get("asset_identifier"), 1000),
        "submitted_at": as_datetime(attrs.get("submitted_at")),
        "triaged_at": as_datetime(attrs.get("triaged_at")),
        "closed_at": as_datetime(attrs.get("closed_at")),
        "bounty_awarded_at": as_datetime(attrs.get("bounty_awarded_at")),
        "disclosed_at": as_datetime(attrs.get("disclosed_at")),
        "last_program_activity_at": as_datetime(attrs.get("last_program_activity_at")),
    }


def _award_row(entry: dict) -> dict | None:
    if not entry.get("id"):
        return None
    attrs = entry.get("attributes") or {}
    bounty = _related(entry, "bounty")
    paid = bounty.get("attributes") or {}
    program = _attr(entry, "program")
    amount = as_float(paid.get("awarded_amount"))
    if amount is None:
        amount = as_float(attrs.get("amount"))
    if amount is None:
        return None
    currency = (
        paid.get("awarded_currency") or program.get("currency") or PAYOUT_CURRENCY
    )
    return {
        "external_id": str(entry["id"])[:100],
        "report_external_id": _text(_related(bounty, "report").get("id"), 100),
        "program_handle": _text(program.get("handle"), 200),
        "program_name": _text(program.get("name"), 300),
        "amount": amount,
        "bonus": as_float(paid.get("awarded_bonus_amount")) or 0.0,
        "currency": str(currency).upper()[:MAX_CURRENCY],
        "awarded_at": as_datetime(paid.get("created_at") or attrs.get("created_at")),
    }


def _account(entries: list[dict]) -> dict:
    """The reporter record every report carries."""
    for entry in entries:
        reporter = _attr(entry, "reporter")
        if reporter:
            return {
                "username": _text(reporter.get("username"), 200),
                "reputation": as_int(reporter.get("reputation")),
                "signal": as_float(reporter.get("signal")),
                "impact": as_float(reporter.get("impact")),
            }
    return {}
