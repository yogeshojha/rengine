"""cdncheck JSONL records, reduced to the addresses a provider fronts."""

from __future__ import annotations

# checked in this order: a CDN answer wins over a WAF one, a WAF over a cloud one
_KINDS = ("cdn", "waf", "cloud")


def parse_attribution(rec: dict) -> tuple[str, dict] | None:
    """The address and who fronts it, or None when cdncheck attributed nothing."""
    ip = rec.get("input") or rec.get("ip")
    if not ip:
        return None
    for kind in _KINDS:
        if rec.get(kind):
            name = rec.get(f"{kind}_name")
            return str(ip), {"is_cdn": True, "cdn_name": name, "cdn_type": kind}
    return None


def parse_attributions(records: list[dict]) -> dict[str, dict]:
    """{ip: {is_cdn, cdn_name, cdn_type}} for every attributed address."""
    out: dict[str, dict] = {}
    for rec in records:
        parsed = parse_attribution(rec)
        if parsed is not None:
            ip, attribution = parsed
            out[ip] = attribution
    return out
