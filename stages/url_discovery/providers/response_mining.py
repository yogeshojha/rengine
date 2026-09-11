from __future__ import annotations

from sqlalchemy import select

from shared.definitions.endpoints import EndpointSource
from shared.models.http_asset import HttpAsset
from shared.services.endpoint_inventory import EndpointObservation
from stages.url_discovery.providers import mine
from stages.url_discovery.providers.base import ProviderResult, UrlProvider

_BATCH = 50


class ResponseMiningProvider(UrlProvider):
    """Links, scripts and forms read out of response bodies this scan already stored.

    Sends no request: the bodies were captured by the HTTP probe, so this runs at any intensity.
    """

    source = EndpointSource.RESPONSE_MINING.value
    tool = None
    binary = None
    touches_target = False
    uses_session = True

    def discover(self, result: ProviderResult) -> None:
        offsite = 0
        mined = 0
        seen: set[str] = set()
        observations: list[EndpointObservation] = []

        rows = self.ctx.session.execute(
            select(
                HttpAsset.url,
                HttpAsset.final_url,
                HttpAsset.response_body,
                HttpAsset.response_headers,
            )
            .where(HttpAsset.scan_id == self.ctx.scan_id)
            .execution_options(yield_per=_BATCH)
        )
        for row in rows:
            if self.aborted():
                result.capped = True
                result.cap_reason = "The scan was cancelled."
                break
            base = row.final_url or row.url
            body = row.response_body or ""
            if not body and not row.response_headers:
                continue
            mined += 1
            for candidate in mine.candidates(body, row.response_headers or {}):
                resolved = self._resolve(base, candidate)
                if resolved is None:
                    offsite += 1
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)
                observations.append(
                    EndpointObservation(
                        url=resolved,
                        found_on=base,
                        detail=f"Linked from the response body of {base}",
                    )
                )

        result.observations = observations
        result.urls_found = len(observations)
        result.pages_fetched = 0
        result.hosts_scanned = mined
        if offsite:
            result.cap_reason = (
                f"{offsite} links pointed outside the scan's scope and were not stored."
            )
        self.progress(
            f"mined {len(observations)} in-scope urls from {mined} stored responses, no requests sent"
        )

    def _resolve(self, base: str, candidate: str) -> str | None:
        absolute = mine.resolve(base, candidate)
        return absolute if absolute and self.in_scope(absolute) else None
