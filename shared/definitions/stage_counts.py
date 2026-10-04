"""Labels for the figures a stage reports when it finishes."""

from __future__ import annotations

from shared.definitions.surface import SURFACE_NOUN, SurfaceDimension

Label = tuple[str, str]


def noun(dimension: SurfaceDimension, *, before: str = "", after: str = "") -> Label:
    singular, plural = SURFACE_NOUN[dimension.value]
    return (
        " ".join(w for w in (before, singular, after) if w),
        " ".join(w for w in (before, plural, after) if w),
    )


HTTP_SERVICE_NOUN: Label = ("HTTP service", "HTTP services")

_WEB = SurfaceDimension.WEB_ASSETS
_IPS = SurfaceDimension.IPS
_SERVICES = SurfaceDimension.SERVICES
_ENDPOINTS = SurfaceDimension.ENDPOINTS

STAGE_COUNT_LABELS: dict[str, Label] = {
    "active": noun(_WEB, before="resolving"),
    "addresses": noun(_IPS),
    "ai_services": ("AI service", "AI services"),
    "alive": noun(_IPS, before="responsive"),
    "answered": ("answered", "answered"),
    "bgp": ("BGP record", "BGP records"),
    "cdn": ("CDN-fronted address", "CDN-fronted addresses"),
    "checked": ("checked", "checked"),
    "checks": ("check run", "checks run"),
    "cloud": ("cloud-hosted address", "cloud-hosted addresses"),
    "covered": noun(_WEB, after="covered by an equivalent"),
    "directories": ("directory", "directories"),
    "dns_records": ("DNS record", "DNS records"),
    "documents": ("response read", "responses read"),
    "edge_only": ("CDN edge address", "CDN edge addresses"),
    "endpoints": noun(_ENDPOINTS),
    "endpoints_new": noun(_ENDPOINTS, before="new"),
    "endpoints_probed": noun(_ENDPOINTS, after="requested"),
    "enriched": noun(_IPS, after="enriched"),
    "fingerprinted": noun(_SERVICES, after="identified"),
    "hosts": noun(_WEB, after="fuzzed"),
    "http_assets": HTTP_SERVICE_NOUN,
    "infostealer_hosts": ("infostealer hostname", "infostealer hostnames"),
    "ips": noun(_IPS),
    "known_ports": noun(_SERVICES, before="known"),
    "lookalike_threats": (
        "lookalike with a page or mail server",
        "lookalikes with a page or mail server",
    ),
    "lookalikes": ("registered lookalike", "registered lookalikes"),
    "mentioned_names": ("referenced name added", "referenced names added"),
    "names": ("name transferred", "names transferred"),
    "new": noun(_IPS, before="new"),
    "open_ports": noun(_SERVICES, before="open"),
    "origins": ("origin", "origins"),
    "pages_fetched": ("page fetched", "pages fetched"),
    "permutations": ("permutation", "permutations"),
    "posture_issues": ("posture check failing", "posture checks failing"),
    "probed": noun(_WEB, after="probed"),
    "ptr": ("PTR record", "PTR records"),
    "recovered": noun(_WEB, after="answered on a second pass"),
    "requests": ("request with parameters", "requests with parameters"),
    "scanned": noun(_IPS, after="scanned"),
    "screenshots": ("screenshot", "screenshots"),
    "secrets": noun(SurfaceDimension.SECRETS),
    "skipped": noun(_IPS, after="skipped"),
    "subdomains": noun(_WEB),
    "targets": ("target", "targets"),
    "uncalibrated": ("site dropped as catch-all", "sites dropped as catch-all"),
    "unresolved": noun(_WEB, after="without a DNS answer"),
    "vulnerabilities": noun(SurfaceDimension.VULNERABILITIES),
    "waf": ("firewall identified", "firewalls identified"),
    "web_services": noun(_SERVICES, before="web"),
    "whois": ("WHOIS record", "WHOIS records"),
    "zones": ("zone checked", "zones checked"),
}

STAGE_COUNT_OVERRIDES: dict[tuple[str, str], Label] = {
    ("takeover", "checked"): ("name checked", "names checked"),
    ("waf_detect", "checked"): noun(_WEB, after="checked"),
    ("session_check", "checked"): ("URL checked", "URLs checked"),
    ("origin_probe", "probed"): noun(_IPS, after="requested"),
    ("service_fingerprint", "probed"): noun(_SERVICES, after="probed"),
}

UNSHOWN_COUNTS: frozenset[str] = frozenset({"excluded"})


def stage_figures(stage: str | None, counts: dict) -> list[tuple[str, int, str]]:
    """Each labelled figure a stage reported, as (key, value, label)."""
    out: list[tuple[str, int, str]] = []
    for key, value in counts.items():
        if not isinstance(value, int) or isinstance(value, bool):
            continue
        label = STAGE_COUNT_OVERRIDES.get((stage or "", key)) or STAGE_COUNT_LABELS.get(
            key
        )
        if label is None:
            continue
        out.append((key, value, label[0] if value == 1 else label[1]))
    return out
