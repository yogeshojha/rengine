from __future__ import annotations

from shared.definitions.endpoints import EndpointSource
from shared.services.endpoint_inventory import EndpointObservation
from stages.url_discovery.providers.base import ProviderResult, UrlProvider
from tools.urlfinder.client import UrlfinderClient, UrlfinderError


class ArchiveProvider(UrlProvider):
    """URLs public archives recorded for this domain. Never contacts the target."""

    source = EndpointSource.ARCHIVE.value
    tool = "urlfinder"
    binary = "urlfinder"
    touches_target = False

    def discover(self, result: ProviderResult) -> None:
        cfg = self.ctx.cfg
        domains = self.ctx.apex_domains[: cfg.max_archive_domains]
        if not domains:
            return
        try:
            client = UrlfinderClient(
                timeout=cfg.timeout,
                proxy_url=self.ctx.net.proxy_url,
                recorder=self.ctx.recorder,
                extra_args=self.extra_args,
            )
        except UrlfinderError as e:
            raise RuntimeError(str(e)) from e

        found = 0
        seen: set[str] = set()
        observations: list[EndpointObservation] = []
        cap = cfg.max_urls
        scanned = 0

        for domain in domains:
            if self.aborted():
                result.capped = True
                result.cap_reason = "The scan was cancelled."
                break
            scanned += 1
            for url in client.collect(domain):
                found += 1
                if url in seen:
                    continue
                seen.add(url)
                # scope first: an out-of-scope result must not consume the budget
                if not self.in_scope(url):
                    continue
                if len(observations) >= cap:
                    result.capped = True
                    result.cap_reason = (
                        f"Stopped at the {cap} URL limit for this provider."
                    )
                    break
                observations.append(
                    EndpointObservation(
                        url=url,
                        detail="Recorded by a public archive, not confirmed by this scan",
                    )
                )
            if result.capped:
                break

        result.observations = observations
        dropped = len(self.ctx.apex_domains) - len(domains)
        if dropped > 0 and not result.cap_reason:
            result.capped = True
            result.cap_reason = (
                f"{dropped} more registrable domains were not queried, at the "
                f"{cfg.max_archive_domains} domain limit."
            )
        result.urls_found = found
        result.hosts_scanned = scanned
        self.progress(
            f"{len(result.observations)} archived urls across {scanned} domains"
        )
