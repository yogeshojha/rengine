"""The contract a bug bounty platform with a researcher API implements."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.enums.api_key import APIProvider
from shared.logging import get_logger
from shared.models.api_key import APIKey
from shared.models.bounty_program import BountyProgram
from shared.utils.crypto import try_decrypt

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
    """The platform will not show this to the credential. Retrying cannot help."""


@dataclass
class ScopeFetch:
    """A program's scope rows, and what the same call states about the program."""

    entries: list[dict]
    program_updates: dict = field(default_factory=dict)


def api_key_row(session: Session, provider: APIProvider) -> APIKey | None:
    return session.execute(
        select(APIKey).where(
            APIKey.provider == provider,
            APIKey.is_enabled == True,  # noqa: E712
        )
    ).scalar_one_or_none()


def decrypted(row: APIKey) -> str:
    return str(try_decrypt(row.key_value) or row.key_value)


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
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "reNgine",
            **headers,
        }
        self.min_interval = min_interval
        self.rate_limit_codes = rate_limit_codes
        self.denied_marker = denied_marker
        self._last = 0.0

    def _denied(self, exc: urllib.error.HTTPError) -> bool:
        """A refusal the credential cannot retry past, told apart from an overage."""
        if not self.denied_marker:
            return False
        try:
            return self.denied_marker in exc.read().decode("utf-8", errors="replace")
        except Exception:
            return False

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
        request = urllib.request.Request(url, headers=self.headers)  # noqa: S310
        for attempt in range(MAX_RETRIES):
            self._pace()
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
                    return json.loads(response.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as exc:
                if exc.code == HTTP_UNAUTHORIZED:
                    msg = f"{self.label} rejected the credentials"
                    raise CredentialsError(msg) from exc
                if exc.code == HTTP_FORBIDDEN and self._denied(exc):
                    msg = f"{self.label} returned {exc.code}"
                    raise AccessDeniedError(msg) from exc
                if exc.code in self.rate_limit_codes and attempt < MAX_RETRIES - 1:
                    delay = (
                        as_int(exc.headers.get("Retry-After")) or RETRY_AFTER_DEFAULT
                    )
                    logger.info(
                        "bounty provider rate limited",
                        provider=self.label,
                        seconds=delay,
                    )
                    time.sleep(min(delay, MAX_RETRY_SLEEP))
                    continue
                msg = f"{self.label} returned {exc.code}"
                raise BountyProviderError(msg) from exc
            except BountyProviderError:
                raise
            except Exception as exc:
                raise BountyProviderError(str(exc)) from exc
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

    @classmethod
    def configured(cls, session: Session) -> bool:
        return cls.from_session(session) is not None

    @abstractmethod
    def programs(self) -> list[dict]:
        """Every program the credential can see, as program rows."""

    @abstractmethod
    def scopes(self, program: BountyProgram) -> ScopeFetch:
        """One program's scope, as scope rows."""

    @abstractmethod
    def verify(self) -> dict:
        """One cheap call down the sync path, to prove the credential works."""

    def changed_since(self, since: datetime | None) -> set[str] | None:  # noqa: ARG002
        """Platform ids whose scope moved since a time. None when it cannot be asked."""
        return None

    def account(self) -> str | None:
        """The account name, when the platform states one."""
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
