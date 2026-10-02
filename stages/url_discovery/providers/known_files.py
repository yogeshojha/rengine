from __future__ import annotations

import ipaddress
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

import httpx

from shared.definitions.endpoints import EndpointSource
from shared.services.endpoint_inventory import EndpointObservation
from shared.utils.net import host_port
from stages.url_discovery.config import MAX_KNOWN_FILE_HOSTS
from stages.url_discovery.providers import mine
from stages.url_discovery.providers.base import ProviderResult, UrlProvider

_ROBOTS = "/robots.txt"
_SECURITY = "/.well-known/security.txt"
_SITEMAPS = ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml")
_RULE_RE = re.compile(r"^(allow|disallow)\s*:\s*(\S+)", re.IGNORECASE)
_SITEMAP_RE = re.compile(r"^sitemap\s*:\s*(\S+)", re.IGNORECASE)
_MAX_BYTES = 5 * 1024 * 1024
_MAX_SITEMAPS = 20
_MAX_WORKERS = 12
_WILDCARD = ("*", "$")
_SECURITY_DETAIL = f"Served at {_SECURITY}"
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
        limit = MAX_KNOWN_FILE_HOSTS
        selected = roots[:limit]
        state = _State()
        client = self.http_client()
        try:
            workers = min(self.workers(_MAX_WORKERS), len(selected))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for found in pool.map(lambda root: self._mine(client, root), selected):
                    if found is None:
                        result.capped = True
                        result.cap_reason = "The scan was cancelled."
                        continue
                    state.merge(found)
        finally:
            client.close()

        kept = [o for o in state.observations if self.in_scope(o.url)]
        offsite = len(state.observations) - len(kept)
        result.observations = kept
        result.urls_found = len(state.observations)
        if offsite and not result.cap_reason:
            result.cap_reason = f"{offsite} declared urls pointed outside the scan's scope and were not stored."
        result.pages_fetched = state.fetched
        result.errors = state.errors
        result.hosts_scanned = min(len(roots), limit)
        self.progress(
            f"{len(result.observations)} urls declared by robots.txt and sitemaps"
        )

    def _mine(self, client: httpx.Client, root: str) -> _State | None:
        if self.aborted():
            return None
        state = _State()
        queue: list[str] = []

        body = self._get(client, urljoin(root, _ROBOTS), state)
        if body is not None:
            rules, declared = _parse_robots(body)
            queue.extend(declared)
            state.found += len(rules)
            for rule in rules:
                state.add(
                    urljoin(root, rule), root, f"Declared by robots.txt on {root}"
                )

        if self._get(client, urljoin(root, _SECURITY), state) is not None:
            state.found += 1
            state.add(urljoin(root, _SECURITY), root, _SECURITY_DETAIL)

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
                state.add(location, url, f"Declared by the sitemap on {url}")
        return state

    def _get(self, client: httpx.Client, url: str, state: _State) -> str | None:
        if self.path_excluded(url):
            state.refused += 1
            return None
        return self.fetch_text(client, url, _MAX_BYTES, state)


class _State:
    def __init__(self) -> None:
        self.observations: list[EndpointObservation] = []
        self.seen: set[str] = set()
        self.found = 0
        self.fetched = 0
        self.errors = 0
        self.refused = 0

    def merge(self, other: _State) -> None:
        self.found += other.found
        self.fetched += other.fetched
        self.errors += other.errors
        self.refused += other.refused
        for obs in other.observations:
            if obs.url in self.seen:
                continue
            self.seen.add(obs.url)
            self.observations.append(obs)

    def add(self, url: str, found_on: str, detail: str) -> None:
        if url in self.seen or len(url) > mine.MAX_URL:
            return
        self.seen.add(url)
        self.observations.append(
            EndpointObservation(url=url, found_on=found_on, detail=detail)
        )


def _fetchable(url: str, in_scope) -> bool:
    """Whether a sitemap URL is http or https, in scope, and a global address when an IP literal."""
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
        seen.setdefault(f"{host.scheme}://{host_port(host.host, host.port)}", host.url)
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
