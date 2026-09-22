"""Ask the address for the fronted site by name, and keep only what answers with it."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import httpx

from shared.logging import get_logger
from shared.models.scan_correlation import OriginFinding
from shared.services.origin_exposure import HTTPS_PORT, ORIGIN_EXPOSED
from shared.utils.infra import generic_page

logger = get_logger(__name__)

BODY_CAP = 200_000
LENGTH_TOLERANCE = 1.25
_TITLE = re.compile(rb"<title[^>]*>(.{0,200}?)</title>", re.I | re.S)
_TLS_PORTS = frozenset({HTTPS_PORT, 8443, 2083, 2087})


@dataclass(frozen=True)
class Page:
    status: int
    length: int
    digest: str
    title: str


def read(response: httpx.Response) -> Page:
    body = response.content[:BODY_CAP]
    found = _TITLE.search(body)
    title = found.group(1).decode("utf-8", "replace").strip() if found else ""
    return Page(
        status=response.status_code,
        length=len(body),
        digest=hashlib.sha256(body).hexdigest(),
        title=title,
    )


def same_site(named: Page | None, origin: Page | None) -> bool:
    """Whether the address served the fronted site rather than a page of its own."""
    if named is None or origin is None:
        return False
    if generic_page(named.title, (named.status,)):
        return False
    if named.digest == origin.digest and named.length:
        return True
    if not named.title or named.title != origin.title:
        return False
    low, high = sorted((max(named.length, 1), max(origin.length, 1)))
    return high / low < LENGTH_TOLERANCE


class OriginConfirmer:
    def __init__(
        self,
        *,
        timeout: float,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self._headers = dict(headers or {})
        self._client = httpx.Client(
            timeout=timeout,
            proxy=proxy_url or None,
            verify=False,  # noqa: S501
            follow_redirects=False,
            transport=httpx.HTTPTransport(verify=False, retries=1),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OriginConfirmer:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def confirms(self, found: OriginFinding) -> bool:
        if found.kind != ORIGIN_EXPOSED:
            return True
        address, port = found.exposed.ip, found.exposed.port or HTTPS_PORT
        name = next((s.host for s in found.fronted if s.host), "")
        if not address or not name or name == address:
            return False
        scheme = "https" if port in _TLS_PORTS else "http"
        named = self._fetch(f"{scheme}://{name}:{port}/")
        origin = self._fetch(
            f"{scheme}://{address}:{port}/",
            host=name,
        )
        return same_site(named, origin)

    def _fetch(self, url: str, *, host: str | None = None) -> Page | None:
        headers = dict(self._headers)
        extensions: dict[str, str] = {}
        if host:
            headers["Host"] = host
            extensions["sni_hostname"] = host
        try:
            return read(self._client.get(url, headers=headers, extensions=extensions))
        except httpx.HTTPError as exc:
            logger.debug("origin confirmation failed", url=url, error=str(exc))
            return None
