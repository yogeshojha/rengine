from __future__ import annotations

import re
from dataclasses import dataclass, field

from shared.definitions.domains import target_zone
from shared.definitions.endpoints import EndpointSource
from shared.services.endpoint_inventory import EndpointObservation
from shared.utils.net import bracketed
from stages.url_discovery.config import MAX_URLS
from stages.url_discovery.providers.base import ProviderResult, UrlProvider
from tools.katana.client import KatanaClient, KatanaError, url_pattern
from tools.katana.parser import parse_katana_record

_JS_RE = re.compile(r"\.m?js(?:\.map)?(?:[?#]|$)", re.IGNORECASE)
_LITERAL = re.compile(r"[a-z0-9_.-]+", re.IGNORECASE)
_ANCHORED = re.compile(r"(\^|\(\^\|\\\.\))((?:[a-z0-9_-]|\\[.-])+)\$", re.IGNORECASE)
_LABELS = "[^/?#@:]*"
_SUBDOMAINS = r"([^/?#@:]*\.)?"
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
                threads=self.ctx.transport.threads,
                timeout=self.ctx.transport.timeout,
                max_duration_minutes=cfg.max_crawl_minutes,
                rate_limit=self.ctx.transport.rate,
                crawl_scope=cfg.crawl_scope,
                crawl_in_scope=self._crawl_in_scope(),
                crawl_out_scope=crawl_out_scope(
                    self.ctx.resolved.excluded_subdomains or []
                ),
                include_js=True,
                headless=cfg.headless,
                exclude_extensions=list(cfg.static_extensions),
                proxy_url=self.ctx.net.proxy_url,
                headers=self.ctx.net.headers,
                scheme=self.ctx.net.probe_scheme,
                recorder=self.ctx.recorder,
                extra_args=self.extra_args,
            )
        except KatanaError as e:
            raise RuntimeError(str(e)) from e

    def _crawl_in_scope(self) -> list[str]:
        """-crawl-scope patterns for a target narrower than its zone."""
        hosts, apexes = self._scope
        if not any(target_zone(apex) != apex for apex in apexes):
            return []
        scheme = self.ctx.net.probe_scheme
        patterns = [url_pattern(_SUBDOMAINS + re.escape(a), scheme) for a in apexes]
        patterns += [
            url_pattern(re.escape(bracketed(host)), scheme)
            for host in sorted(hosts)
            if not any(host == a or host.endswith(f".{a}") for a in apexes)
        ]
        return patterns

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
            self._ingest(records, state, result, MAX_URLS)

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


def crawl_out_scope(entries: list[str]) -> list[str]:
    """-crawl-out-scope patterns for the host exclusions katana can read."""
    patterns = []
    for entry in entries:
        if _LITERAL.fullmatch(entry):
            patterns.append(url_pattern(f"{_LABELS}{re.escape(entry)}{_LABELS}"))
            continue
        anchored = _ANCHORED.fullmatch(entry)
        if anchored is not None:
            lead = "" if anchored.group(1) == "^" else _SUBDOMAINS
            patterns.append(url_pattern(lead + anchored.group(2)))
    return patterns


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
