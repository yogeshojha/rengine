"""Hardening checks read off a stored HTTP response."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, select, text, update
from sqlalchemy.orm import Session

from shared.definitions.hygiene import (
    BACKFILL_BATCH,
    HSTS_MIN_MAX_AGE,
    MAX_EVIDENCE,
    HygieneCheck,
)
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset

logger = get_logger(__name__)

C = HygieneCheck

_HTML = ("text/html", "application/xhtml")
_VERSION_RE = re.compile(r"\d+\.\d+")
_MAX_AGE_RE = re.compile(r"max-age\s*=\s*\"?(\d+)", re.IGNORECASE)
_SET_COOKIE_LINE = re.compile(r"^set-cookie\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_JOINED_COOKIE_SPLIT = re.compile(r",\s*(?=[^\s;,=]+=)")
_SESSION_NAME = re.compile(
    r"sess|(^|[^a-z])sid([^a-z]|$)|auth|token|jwt|login|logged|remember|identity",
    re.IGNORECASE,
)
_NOT_SESSION = re.compile(r"csrf|xsrf", re.IGNORECASE)
_RUNTIME_HEADERS = (
    "x_powered_by",
    "x_aspnet_version",
    "x_aspnetmvc_version",
    "x_generator",
)
_FRAME_VALUES = ("deny", "sameorigin")
_CACHE_PRIVATE = ("no-store", "private")
_SCRIPT_WILDCARDS = ("*", "https:", "http:", "data:")
_KEYED_SOURCES = ("'nonce-", "'sha256-", "'sha384-", "'sha512-")


@dataclass(frozen=True)
class Cookie:
    name: str
    attributes: frozenset[str]

    @property
    def session(self) -> bool:
        return bool(_SESSION_NAME.search(self.name)) and not _NOT_SESSION.search(
            self.name
        )


@dataclass(frozen=True)
class Verdict:
    key: str
    failed: bool
    evidence: str | None = None


@dataclass
class Hygiene:
    verdicts: list[Verdict] = field(default_factory=list)

    @property
    def issues(self) -> list[str]:
        return [str(v.key) for v in self.verdicts if v.failed]

    @property
    def checked(self) -> list[str]:
        return [str(v.key) for v in self.verdicts]

    @property
    def evidence(self) -> dict[str, str]:
        return {
            str(v.key): v.evidence for v in self.verdicts if v.failed and v.evidence
        }


# ---------- parsing ----------


def normalize_headers(raw: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (raw or {}).items():
        if value is None:
            continue
        name = str(key).strip().lower().replace("-", "_")
        text_value = (
            ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        )
        out[name] = f"{out[name]}, {text_value}" if name in out else text_value
    return out


def _clip(value: str) -> str:
    value = " ".join(value.split())
    return value if len(value) <= MAX_EVIDENCE else value[: MAX_EVIDENCE - 1] + "…"


def _cookie(line: str) -> Cookie | None:
    parts = [p.strip() for p in line.split(";")]
    if not parts or "=" not in parts[0]:
        return None
    name = parts[0].split("=", 1)[0].strip()
    if not name:
        return None
    attributes = frozenset(p.split("=", 1)[0].strip().lower() for p in parts[1:] if p)
    return Cookie(name=name, attributes=attributes)


def cookies_of(headers: dict[str, str], raw_header: str | None) -> list[Cookie]:
    lines: list[str]
    if raw_header and (found := _SET_COOKIE_LINE.findall(raw_header)):
        lines = found
    elif joined := headers.get("set_cookie"):
        lines = _JOINED_COOKIE_SPLIT.split(joined)
    else:
        return []
    out = []
    for line in lines:
        cookie = _cookie(line)
        if cookie is not None:
            out.append(cookie)
    return out


def csp_directives(policy: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for chunk in policy.split(";"):
        tokens = chunk.strip().split()
        if not tokens:
            continue
        name = tokens[0].lower()
        out.setdefault(name, [t.lower() for t in tokens[1:]])
    return out


def _script_sources(directives: dict[str, list[str]]) -> list[str] | None:
    for name in ("script-src", "default-src"):
        if name in directives:
            return directives[name]
    return None


def _is_html(content_type: str | None) -> bool:
    return bool(content_type) and content_type.lower().startswith(_HTML)


def _cache_directives(headers: dict[str, str]) -> set[str]:
    return {d.strip().lower() for d in headers.get("cache_control", "").split(",") if d}


# ---------- checks ----------

_OK = (200, 300)
_REDIRECT = (300, 400)


def _between(status: int | None, bounds: tuple[int, int]) -> bool:
    return status is not None and bounds[0] <= status < bounds[1]


def _transport(h: dict[str, str], scheme: str, status: int, add) -> None:
    if scheme == "https":
        hsts = h.get("strict_transport_security")
        add(Verdict(C.NO_HSTS, hsts is None))
        if hsts is not None:
            match = _MAX_AGE_RE.search(hsts)
            age = int(match.group(1)) if match else -1
            add(Verdict(C.HSTS_SHORT, age < HSTS_MIN_MAX_AGE, _clip(hsts)))
    elif scheme == "http":
        location = h.get("location", "")
        redirects = _between(status, _REDIRECT) and location.lower().startswith(
            "https://"
        )
        add(
            Verdict(
                C.NO_HTTPS_REDIRECT,
                not redirects,
                _clip(f"{status} {location}".strip()),
            )
        )


def _content(h: dict[str, str], status: int, content_type: str | None, add) -> None:
    csp = h.get("content_security_policy")
    csp_ro = h.get("content_security_policy_report_only")
    directives = csp_directives(csp) if csp else {}
    ok = _between(status, _OK)
    if ok and _is_html(content_type):
        xfo = h.get("x_frame_options", "").strip().lower()
        framed = xfo in _FRAME_VALUES or "frame-ancestors" in directives
        add(Verdict(C.NO_FRAME_PROTECTION, not framed, _clip(xfo) if xfo else None))
        add(Verdict(C.NO_CSP, csp is None and csp_ro is None))
        add(
            Verdict(
                C.CSP_REPORT_ONLY,
                csp is None and csp_ro is not None,
                _clip(csp_ro) if csp_ro else None,
            )
        )
        add(Verdict(C.NO_REFERRER_POLICY, "referrer_policy" not in h))
    if ok and content_type:
        nosniff = h.get("x_content_type_options", "").strip().lower() == "nosniff"
        add(Verdict(C.NO_NOSNIFF, not nosniff))
    sources = _script_sources(directives) if csp else None
    if sources is not None:
        strict = "'strict-dynamic'" in sources
        keyed = any(s.startswith(_KEYED_SOURCES) for s in sources)
        inline = "'unsafe-inline'" in sources and not keyed and not strict
        wildcard = any(s in _SCRIPT_WILDCARDS for s in sources) and not strict
        shown = _clip(" ".join(sources))
        add(Verdict(C.CSP_UNSAFE_INLINE, inline, shown))
        add(Verdict(C.CSP_WILDCARD_SCRIPT, wildcard, shown))


def _cookie_checks(h: dict[str, str], cookies: list[Cookie], https: bool, add) -> None:
    if cookies and https:
        insecure = [c.name for c in cookies if "secure" not in c.attributes]
        add(
            Verdict(
                C.COOKIE_NO_SECURE, bool(insecure), _clip(", ".join(insecure)) or None
            )
        )
    session_cookies = [c for c in cookies if c.session]
    if session_cookies:
        readable = [c.name for c in session_cookies if "httponly" not in c.attributes]
        add(
            Verdict(
                C.COOKIE_NO_HTTPONLY, bool(readable), _clip(", ".join(readable)) or None
            )
        )
        guarded = any(d in _cache_directives(h) for d in _CACHE_PRIVATE)
        add(
            Verdict(
                C.CACHEABLE_SESSION,
                not guarded,
                _clip(h.get("cache_control") or "no Cache-Control header"),
            )
        )


def _cross_origin(h: dict[str, str], add) -> None:
    acao = h.get("access_control_allow_origin")
    if acao is None:
        return
    origin = acao.strip().lower()
    credentials = (
        h.get("access_control_allow_credentials", "").strip().lower() == "true"
    )
    add(
        Verdict(
            C.CORS_CREDENTIALS,
            credentials and origin in ("*", "null"),
            _clip(f"{acao}; credentials true" if credentials else acao),
        )
    )
    add(Verdict(C.CORS_ANY_ORIGIN, origin == "*", _clip(acao)))


def _disclosure(h: dict[str, str], add) -> None:
    server = h.get("server")
    if server:
        add(Verdict(C.SERVER_VERSION, bool(_VERSION_RE.search(server)), _clip(server)))
    disclosed = [f"{n.replace('_', '-')}: {h[n]}" for n in _RUNTIME_HEADERS if h.get(n)]
    add(
        Verdict(
            C.RUNTIME_DISCLOSED, bool(disclosed), _clip("; ".join(disclosed)) or None
        )
    )


def evaluate(
    headers: dict[str, Any] | None,
    raw_header: str | None,
    *,
    scheme: str | None,
    status_code: int | None,
    content_type: str | None,
) -> Hygiene:
    """Every check that applies to the response, with its outcome."""
    result = Hygiene()
    if status_code is None:
        return result
    h = normalize_headers(headers)
    add = result.verdicts.append
    scheme = (scheme or "").lower()
    _transport(h, scheme, status_code, add)
    _content(h, status_code, content_type, add)
    _cookie_checks(h, cookies_of(h, raw_header), scheme == "https", add)
    _cross_origin(h, add)
    _disclosure(h, add)
    return result


def evaluate_asset(asset: HttpAsset) -> Hygiene:
    return evaluate(
        asset.response_headers,
        asset.raw_response_header,
        scheme=asset.scheme,
        status_code=asset.status_code,
        content_type=asset.content_type,
    )


# ---------- host fold ----------

_FOLD_SQL = text(
    """
    WITH per_host AS (
      SELECT a.host,
             coalesce(jsonb_agg(DISTINCT i.v ORDER BY i.v) FILTER (WHERE i.v IS NOT NULL), '[]'::jsonb) AS issues,
             coalesce(jsonb_agg(DISTINCT c.v ORDER BY c.v) FILTER (WHERE c.v IS NOT NULL), '[]'::jsonb) AS checked
      FROM http_assets a
      LEFT JOIN LATERAL jsonb_array_elements_text(a.hygiene_issues::jsonb) i(v) ON true
      LEFT JOIN LATERAL jsonb_array_elements_text(a.hygiene_checked::jsonb) c(v) ON true
      WHERE a.scan_id = :scan_id AND a.hygiene_checked IS NOT NULL
      GROUP BY a.host
    )
    UPDATE subdomains s
       SET hygiene_issues = per_host.issues::json,
           hygiene_checked = per_host.checked::json
      FROM per_host
     WHERE s.scan_id = :scan_id AND s.name = per_host.host
    """
)


def fold_onto_hosts(session: Session, scan_id: UUID) -> int:
    """Union every asset's checks onto its host row."""
    return session.execute(_FOLD_SQL, {"scan_id": scan_id}).rowcount


