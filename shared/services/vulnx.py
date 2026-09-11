"""vulnx: per-CVE exploit intelligence, fetched on demand and cached forever."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from shared.logging import get_logger
from shared.models.threat_intel import CveIntel
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

BASE_URL = "https://api.projectdiscovery.io/v2/vulnerability"
PROVIDER = "vulnx"
TIMEOUT = 30
MAX_PER_RUN = 200
FIELDS = (
    "cve_id,severity,cvss_score,epss_score,is_kev,is_vkev,is_poc,poc_count,"
    "poc_first_seen,pocs,is_template,is_remote,is_auth,is_patch_available,"
    "description,remediation,weaknesses,exposure,kev,h1,cve_created_at"
)
REFRESH_AFTER = timedelta(days=14)
MAX_POCS = 25
MAX_EXPOSURE_PRODUCTS = 8
HTTP_TOO_MANY = 429


class VulnxError(RuntimeError):
    pass


class RateLimitedError(VulnxError):
    def __init__(self, reset_at: float) -> None:
        super().__init__("vulnx rate limit reached")
        self.reset_at = reset_at


@dataclass
class Budget:
    """What the last response said about how much room is left."""

    remaining: int | None = None
    reset_at: float | None = None

    def wait(self) -> None:
        if self.remaining is not None and self.remaining <= 0 and self.reset_at:
            delay = max(0.0, self.reset_at - time.time()) + 1
            if delay > 0:
                logger.info("vulnx budget spent, waiting", seconds=round(delay, 1))
                time.sleep(min(delay, 90))


def _request(path: str, params: dict, api_key: str | None, budget: Budget) -> dict:
    budget.wait()
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "reNgine"})  # noqa: S310
    if api_key:
        request.add_header("X-Api-Key", api_key)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            budget.remaining = _int(response.headers.get("x-ratelimit-remaining"))
            budget.reset_at = _float(response.headers.get("x-ratelimit-reset"))
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == HTTP_TOO_MANY:
            budget.remaining = 0
            budget.reset_at = _float(exc.headers.get("x-ratelimit-reset")) or (
                time.time() + 60
            )
            raise RateLimitedError(budget.reset_at) from exc
        msg = f"vulnx returned {exc.code}"
        raise VulnxError(msg) from exc
    except Exception as exc:
        raise VulnxError(str(exc)) from exc


def _int(raw) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _float(raw) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _dt(raw) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _row(cve: str, data: dict) -> dict:
    exposure = data.get("exposure") or {}
    products = [
        {"id": str(v.get("id"))[:120], "hosts": int(v.get("max_hosts") or 0)}
        for v in (exposure.get("values") or [])
        if v.get("id")
    ]
    products.sort(key=lambda p: -p["hosts"])
    pocs = [
        {
            "url": str(p.get("url"))[:500],
            "source": str(p.get("source") or "")[:40] or None,
            "added_at": p.get("added_at"),
        }
        for p in (data.get("pocs") or [])
        if p.get("url")
    ][:MAX_POCS]
    h1 = data.get("h1") or {}
    kev_sources = sorted(
        {str(k.get("source"))[:40] for k in (data.get("kev") or []) if k.get("source")}
    )
    return {
        "cve": cve,
        "provider": PROVIDER,
        "severity": str(data.get("severity") or "")[:16] or None,
        "cvss_score": data.get("cvss_score"),
        "description": strip_control(data.get("description") or "")[:4000] or None,
        "remediation": strip_control(data.get("remediation") or "")[:2000] or None,
        "weaknesses": [
            {
                "cwe_id": str(w.get("cwe_id"))[:40],
                "cwe_name": strip_control(w.get("cwe_name") or "")[:200],
            }
            for w in (data.get("weaknesses") or [])
            if w.get("cwe_id")
        ][:10],
        "pocs": pocs,
        "poc_count": int(data.get("poc_count") or len(pocs) or 0),
        "poc_first_seen": _dt(data.get("poc_first_seen")),
        "template_available": data.get("is_template"),
        "is_remote": data.get("is_remote"),
        "needs_auth": data.get("is_auth"),
        "patch_available": data.get("is_patch_available"),
        "vendor_kev": bool(data.get("is_vkev")),
        "kev_sources": kev_sources,
        "exposure_hosts": int(exposure.get("max_hosts") or 0) or None,
        "exposure_products": products[:MAX_EXPOSURE_PRODUCTS],
        "hackerone_rank": _int(h1.get("rank")),
        "hackerone_reports": _int(h1.get("reports")),
        "published_at": _dt(data.get("cve_created_at")),
        "fetched_at": utc_now(),
    }


def api_key(session: Session) -> str | None:
    """The stored vulnx key, if the operator added one."""
    try:
        from shared.utils.crypto import decrypt  # noqa: PLC0415

        raw = session.execute(
            text(
                "SELECT key_value FROM api_keys WHERE provider = 'VULNX' AND is_enabled LIMIT 1"
            )
        ).scalar()
        return decrypt(raw) if raw else None
    except Exception:
        logger.debug("vulnx key unavailable", exc_info=True)
        return None


def pending(session: Session, cves: list[str]) -> list[str]:
    """Which of these CVEs we have not cached, or cached too long ago."""
    keys = sorted({c.strip().upper() for c in cves if c and c.strip()})
    if not keys:
        return []
    cutoff = utc_now() - REFRESH_AFTER
    known = {
        row.cve
        for row in session.execute(
            select(CveIntel.cve, CveIntel.fetched_at).where(CveIntel.cve.in_(keys))
        )
        if row.fetched_at and row.fetched_at > cutoff
    }
    return [c for c in keys if c not in known]


def enrich(session: Session, cves: list[str], *, limit: int = MAX_PER_RUN) -> dict:
    """Fetch and cache detail for CVEs we do not already hold."""
    todo = pending(session, cves)[:limit]
    if not todo:
        return {"requested": 0, "cached": 0, "failed": 0, "rate_limited": False}

    key = api_key(session)
    budget = Budget()
    cached = failed = 0
    limited = False

    for cve in todo:
        try:
            payload = _request(
                f"/{urllib.parse.quote(cve)}", {"fields": FIELDS}, key, budget
            )
        except RateLimitedError:
            limited = True
            logger.info("vulnx enrichment stopped at the rate limit", cached=cached)
            break
        except VulnxError:
            failed += 1
            continue
        data = payload.get("data") or {}
        if not data.get("cve_id"):
            failed += 1
            continue
        row = _row(cve, data)
        session.execute(
            pg_insert(CveIntel)
            .values(**row)
            .on_conflict_do_update(
                index_elements=[CveIntel.cve],
                set_={k: v for k, v in row.items() if k != "cve"},
            )
        )
        cached += 1
    session.commit()
    return {
        "requested": len(todo),
        "cached": cached,
        "failed": failed,
        "rate_limited": limited,
    }


def enrich_scan(session: Session, scan_id, *, limit: int = MAX_PER_RUN) -> dict:
    cves = (
        session.execute(
            text("""
            SELECT DISTINCT upper(btrim(c.cve)) AS cve
            FROM vulnerabilities v
            CROSS JOIN LATERAL jsonb_array_elements_text(v.cve_ids::jsonb) AS c(cve)
            WHERE v.scan_id = :scan_id
        """),
            {"scan_id": str(scan_id)},
        )
        .scalars()
        .all()
    )
    return enrich(session, list(cves), limit=limit)
