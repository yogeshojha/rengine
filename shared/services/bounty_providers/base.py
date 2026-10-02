"""The contract a bug bounty platform with a researcher API implements."""

from __future__ import annotations

import json
import time
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.enums.api_key import APIProvider
from shared.http import get_sync_client
from shared.logging import get_logger
from shared.models.api_key import APIKey
from shared.models.bounty_program import BountyProgram
from shared.utils.net import redact_url_queries

logger = get_logger(__name__)

TIMEOUT = 30
MAX_RETRIES = 3
RETRY_AFTER_DEFAULT = 5
MAX_RETRY_SLEEP = 60
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_TOO_MANY = 429
MAX_INSTRUCTION = 4000
MAX_URL = 4000


class BountyProviderError(RuntimeError):
    pass


class CredentialsError(BountyProviderError):
    pass


class AccessDeniedError(BountyProviderError):
    """The platform refuses this read to the credential."""


@dataclass
class ScopeFetch:
    """A program's scope rows, and what the same call states about the program."""

    entries: list[dict]
    program_updates: dict = field(default_factory=dict)


@dataclass
class ReportFetch:
    """The account's own reports, the bounties paid on them and the account's standing."""

    reports: list[dict]
    awards: list[dict]
    account: dict = field(default_factory=dict)


def api_key_row(session: Session, provider: APIProvider) -> APIKey | None:
    return session.execute(
        select(APIKey).where(
            APIKey.provider == provider,
            APIKey.is_enabled.is_(True),
        )
    ).scalar_one_or_none()


class JsonClient:
    """One paced, retrying JSON GET path shared by every provider."""

    def __init__(
        self,
        *,
        label: str,
        headers: dict[str, str],
        min_interval: float = 0.0,
        rate_limit_codes: tuple[int, ...] = (HTTP_TOO_MANY,),
        denied_marker: str = "",
    ) -> None:
        self.label = label
        self.headers = {"Accept": "application/json", **headers}
        self.min_interval = min_interval
        self.rate_limit_codes = rate_limit_codes
        self.denied_marker = denied_marker
        self._last = 0.0

    def _denied(self, response: httpx.Response) -> bool:
        return bool(self.denied_marker) and self.denied_marker in response.text

    def _pace(self) -> None:
        if self.min_interval <= 0:
            return
        gap = self.min_interval - (time.monotonic() - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.monotonic()

    def get(self, url: str, params: dict | None = None) -> Any:
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        for attempt in range(MAX_RETRIES):
            self._pace()
            try:
                with get_sync_client(timeout=TIMEOUT) as client:
                    response = client.get(url, headers=self.headers)
            except httpx.HTTPError as exc:
                raise BountyProviderError(redact_url_queries(str(exc))) from None
            code = response.status_code
            if not response.is_error:
                try:
                    return json.loads(
                        response.content.decode("utf-8", errors="replace")
                    )
                except ValueError as exc:
                    raise BountyProviderError(str(exc)) from exc
            if code == HTTP_UNAUTHORIZED:
                msg = f"{self.label} rejected the credentials"
                raise CredentialsError(msg)
            if code == HTTP_FORBIDDEN and self._denied(response):
                msg = f"{self.label} returned {code}"
                raise AccessDeniedError(msg)
            if code in self.rate_limit_codes and attempt < MAX_RETRIES - 1:
                delay = (
                    as_int(response.headers.get("Retry-After")) or RETRY_AFTER_DEFAULT
                )
                logger.info(
                    "bounty provider rate limited",
                    provider=self.label,
                    seconds=delay,
                )
                time.sleep(min(delay, MAX_RETRY_SLEEP))
                continue
            msg = f"{self.label} returned {code}"
            raise BountyProviderError(msg)
        msg = f"{self.label} rate limit did not clear"
        raise BountyProviderError(msg)


class BountyProvider(ABC):
    """Reads one platform's programs and scope as rows the sync engine can store."""

    platform: ClassVar[str]
    api_provider: ClassVar[APIProvider]
    label: ClassVar[str]

    @classmethod
    @abstractmethod
    def from_session(cls, session: Session) -> BountyProvider | None:
        """The configured provider, or None when the instance has no credential."""

    @abstractmethod
    def programs(self) -> list[dict]:
        """Every program the credential can see, as program rows."""

    @abstractmethod
    def scopes(self, program: BountyProgram) -> ScopeFetch:
        """One program's scope, as scope rows."""

    @abstractmethod
    def verify(self) -> dict:
        """One call down the sync path that checks the credential."""

    def changed_since(self, since: datetime | None) -> set[str] | None:  # noqa: ARG002
        """Platform ids whose scope moved since a time. None when it cannot be asked."""
        return None

    def own_reports(self) -> ReportFetch | None:
        """The account's reports and bounties. None when the platform has no such read."""
        return None


def as_int(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def as_float(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def as_datetime(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def as_url(raw: Any) -> str | None:
    value = str(raw or "").strip()
    return value if value and len(value) <= MAX_URL else None