# ---------- backfill ----------

_ASSET_UPDATE = (
    update(HttpAsset)
    .where(HttpAsset.id == bindparam("b_id"))
    .values(hygiene_issues=bindparam("issues"), hygiene_checked=bindparam("checked"))
)


def pending_scans(session: Session, *, limit: int) -> list[UUID]:
    rows = session.execute(
        select(HttpAsset.scan_id)
        .where(HttpAsset.hygiene_checked.is_(None))
        .group_by(HttpAsset.scan_id)
        .limit(limit)
    ).all()
    return [row[0] for row in rows]


def backfill_scan(session: Session, scan_id: UUID) -> int:
    """Evaluate every stored response of one scan, then fold onto its hosts."""
    stmt = (
        select(
            HttpAsset.id,
            HttpAsset.scheme,
            HttpAsset.status_code,
            HttpAsset.content_type,
            HttpAsset.response_headers,
            HttpAsset.raw_response_header,
        )
        .where(HttpAsset.scan_id == scan_id, HttpAsset.hygiene_checked.is_(None))
        .execution_options(yield_per=BACKFILL_BATCH)
    )
    done = 0
    batch: list[dict] = []
    for row in session.execute(stmt):
        found = evaluate(
            row.response_headers,
            row.raw_response_header,
            scheme=row.scheme,
            status_code=row.status_code,
            content_type=row.content_type,
        )
        batch.append({"b_id": row.id, "issues": found.issues, "checked": found.checked})
        if len(batch) >= BACKFILL_BATCH:
            session.connection().execute(_ASSET_UPDATE, batch)
            done += len(batch)
            batch = []
    if batch:
        session.connection().execute(_ASSET_UPDATE, batch)
        done += len(batch)
    fold_onto_hosts(session, scan_id)
    session.commit()
    return done
