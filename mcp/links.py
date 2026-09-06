"""Deep links back into the UI. A tool's number is only a promise if it opens."""

from __future__ import annotations

import uuid
from urllib.parse import urlencode


def _base(url: str) -> str:
    return url.rstrip("/")


def scan_tab(
    ui: str, scan_id: uuid.UUID | str, tab: str, query: str | None = None
) -> str:
    params = {"tab": tab}
    if query:
        params["q"] = query
    return f"{_base(ui)}/scans/{scan_id}?{urlencode(params)}"


def scan(ui: str, scan_id: uuid.UUID | str) -> str:
    return f"{_base(ui)}/scans/{scan_id}"


def target(ui: str, target_id: uuid.UUID | str, tab: str | None = None) -> str:
    suffix = f"?tab={tab}" if tab else ""
    return f"{_base(ui)}/targets/{target_id}{suffix}"


def scans_for_target(ui: str, target_id: uuid.UUID | str) -> str:
    return f"{_base(ui)}/scans?target={target_id}"


def dashboard(ui: str) -> str:
    return f"{_base(ui)}/dashboard"
