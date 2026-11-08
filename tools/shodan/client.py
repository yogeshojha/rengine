from __future__ import annotations

import json
import time
from types import TracebackType

import httpx

from shared.http import get_sync_client

HOST_URL = "https://api.shodan.io/shodan/host/{ip}"
REQUEST_TIMEOUT = 20.0
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
# Shodan's API limit is one request a second
MIN_INTERVAL = 1.05
_NOT_FOUND = 404
_REFUSED = frozenset({401, 403})
_RATE_LIMITED = 429


def _read_capped(resp: httpx.Response) -> bytes | None:
    """The body, or None past MAX_RESPONSE_BYTES."""
    body = bytearray()
    for chunk in resp.iter_bytes():
        body += chunk
        if len(body) > MAX_RESPONSE_BYTES:
            return None
    return bytes(body)


class ShodanError(Exception):
    """Shodan did not answer, or answered with something unreadable."""


class ShodanRefusedError(ShodanError):
    """Shodan refused the key or the plan for host lookups."""


class ShodanRateLimitedError(ShodanError):
    """Shodan refused the request at its rate limit."""


class ShodanClient:
    def __init__(self, key: str) -> None:
        self._key = key
        self._client = get_sync_client(
            timeout=httpx.Timeout(REQUEST_TIMEOUT), follow_redirects=False
        )
        self._last = 0.0

    def __enter__(self) -> ShodanClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._client.close()

    def _pace(self) -> None:
        wait = self._last + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def host(self, ip: str) -> dict | None:
        """Everything Shodan indexed for one address, or None when it holds nothing."""
        self._pace()
        try:
            with self._client.stream(
                "GET", HOST_URL.format(ip=ip), params={"key": self._key}
            ) as resp:
                status = resp.status_code
                body = _read_capped(resp) if status == httpx.codes.OK else b""
        except httpx.TimeoutException:
            msg = f"Shodan did not answer within {REQUEST_TIMEOUT:.0f} seconds."
            raise ShodanError(msg) from None
        except httpx.HTTPError as exc:
            msg = f"Shodan could not be reached: {type(exc).__name__}."
            raise ShodanError(msg) from None
        if status == _NOT_FOUND:
            return None
        if status in _REFUSED:
            msg = f"Shodan refused the key for host lookups: HTTP {status}."
            raise ShodanRefusedError(msg)
        if status == _RATE_LIMITED:
            msg = "Shodan rate limit reached."
            raise ShodanRateLimitedError(msg)
        if status != httpx.codes.OK:
            msg = f"Shodan returned HTTP {status}."
            raise ShodanError(msg)
        if body is None:
            msg = "Shodan returned an oversized answer."
            raise ShodanError(msg)
        try:
            payload = json.loads(body)
        except ValueError:
            msg = "Shodan returned an unreadable answer."
            raise ShodanError(msg) from None
        return payload if isinstance(payload, dict) else None
