from __future__ import annotations

import httpx

from shared.definitions.infostealer import MAX_RESPONSE_BYTES, REQUEST_TIMEOUT
from shared.http import get_sync_client
from tools.hudsonrock.models import InfostealerReport
from tools.hudsonrock.parser import parse_domain_report

BASE_URL = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools"
_RATE_LIMITED = 429


class HudsonRockError(Exception):
    """Hudson Rock did not answer or returned something unreadable."""


class HudsonRockRateLimitedError(HudsonRockError):
    """Hudson Rock refused the request at its rate limit."""


class HudsonRockClient:
    def search_domain(self, domain: str) -> InfostealerReport:
        try:
            with get_sync_client(timeout=httpx.Timeout(REQUEST_TIMEOUT)) as client:
                resp = client.get(
                    f"{BASE_URL}/search-by-domain", params={"domain": domain}
                )
        except httpx.TimeoutException:
            msg = f"Hudson Rock did not answer within {REQUEST_TIMEOUT:.0f} seconds."
            raise HudsonRockError(msg) from None
        except httpx.HTTPError as exc:
            msg = f"Hudson Rock could not be reached: {type(exc).__name__}."
            raise HudsonRockError(msg) from None
        if resp.status_code == _RATE_LIMITED:
            msg = "Hudson Rock rate limit reached. Try again in a minute."
            raise HudsonRockRateLimitedError(msg)
        if resp.status_code != httpx.codes.OK:
            msg = f"Hudson Rock returned HTTP {resp.status_code}."
            raise HudsonRockError(msg)
        if len(resp.content) > MAX_RESPONSE_BYTES:
            msg = "Hudson Rock returned an oversized answer."
            raise HudsonRockError(msg)
        try:
            payload = resp.json()
        except ValueError:
            msg = "Hudson Rock returned an unreadable answer."
            raise HudsonRockError(msg) from None
        report = parse_domain_report(payload, domain)
        if report is None:
            msg = "Hudson Rock returned an unreadable answer."
            raise HudsonRockError(msg)
        return report
