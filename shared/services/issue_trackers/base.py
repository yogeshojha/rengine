"""The contract an issue tracker implements, and the one HTTP path they share."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx

from shared.definitions.issue_trackers import (
    TRACKERS_BY_KIND,
    TrackerSpec,
)
from shared.http import get_sync_client
from shared.logging import get_logger
from shared.services.issue_trackers.document import Doc
from shared.utils.net import redact_url_queries, validate_public_https_url

logger = get_logger(__name__)

TIMEOUT = 30
MAX_RETRIES = 3
RETRY_AFTER_DEFAULT = 5
MAX_RETRY_SLEEP = 60
MAX_REMOTE_MESSAGE = 300
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_GONE = 410
HTTP_TOO_MANY = 429
HTTP_ERROR = 400
HTTP_REDIRECT = 300
GONE = frozenset({HTTP_NOT_FOUND, HTTP_GONE})


class TrackerError(RuntimeError):
    pass


class CredentialsError(TrackerError):
    pass


class RemoteNotFoundError(TrackerError):
    pass


class RateLimitedError(TrackerError):
    pass


@dataclass(frozen=True)
class RemoteIssue:
    key: str
    external_id: str
    url: str


@dataclass(frozen=True)
class RemoteStatus:
    name: str
    category: str | None


@dataclass(frozen=True)
class Option:
    key: str
    name: str


def _remote_message(response: httpx.Response) -> str:
    """The tracker's own explanation of a refusal, trimmed."""
    try:
        body = response.json()
    except ValueError:
        return ""
    parts: list[str] = []
    if isinstance(body, dict):
        for key in ("errorMessages", "message", "error"):
            value = body.get(key)
            if isinstance(value, list):
                parts.extend(str(v) for v in value if v)
            elif isinstance(value, str) and value:
                parts.append(value)
        errors = body.get("errors")
        if isinstance(errors, dict):
            parts.extend(f"{k}: {v}" for k, v in errors.items())
        elif isinstance(errors, list):
            parts.extend(_error_text(e) for e in errors)
    return redact_url_queries("; ".join(p for p in parts if p))[:MAX_REMOTE_MESSAGE]


def _error_text(error: object) -> str:
    if not isinstance(error, dict):
        return str(error)
    if error.get("message"):
        return str(error["message"])
    return " ".join(
        str(error[k]) for k in ("resource", "field", "code") if error.get(k)
    )


class Tracker(ABC):
    """One tracker site reached with one credential."""

    kind: ClassVar[str]
    initial_status: ClassVar[str | None] = None

    def __init__(
        self, url: str, config: dict, *, client: httpx.Client | None = None
    ) -> None:
        self.url = url.rstrip("/")
        self.config = config
        self._client = client
        self._validated = client is not None

    @property
    def spec(self) -> TrackerSpec:
        return TRACKERS_BY_KIND[self.kind]

    @property
    def label(self) -> str:
        return self.spec.label

    @abstractmethod
    def headers(self) -> dict[str, str]: ...

    def client(self) -> httpx.Client:
        if not self._validated:
            try:
                validate_public_https_url(self.url, label=self.spec.url_label)
            except ValueError as exc:
                raise TrackerError(str(exc)) from None
            self._validated = True
        if self._client is None:
            self._client = get_sync_client(
                follow_redirects=False, timeout=httpx.Timeout(TIMEOUT)
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _wait(self, response: httpx.Response) -> float | None:
        """Seconds to wait before retrying, or None when the answer is not a rate limit."""
        code = response.status_code
        headers = response.headers
        limited = code == HTTP_TOO_MANY or (
            code == HTTP_FORBIDDEN
            and (
                "Retry-After" in headers or headers.get("x-ratelimit-remaining") == "0"
            )
        )
        if not limited:
            return None
        delay = _as_int(headers.get("Retry-After"))
        reset = _as_int(headers.get("x-ratelimit-reset"))
        if delay is None and reset is not None:
            delay = max(1, reset - int(time.time()))
        return float(min(delay or RETRY_AFTER_DEFAULT, MAX_RETRY_SLEEP))

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
    ) -> Any:
        url = f"{self.url}{path}"
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client().request(
                    method, url, params=params, json=json, headers=self.headers()
                )
            except httpx.TimeoutException:
                msg = f"{self.label} did not respond."
                raise TrackerError(msg) from None
            except httpx.HTTPError:
                msg = f"{self.label} is unreachable. Check the {self.spec.url_label}."
                raise TrackerError(msg) from None
            code = response.status_code
            wait = self._wait(response)
            if wait is not None:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)
                    continue
                msg = f"{self.label} rate limit reached."
                raise RateLimitedError(msg)
            if code == HTTP_UNAUTHORIZED:
                msg = f"{self.label} rejected the credentials."
                raise CredentialsError(msg)
            detail = _remote_message(response) if code >= HTTP_REDIRECT else ""
            suffix = f": {detail}" if detail else ""
            if code in GONE:
                msg = f"{self.label} returned {code}{suffix}"
                raise RemoteNotFoundError(msg)
            if HTTP_REDIRECT <= code < HTTP_ERROR:
                msg = f"{self.label} returned {code}. Check the {self.spec.url_label}."
                raise TrackerError(msg)
            if code >= HTTP_ERROR:
                msg = f"{self.label} returned {code}{suffix}"
                raise TrackerError(msg)
            if not response.content:
                return None
            try:
                return response.json()
            except ValueError:
                msg = f"{self.label} returned an unexpected response."
                raise TrackerError(msg) from None
        msg = f"{self.label} rate limit reached."
        raise RateLimitedError(msg)

    def request_dict(self, method: str, path: str, **kwargs: Any) -> dict:
        found = self.request(method, path, **kwargs)
        if found is None:
            return {}
        if not isinstance(found, dict):
            msg = f"{self.label} returned an unexpected response."
            raise TrackerError(msg)
        return found

    def request_list(self, method: str, path: str, **kwargs: Any) -> list[dict]:
        found = self.request(method, path, **kwargs)
        if found is None:
            return []
        if not isinstance(found, list):
            msg = f"{self.label} returned an unexpected response."
            raise TrackerError(msg)
        return [row for row in found if isinstance(row, dict)]

    def public_destination(self, destination: str) -> bool:  # noqa: ARG002
        """Whether anyone outside the organization can read issues filed there."""
        return False

    @abstractmethod
    def find_marker(self, destination: str, marker: str) -> RemoteIssue | None:
        """The issue carrying this marker label, when one exists."""

    @abstractmethod
    def verify(self) -> str:
        """The account the credential signs in as."""

    @abstractmethod
    def destinations(self, query: str = "") -> list[Option]: ...

    def issue_types(self, destination: str) -> list[Option]:  # noqa: ARG002
        return []

    @abstractmethod
    def create(
        self,
        destination: str,
        issue_type: str | None,
        title: str,
        body: Doc,
        labels: list[str],
    ) -> RemoteIssue: ...

    @abstractmethod
    def comment(self, destination: str, external_id: str, body: Doc) -> None: ...

    @abstractmethod
    def statuses(
        self, destination: str, external_ids: list[str]
    ) -> dict[str, RemoteStatus | None]:
        """Status per issue id; None for an issue the tracker no longer holds."""


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None
