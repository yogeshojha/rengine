"""Group crt.sh organization-search rows by the organization each certificate names."""

from __future__ import annotations

import json
import re
from datetime import date, datetime

from shared.definitions.domains import registrable_domain
from tools.crtsh.models import CrtShOrganization, CrtShResult

_HOST_RE = re.compile(r"(?:[a-zA-Z0-9_-]+\.)+[a-zA-Z]{2,}")


def _domains(blob: str) -> set[str]:
    found: set[str] = set()
    for token in _HOST_RE.findall(blob):
        registrable = registrable_domain(token, strict=True)
        if registrable:
            found.add(registrable)
    return found


def _day(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def parse_org_search(payload: str) -> CrtShResult | None:
    """None when the answer is not a JSON list; crt.sh returns an error page as 200."""
    try:
        rows = json.loads(payload)
    except (ValueError, TypeError):
        return None
    if not isinstance(rows, list):
        return None
    grouped: dict[str, CrtShOrganization] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = " ".join(str(row.get("name_value") or "").split())
        if not name:
            continue
        entry = grouped.setdefault(name, CrtShOrganization(name=name))
        entry.certs += 1
        issued = _day(row.get("not_before"))
        for domain in _domains(str(row.get("common_name") or "")):
            latest = entry.domains.get(domain)
            if domain not in entry.domains or (
                issued and (not latest or issued > latest)
            ):
                entry.domains[domain] = issued
    organizations = sorted(grouped.values(), key=lambda org: (-org.certs, org.name))
    return CrtShResult(certs=len(rows), organizations=organizations)
