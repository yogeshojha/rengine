"""Intigriti: programs, typed scope and the platform's own scope-change feed."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from sqlalchemy.orm import Session

from shared.definitions.bounty_programs import (
    BountyPlatform,
    ProgramSource,
    ProgramState,
    ScopeState,
    SubmissionState,
    scope_tier,
    target_for_scope,
)
from shared.enums.api_key import APIProvider
from shared.models.bounty_program import BountyProgram
from shared.services.bounty_providers.base import (
    HTTP_FORBIDDEN,
    HTTP_TOO_MANY,
    MAX_INSTRUCTION,
    BountyProvider,
    BountyProviderError,
    JsonClient,
    ScopeFetch,
    api_key_row,
    as_float,
    decrypted,
)
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

BASE_URL = "https://api.intigriti.com/external/researcher/v1"
WEB_URL = "https://app.intigriti.com/researcher"
PAGE_SIZE = 500
MAX_PAGES = 40
MIN_INTERVAL = 0.5
DENIED_CODE = "FORBID001"

# confidentialityLevel
LEVEL_PUBLIC = 4

# status
STATUS_SUBMISSION = {
    3: SubmissionState.OPEN.value,
    4: SubmissionState.PAUSED.value,
    5: SubmissionState.CLOSED.value,
}

# domains.content[].type, read off the live API
ASSET_TYPES: dict[int, str] = {
    1: "URL",
    2: "GOOGLE_PLAY_APP_ID",
    3: "APPLE_STORE_APP_ID",
    4: "CIDR",
    5: "HARDWARE",
    6: "OTHER",
    7: "WILDCARD",
    8: "SOURCE_CODE",
}

# domains.content[].tier ids are not ordered: 1 is No Bounty, 4 is Tier 1, 5 is out of scope
TIER_OUT_OF_SCOPE = 5
OUT_OF_SCOPE_LABEL = "out of scope"
NO_BOUNTY_LABEL = "no bounty"


class IntigritiProvider(BountyProvider):
    platform: ClassVar[str] = BountyPlatform.INTIGRITI.value
    api_provider: ClassVar[APIProvider] = APIProvider.INTIGRITI
    label: ClassVar[str] = "Intigriti"

    def __init__(self, token: str) -> None:
        self.client = JsonClient(
            label=self.label,
            headers={"Authorization": f"Bearer {token}"},
            min_interval=MIN_INTERVAL,
            rate_limit_codes=(HTTP_FORBIDDEN, HTTP_TOO_MANY),
            denied_marker=DENIED_CODE,
        )

    @classmethod
    def from_session(cls, session: Session) -> IntigritiProvider | None:
        row = api_key_row(session, cls.api_provider)
        if not row:
            return None
        token = decrypted(row)
        return cls(token) if token else None

    def _paged(self, path: str, params: dict | None = None) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        for _ in range(MAX_PAGES):
            payload = self.client.get(
                f"{BASE_URL}{path}",
                {**(params or {}), "limit": PAGE_SIZE, "offset": offset},
            )
            records = payload.get("records") or []
            rows.extend(records)
            offset += len(records)
            if not records or offset >= (payload.get("maxCount") or 0):
                break
        return rows

    def programs(self) -> list[dict]:
        return [r for r in (_program_row(e) for e in self._paged("/programs")) if r]

    def scopes(self, program: BountyProgram) -> ScopeFetch:
        if not program.external_id:
            msg = f"{self.label} program {program.handle} has no platform id"
            raise BountyProviderError(msg)
        payload = self.client.get(f"{BASE_URL}/programs/{program.external_id}")
        content = ((payload.get("domains") or {}).get("content")) or []
        return ScopeFetch(
            entries=[r for r in (_scope_row(e) for e in content) if r],
            program_updates={
                "joined": program.program_state == ProgramState.PRIVATE.value
            },
        )

    def changed_since(self, since: datetime | None) -> set[str] | None:
        if since is None:
            return None
        records = self._paged(
            "/programs/activities", {"createdSince": int(since.timestamp())}
        )
        return {str(r["programId"]) for r in records if r.get("programId")}

    def verify(self) -> dict:
        payload = self.client.get(f"{BASE_URL}/programs", {"limit": 1, "offset": 0})
        records = payload.get("records") or []
        return {
            "programs_visible": payload.get("maxCount") or len(records),
            "sample_handle": (records[0].get("handle") if records else None),
        }


def _enum_id(entry: dict, key: str) -> int | None:
    value = (entry.get(key) or {}).get("id")
    return value if isinstance(value, int) else None


def _enum_value(entry: dict, key: str) -> str | None:
    value = (entry.get(key) or {}).get("value")
    return strip_control(str(value)).strip() if value else None


def _money(entry: dict, key: str) -> tuple[float | None, str | None]:
    money = entry.get(key) or {}
    currency = money.get("currency")
    return as_float(money.get("value")), (str(currency)[:16] if currency else None)


def _program_url(entry: dict) -> str | None:
    raw = str((entry.get("webLinks") or {}).get("detail") or "").strip()
    if not raw:
        return None
    if raw.startswith("http"):
        return raw[:500]
    path = raw.split("=", 1)[1] if "=" in raw else raw
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{WEB_URL}{path}"[:500]


def _program_row(entry: dict) -> dict | None:
    handle = strip_control(str(entry.get("handle") or "")).strip()[:200]
    external_id = str(entry.get("id") or "").strip()[:100]
    if not handle or not external_id:
        return None
    level = _enum_id(entry, "confidentialityLevel")
    low, _ = _money(entry, "minBounty")
    high, currency = _money(entry, "maxBounty")
    return {
        "platform": BountyPlatform.INTIGRITI.value,
        "source": ProgramSource.API.value,
        "external_id": external_id,
        "handle": handle,
        "name": strip_control(str(entry.get("name") or handle))[:300],
        "url": _program_url(entry),
        "profile_picture": None,
        "program_state": (
            ProgramState.PUBLIC if level == LEVEL_PUBLIC else ProgramState.PRIVATE
        ).value,
        "raw_state": (_enum_value(entry, "confidentialityLevel") or "")[:32] or None,
        "submission_state": STATUS_SUBMISSION.get(
            _enum_id(entry, "status") or 0, SubmissionState.UNKNOWN.value
        ),
        "offers_bounties": bool(high and high > 0),
        "open_scope": None,
        "gold_standard_safe_harbor": None,
        "currency": currency,
        "started_accepting_at": None,
        "bookmarked": bool(entry.get("following")),
        "reports_for_user": None,
        "earnings_for_user": None,
        "min_payout": low,
        "max_payout": high,
        "payout_currency": currency,
        "safe_harbor": None,
        "requires_2fa": None,
        "synced_at": utc_now(),
    }


def _scope_row(entry: dict) -> dict | None:
    identifier = strip_control(str(entry.get("endpoint") or "")).strip()
    if not identifier:
        return None
    asset_type = ASSET_TYPES.get(_enum_id(entry, "type") or 0, "OTHER")
    label = (_enum_value(entry, "tier") or "").strip().lower()
    out_of_scope = (
        _enum_id(entry, "tier") == TIER_OUT_OF_SCOPE or label == OUT_OF_SCOPE_LABEL
    )
    resolved = target_for_scope(asset_type, identifier)
    description = entry.get("description")
    return {
        "asset_type": asset_type,
        "asset_identifier": identifier[:1000],
        "scope_state": (
            ScopeState.OUT_OF_SCOPE if out_of_scope else ScopeState.IN_SCOPE
        ).value,
        "eligible_for_bounty": (
            None if out_of_scope or not label else label != NO_BOUNTY_LABEL
        ),
        "max_severity": None,
        "tier": None if out_of_scope else scope_tier(_enum_value(entry, "tier")),
        "instruction": (
            strip_control(str(description))[:MAX_INSTRUCTION] if description else None
        ),
        "reference": None,
        "target_value": resolved[0] if resolved else None,
        "target_type": resolved[1] if resolved else None,
        "synced_at": utc_now(),
    }
