from __future__ import annotations

import re
from dataclasses import dataclass, field

from shared.definitions.endpoints import EndpointSource
from shared.services.endpoint_inventory import EndpointObservation
from stages.url_discovery.providers.base import ProviderResult, UrlProvider
from tools.katana.client import KatanaClient, KatanaError
from tools.katana.parser import parse_katana_record

_JS_RE = re.compile(r"\.m?js(?:\.map)?(?:[?#]|$)", re.IGNORECASE)
_UNRESPONSIVE = ("could not", "connection refused", "timeout", "no address")
_HANDOVER_EVERY = 200
_FATAL = (
    "flag provided but not defined",
    "invalid value",
    "could not create runner",
    "panic:",
)


class KatanaProvider(UrlProvider):
    """Walk the site by following links, forms and JavaScript."""

    source = EndpointSource.CRAWL.value
    tool = "katana"
    binary = "katana"

    def _client(self) -> KatanaClient:
        cfg = self.ctx.cfg
        try:
            return KatanaClient(
                depth=cfg.crawl_depth,
                threads=cfg.threads,
                timeout=cfg.timeout,
                max_duration_minutes=cfg.max_crawl_minutes,
                rate_limit=cfg.rate,
                crawl_scope=cfg.crawl_scope,
                include_js=cfg.crawl_javascript,
                headless=cfg.headless,
                exclude_extensions=list(cfg.static_extensions)
                if cfg.drop_noise
                else [],
                proxy_url=self.ctx.net.proxy_url,
                headers=self.ctx.net.headers,
                recorder=self.ctx.recorder,
                extra_args=self.extra_args,
            )
        except KatanaError as e:
            raise RuntimeError(str(e)) from e

    def discover(self, result: ProviderResult) -> None:
        targets = [h.url for h in self.ctx.hosts]
        if not targets:
            return
        cfg = self.ctx.cfg
        errors = 0

        fatal: list[str] = []

        def _stderr(line: str) -> None:
            nonlocal errors
            lowered = line.lower()
            if any(token in lowered for token in _FATAL):
                fatal.append(line.strip()[:300])
            elif any(token in lowered for token in _UNRESPONSIVE):
                errors += 1

        client = self._client()

        state = _Crawl()
        with client.stream_crawl(
            targets, should_stop=self.ctx.is_aborted, stderr_sink=_stderr
        ) as records:
            self._ingest(records, state, result, cfg.max_urls)

        if fatal:
            msg = f"katana could not run: {fatal[0]}"
            raise RuntimeError(msg)

        result.observations = state.observations
        result.urls_found = state.found
        result.hosts_scanned = len(targets)
        result.depth_reached = min(state.deepest, cfg.crawl_depth)
        result.errors = errors
        note = f"crawled {len(targets)} sites, {state.collected} urls"
        if state.out_of_scope:
            note += f", {state.out_of_scope} off-site links out of scope"
        self.progress(note)

    def _ingest(self, records, state: _Crawl, result: ProviderResult, cap: int) -> None:
        """Read the crawl and hand batches to the stage."""
        for record in records:
            parsed = parse_katana_record(record)
            if parsed is None:
                continue
            state.found += 1
            url = parsed["url"]
            if url in state.seen:
                continue
            state.seen.add(url)
            if not self.in_scope(url):
                state.out_of_scope += 1
                continue
            if state.collected >= cap:
                result.capped = True
                result.cap_reason = f"Stopped at the {cap} URL limit for this provider."
                break
            state.observations.append(_observation(parsed))
            state.deepest = max(state.deepest, url.count("/") - 2)
            if len(state.observations) >= _HANDOVER_EVERY:
                state.handed += len(state.observations)
                self.hand_over(state.observations)


@dataclass
class _Crawl:
    """Crawl state, handed-over batches included."""

    found: int = 0
    out_of_scope: int = 0
    deepest: int = 0
    handed: int = 0
    seen: set[str] = field(default_factory=set)
    observations: list[EndpointObservation] = field(default_factory=list)

    @property
    def collected(self) -> int:
        return self.handed + len(self.observations)


def _observation(parsed: dict) -> EndpointObservation:
    return EndpointObservation(
        url=parsed["url"],
        found_on=parsed["found_on"],
        detail=_detail(parsed),
        methods=[parsed["method"]] if parsed["method"] else [],
        is_probed=parsed["status_code"] is not None,
        status_code=parsed["status_code"],
        content_type=parsed["content_type"],
        content_length=parsed["content_length"],
        title=parsed["title"],
    )


def _detail(parsed: dict) -> str:
    tag, attribute = parsed.get("tag"), parsed.get("attribute")
    if tag and attribute:
        return f"Found in a <{tag}> {attribute} attribute"
    if tag:
        return f"Found in a <{tag}> element"
    if _JS_RE.search(parsed.get("found_on") or ""):
        return "Read out of a javascript bundle, not linked from any page"
    return "Reached by following links from the site"
