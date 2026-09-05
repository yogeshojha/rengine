from __future__ import annotations

import ipaddress
import re
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

import httpx

from shared.definitions.endpoints import EndpointSource
from shared.services.endpoint_inventory import EndpointObservation
from stages.url_discovery.providers.base import ProviderResult, UrlProvider

_ROBOTS = "/robots.txt"
_SECURITY = "/.well-known/security.txt"
_SITEMAPS = ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml")
_RULE_RE = re.compile(r"^(allow|disallow)\s*:\s*(\S+)", re.IGNORECASE)
_SITEMAP_RE = re.compile(r"^sitemap\s*:\s*(\S+)", re.IGNORECASE)
_MAX_BYTES = 5 * 1024 * 1024
_MAX_SITEMAPS = 20
_MAX_URL = 2000
_CLIENT_ERROR = 400
_WILDCARD = ("*", "$")
_ALLOWED_SCHEMES = ("http", "https")


class KnownFilesProvider(UrlProvider):
    """The site's own declarations: robots.txt, sitemap.xml and security.txt."""

    source = EndpointSource.SITEMAP.value
    tool = None
    binary = None

    def discover(self, result: ProviderResult) -> None:
        roots = _roots(self.ctx.hosts)
        if not roots:
            return
        limit = self.ctx.cfg.max_known_file_hosts
        state = _State()
        client = self._client()
        try:
            for root in roots[:limit]:
                if self.aborted():
                    result.capped = True
                    result.cap_reason = "The scan was cancelled."
                    break
                self._mine(client, root, state)
        finally:
            client.close()

        kept = [o for o in state.observations if self.in_scope(o.url)]
        offsite = len(state.observations) - len(kept)
        result.observations = kept
        result.urls_found = len(kept)
        if offsite:
            result.cap_reason = f"{offsite} declared urls pointed outside the scan's scope and were not stored."
        result.pages_fetched = state.fetched
        result.errors = state.errors
        result.hosts_scanned = min(len(roots), limit)
        self.progress(
            f"{len(result.observations)} urls declared by robots.txt and sitemaps"
        )

    def _client(self) -> httpx.Client:
        headers = dict(self.ctx.net.headers or {})
        headers.setdefault("User-Agent", "reNgine/3.0 (+https://rengine.wiki)")
        return httpx.Client(
            timeout=self.ctx.cfg.timeout,
            follow_redirects=True,
            verify=False,  # noqa: S501
            proxy=self.ctx.net.proxy_url or None,
            headers=headers,
        )

    def _mine(self, client: httpx.Client, root: str, state: _State) -> None:
        queue: list[str] = []

        body = self._get(client, urljoin(root, _ROBOTS), state)
        if body is not None:
            rules, declared = _parse_robots(body)
            queue.extend(declared)
            state.found += len(rules)
            for rule in rules:
                state.add(urljoin(root, rule), root, EndpointSource.ROBOTS.value)

        if self._get(client, urljoin(root, _SECURITY), state) is not None:
            state.found += 1
            state.add(urljoin(root, _SECURITY), root, self.source)

        queue.extend(urljoin(root, path) for path in _SITEMAPS)
        visited: set[str] = set()
        while queue and len(visited) < _MAX_SITEMAPS:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            if not _fetchable(url, self.in_scope):
                state.refused += 1
                continue
            body = self._get(client, url, state)
            if body is None:
                continue
            locations, nested = _parse_sitemap(body)
            queue.extend(n for n in nested if n not in visited)
            state.found += len(locations)
            for location in locations:
                state.add(location, url, self.source)

    def _get(self, client: httpx.Client, url: str, state: _State) -> str | None:
        state.fetched += 1
        try:
            response = client.get(url)
        except (httpx.HTTPError, ValueError):
            state.errors += 1
            return None
        if response.status_code >= _CLIENT_ERROR:
            return None
        return response.text[:_MAX_BYTES]


class _State:
    def __init__(self) -> None:
        self.observations: list[EndpointObservation] = []
        self.seen: set[str] = set()
        self.found = 0
        self.fetched = 0
        self.errors = 0
        self.refused = 0

    def add(self, url: str, found_on: str, source: str) -> None:
        if url in self.seen or len(url) > _MAX_URL:
            return
        self.seen.add(url)
        label = "robots.txt" if source == EndpointSource.ROBOTS.value else "the sitemap"
        self.observations.append(
            EndpointObservation(
                url=url,
                found_on=found_on,
                detail=f"Declared by {label} on {found_on}",
            )
        )


def _fetchable(url: str, in_scope) -> bool:
    """A sitemap URL is attacker-controlled: it must stay in scope and off private space."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        return False
    host = (parts.hostname or "").lower()
    if not host or not in_scope(url):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return address.is_global


def _roots(hosts) -> list[str]:
    seen: dict[str, str] = {}
    for host in hosts:
        seen.setdefault(f"{host.scheme}://{host.host}:{host.port}", host.url)
    return list(seen.values())


def _parse_robots(body: str) -> tuple[list[str], list[str]]:
    rules: list[str] = []
    sitemaps: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        sitemap = _SITEMAP_RE.match(line)
        if sitemap:
            sitemaps.append(sitemap.group(1))
            continue
        rule = _RULE_RE.match(line)
        if not rule:
            continue
        path = rule.group(2)
        # a wildcard rule names a pattern, not a URL
        if path in ("/", "") or any(token in path for token in _WILDCARD):
            continue
        rules.append(path)
    return rules, sitemaps


def _parse_sitemap(body: str) -> tuple[list[str], list[str]]:
    try:
        root = ET.fromstring(body)  # noqa: S314
    except ET.ParseError:
        return [], []
    is_index = root.tag.endswith("sitemapindex")
    values = [
        (element.text or "").strip()
        for element in root.iter()
        if element.tag.endswith("loc") and (element.text or "").strip()
    ]
    return ([], values) if is_index else (values, [])
