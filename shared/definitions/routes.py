"""UI paths the backend links to, mirrored by frontend/src/lib/config/routes.ts."""

from __future__ import annotations

from enum import StrEnum
from urllib.parse import quote, urlencode


class ScanTab(StrEnum):
    WEB_ASSETS = "web-assets"
    ENDPOINTS = "endpoints"
    SERVICES = "services"
    IPS = "ips"
    VULNERABILITIES = "vulnerabilities"
    SOFTWARE = "software"
    SECRETS = "secrets"
    INTERESTING = "interesting"


class BountyHubTab(StrEnum):
    UPDATES = "updates"


SCHEDULES = "/automation/schedules"


def _query(params: dict[str, str] | None) -> str:
    return f"?{urlencode(params, quote_via=quote)}" if params else ""


def scan(scan_id: str, tab: str | None = None) -> str:
    return f"/scans/{scan_id}" + _query({"tab": tab} if tab else None)


def target(target_id: str) -> str:
    return f"/targets/{target_id}"


def surface(tab: str, params: dict[str, str] | None = None) -> str:
    return f"/surface/{tab}" + _query(params)


def cve(cve_id: str) -> str:
    return f"/surface/cve/{quote(cve_id)}"


def bounty_hub(tab: str) -> str:
    return "/bounty-hub" + _query({"tab": tab})


def tripwires(run_id: str) -> str:
    return "/tripwires" + _query({"run": str(run_id)})
