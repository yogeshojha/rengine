from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select

from shared.definitions.endpoints import EndpointSource
from shared.models.endpoint import Endpoint
from shared.services.endpoint_inventory import EndpointObservation
from stages.url_discovery.providers import mine
from stages.url_discovery.providers.base import ProviderResult, UrlProvider

_BUNDLE_EXTENSIONS = ("js", "mjs")
_OK = 200
_MAX_MAP_BYTES = 12 * 1024 * 1024
_MAX_SOURCES_SHOWN = 3
_MAX_WORKERS = 8


class SourceMapProvider(UrlProvider):
    """Source maps served beside a live javascript bundle."""

    source = EndpointSource.JS.value
    tool = None
    binary = None
    uses_session = True

    def discover(self, result: ProviderResult) -> None:
        bundles = self._bundles()
        result.hosts_total = len(bundles)
        if not bundles:
            self.progress(
                "no javascript bundle answered, so there is no map to ask for"
            )
            return

        limit = self.ctx.cfg.max_source_maps
        selected = bundles[:limit]
        client = self._client()
        try:
            workers = min(_MAX_WORKERS, len(selected))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                found = list(pool.map(lambda url: self._fetch(client, url), selected))
        finally:
            client.close()

        state = _State()
        for outcome in found:
            if outcome is None:
                result.capped = True
                result.cap_reason = "The scan was cancelled."
                continue
            state.absorb(outcome, self.in_scope)

        result.observations = state.observations
        result.urls_found = len(state.observations)
        result.pages_fetched = len(selected)
        result.hosts_scanned = len(selected)
        result.errors = state.errors
        if len(bundles) > len(selected):
            result.capped = True
            result.cap_reason = (
                f"{len(bundles) - len(selected):,} more bundles were not asked for: "
                f"the limit is {limit:,} per scan."
            )
        self.progress(state.note(len(selected)))

    def _bundles(self) -> list[str]:
        """Distinct bundles this scan proved answer."""
        rows = self.ctx.session.scalars(
            select(Endpoint.url)
            .where(
                Endpoint.scan_id == self.ctx.scan_id,
                Endpoint.extension.in_(_BUNDLE_EXTENSIONS),
                Endpoint.status_code == _OK,
            )
            .order_by(Endpoint.url)
        )
        seen: dict[str, None] = {}
        for url in rows:
            base = _strip(url)
            if base:
                seen.setdefault(base, None)
        return list(seen)

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

    def _fetch(self, client: httpx.Client, bundle: str) -> _Outcome | None:
        if self.aborted():
            return None
        url = f"{bundle}.map"
        outcome = _Outcome(bundle=bundle, url=url)
        try:
            with client.stream("GET", url) as response:
                if response.status_code != _OK:
                    return outcome
                body = bytearray()
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > _MAX_MAP_BYTES:
                        outcome.too_large = True
                        return outcome
        except (httpx.HTTPError, ValueError):
            outcome.failed = True
            return outcome
        outcome.read(bytes(body))
        return outcome


class _Outcome:
    def __init__(self, bundle: str, url: str) -> None:
        self.bundle = bundle
        self.url = url
        self.failed = False
        self.too_large = False
        self.digest: str | None = None
        self.sources: list[str] = []
        self.contents: list[str] = []

    def read(self, raw: bytes) -> None:
        try:
            document = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(document, dict):
            return
        sources = document.get("sources")
        if not isinstance(sources, list) or not sources:
            return
        self.digest = hashlib.sha256(raw).hexdigest()
        self.sources = [s for s in sources if isinstance(s, str)]
        contents = document.get("sourcesContent")
        self.contents = (
            [c for c in contents if isinstance(c, str)]
            if isinstance(contents, list)
            else []
        )

    @property
    def exposed(self) -> bool:
        return self.digest is not None


class _State:
    def __init__(self) -> None:
        self.observations: list[EndpointObservation] = []
        self.seen: set[str] = set()
        self.digests: set[str] = set()
        self.exposed = 0
        self.modules = 0
        self.errors = 0
        self.too_large = 0
        self.offsite = 0

    def absorb(self, outcome: _Outcome, in_scope) -> None:
        if outcome.failed:
            self.errors += 1
            return
        if outcome.too_large:
            self.too_large += 1
            return
        if not outcome.exposed:
            return

        self.exposed += 1
        self.modules += len(outcome.sources)
        shown = ", ".join(outcome.sources[:_MAX_SOURCES_SHOWN])
        self._add(
            outcome.url,
            outcome.bundle,
            f"Source map for {outcome.bundle}, naming {len(outcome.sources):,} "
            f"modules including {shown}",
        )

        if outcome.digest in self.digests:
            return
        self.digests.add(outcome.digest)
        detail = f"Read out of the source map for {outcome.bundle}"
        for text in outcome.contents:
            for candidate in mine.candidates(text):
                absolute = mine.resolve(outcome.bundle, candidate)
                if absolute is None:
                    continue
                if not in_scope(absolute):
                    self.offsite += 1
                    continue
                self._add(absolute, outcome.url, detail)

    def _add(self, url: str, found_on: str, detail: str) -> None:
        if url in self.seen or len(url) > mine.MAX_URL:
            return
        self.seen.add(url)
        self.observations.append(
            EndpointObservation(url=url, found_on=found_on, detail=detail)
        )

    def note(self, asked: int) -> str:
        parts = (
            [
                f"{self.exposed:,} of {asked:,} bundles ship their source map",
                f"{self.modules:,} modules named",
                f"{len(self.observations):,} urls",
            ]
            if self.exposed
            else [f"no source map beside any of {asked:,} bundles"]
        )
        if self.too_large:
            parts.append(f"{self.too_large:,} too large to read")
        return ", ".join(parts)


def _strip(url: str) -> str | None:
    """The bundle url without its query string or fragment."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.path:
        return None
    return f"{parts.scheme}://{parts.netloc}{parts.path}"
