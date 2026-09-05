from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from sqlalchemy import select

from shared.definitions.endpoints import EndpointSource
from shared.models.http_asset import HttpAsset
from shared.services.endpoint_inventory import EndpointObservation
from stages.url_discovery.providers.base import ProviderResult, UrlProvider

_ATTRIBUTE_RE = re.compile(
    r"""(?:href|src|action|data-url|data-href|data-src|formaction)\s*=\s*"""
    r"""["']([^"'<>\s]{1,2000})["']""",
    re.IGNORECASE,
)
_ABSOLUTE_RE = re.compile(r"""https?://[^\s"'<>()\[\]{}\\`]{4,1500}""", re.IGNORECASE)
_QUOTED_PATH_RE = re.compile(
    r"""["'`](/[A-Za-z0-9_\-./~%]{1,300}(?:\?[A-Za-z0-9_\-.=&%~+/]{0,200})?)["'`]"""
)
_LINK_HEADER_RE = re.compile(r"<([^>]{1,1500})>")

_SKIP_PREFIXES = ("javascript:", "mailto:", "tel:", "data:", "blob:", "about:", "#")
_PLACEHOLDER = ("{{", "${", "%7b%7b", "<%", "[[")
_MINED_HEADERS = ("link", "content-location", "location", "refresh")
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
            for candidate in self._candidates(body, row.response_headers or {}):
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

    def _candidates(self, body: str, headers: dict) -> list[str]:
        out: list[str] = []
        out.extend(_ATTRIBUTE_RE.findall(body))
        out.extend(_ABSOLUTE_RE.findall(body))
        out.extend(_QUOTED_PATH_RE.findall(body))
        for name, value in headers.items():
            if name.lower() not in _MINED_HEADERS or not isinstance(value, str):
                continue
            out.extend(_LINK_HEADER_RE.findall(value) or [value])
        return out

    def _resolve(self, base: str, candidate: str) -> str | None:
        value = html.unescape(candidate.strip())
        if not value or len(value) > 2000:  # noqa: PLR2004
            return None
        lowered = value.lower()
        if lowered.startswith(_SKIP_PREFIXES) or any(
            token in lowered for token in _PLACEHOLDER
        ):
            return None
        try:
            absolute = urljoin(base, value)
        except ValueError:
            return None
        return absolute if self.in_scope(absolute) else None
