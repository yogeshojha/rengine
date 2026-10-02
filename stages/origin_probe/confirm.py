from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

import httpx

from shared.definitions.ports import likely_tls
from shared.logging import get_logger
from shared.models.scan_correlation import OriginFinding
from shared.services.origin_exposure import HTTPS_PORT, ORIGIN_EXPOSED
from shared.utils.infra import generic_page
from shared.utils.net import host_port

logger = get_logger(__name__)

BODY_CAP = 200_000
LENGTH_TOLERANCE = 1.25
_TITLE = re.compile(rb"<title[^>]*>(.{0,200}?)</title>", re.I | re.S)
_SCHEMES = frozenset({"http", "https"})


class Verdict(StrEnum):
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    UNCHECKED = "unchecked"


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

    def check(self, found: OriginFinding) -> Verdict:
        """Whether the address served the fronted site, refused it, or could not be asked."""
        if found.kind != ORIGIN_EXPOSED:
            return Verdict.CONFIRMED
        address, port = found.exposed.ip, found.exposed.port or HTTPS_PORT
        name = next((s.host for s in found.fronted if s.host), "")
        if not address or not name or name == address:
            return Verdict.UNCHECKED
        scheme = urlsplit(found.exposed.url or "").scheme.lower()
        if scheme not in _SCHEMES:
            scheme = "https" if likely_tls(port) else "http"
        named = self._fetch(f"{scheme}://{host_port(name, port)}/")
        origin = self._fetch(f"{scheme}://{host_port(address, port)}/", host=name)
        if named is None or origin is None:
            return Verdict.UNCHECKED
        return Verdict.CONFIRMED if same_site(named, origin) else Verdict.REFUTED

    def _fetch(self, url: str, *, host: str | None = None) -> Page | None:
        headers = dict(self._headers)
        extensions: dict[str, str] = {}
        if host:
            headers["Host"] = host
            extensions["sni_hostname"] = host
        try:
            return read(self._client.get(url, headers=headers, extensions=extensions))
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            logger.debug("origin confirmation failed", url=url, error=str(exc))
            return None
