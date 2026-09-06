from __future__ import annotations

from shared.definitions.endpoints import EndpointSource
from shared.services.endpoint_inventory import EndpointObservation
from stages.url_discovery.providers.base import ProviderResult, UrlProvider
from tools.katana.client import KatanaClient, KatanaError
from tools.katana.parser import parse_katana_record

_UNRESPONSIVE = ("could not", "connection refused", "timeout", "no address")
# katana prints these when it cannot start at all, which must not read as "found nothing"
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

        found = 0
        out_of_scope = 0
        deepest = 0
        seen: set[str] = set()
        observations: list[EndpointObservation] = []
        cap = cfg.max_urls

        with client.stream_crawl(
            targets, should_stop=self.ctx.is_aborted, stderr_sink=_stderr
        ) as records:
            for record in records:
                parsed = parse_katana_record(record)
                if parsed is None:
                    continue
                found += 1
                url = parsed["url"]
                if url in seen:
                    continue
                seen.add(url)
                # katana's -field-scope bounds what it follows, not what it prints, so a
                # link to any third party arrives here; scope before the budget
                if not self.in_scope(url):
                    out_of_scope += 1
                    continue
                if len(observations) >= cap:
                    result.capped = True
                    result.cap_reason = (
                        f"Stopped at the {cap} URL limit for this provider."
                    )
                    break
                observations.append(_observation(parsed))
                deepest = max(deepest, url.count("/") - 2)

        if fatal:
            # zero records because the tool never ran is a failure, not an empty result
            msg = f"katana could not run: {fatal[0]}"
            raise RuntimeError(msg)

        result.observations = observations
        result.urls_found = found
        result.hosts_scanned = len(targets)
        result.depth_reached = min(deepest, cfg.crawl_depth)
        result.errors = errors
        note = f"crawled {len(targets)} sites, {len(observations)} urls"
        if out_of_scope:
            note += f" ({out_of_scope} off-site links not in scope)"
        self.progress(note)


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
    return "Reached by following links from the site"
