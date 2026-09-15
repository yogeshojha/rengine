"""dnsx, a validating resolver and one policy fetch per zone."""

from __future__ import annotations

import httpx

from shared.definitions.domain_posture import (
    POLICY_FETCH_TIMEOUT,
    POLICY_MAX_BYTES,
    VALIDATING_RESOLVERS,
)
from shared.logging import get_logger
from shared.services.domain_posture.dnssec import dnssec_state
from shared.services.domain_posture.records import PolicyFetch
from stages.base import NetOptions
from tools.dnsx.client import DnsxClient

logger = get_logger(__name__)

_POLICY_PATH = "/.well-known/mta-sts.txt"
_USER_AGENT = "reNgine/3.0 (+https://rengine.wiki)"


def _host(value: str) -> str:
    return value.strip().lower().rstrip(".")


class DnsxLookup:
    def __init__(self, client: DnsxClient, net: NetOptions) -> None:
        self._client = client
        self._net = net

    def records(
        self, names: list[str], types: tuple[str, ...]
    ) -> dict[str, dict[str, list[str]]]:
        if not names:
            return {}
        result = self._client.query(names, record_types=list(types))
        out: dict[str, dict[str, list[str]]] = {}
        for rec in result.json_records:
            host = _host(str(rec.get("host") or ""))
            if not host:
                continue
            found = out.setdefault(host, {})
            for kind in types:
                values = rec.get(kind)
                if isinstance(values, list):
                    found.setdefault(kind, []).extend(str(v) for v in values)
        return out

    def dnssec(self, zone: str) -> str:
        return dnssec_state(zone, VALIDATING_RESOLVERS)

    def policy(self, zone: str) -> PolicyFetch:
        url = f"https://mta-sts.{zone}{_POLICY_PATH}"
        try:
            with (
                httpx.Client(
                    timeout=POLICY_FETCH_TIMEOUT,
                    follow_redirects=False,
                    proxy=self._net.proxy_url or None,
                    headers={"User-Agent": _USER_AGENT},
                ) as client,
                client.stream("GET", url) as response,
            ):
                if response.status_code != httpx.codes.OK:
                    return PolicyFetch(reached=True, body=None)
                body = b""
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > POLICY_MAX_BYTES:
                        return PolicyFetch(reached=True, body=None)
                return PolicyFetch(
                    reached=True, body=body.decode("utf-8", errors="replace")
                )
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("mta-sts policy host not reached", zone=zone, error=str(exc))
            return PolicyFetch(reached=False)
