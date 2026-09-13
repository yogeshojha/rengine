"""The result dimensions a scan produces, named as the UI names them."""

from __future__ import annotations

from enum import StrEnum

from shared.enums.scan import AssetKind


class SurfaceDimension(StrEnum):
    WEB_ASSETS = "web_assets"
    ENDPOINTS = "endpoints"
    SERVICES = "services"
    IPS = "ips"
    VULNERABILITIES = "vulnerabilities"
    SOFTWARE = "software"


SURFACE_ORDER: tuple[str, ...] = tuple(d.value for d in SurfaceDimension)

SURFACE_LABELS: dict[str, str] = {
    SurfaceDimension.WEB_ASSETS.value: "Web assets",
    SurfaceDimension.ENDPOINTS.value: "Endpoints",
    SurfaceDimension.SERVICES.value: "Services",
    SurfaceDimension.IPS.value: "IP addresses",
    SurfaceDimension.VULNERABILITIES.value: "Vulnerabilities",
    SurfaceDimension.SOFTWARE.value: "Software",
}

SURFACE_NOUN: dict[str, tuple[str, str]] = {
    SurfaceDimension.WEB_ASSETS.value: ("web asset", "web assets"),
    SurfaceDimension.ENDPOINTS.value: ("endpoint", "endpoints"),
    SurfaceDimension.SERVICES.value: ("service", "services"),
    SurfaceDimension.IPS.value: ("address", "addresses"),
    SurfaceDimension.VULNERABILITIES.value: ("finding", "findings"),
    SurfaceDimension.SOFTWARE.value: ("software CVE", "software CVEs"),
}

SURFACE_KINDS: dict[str, frozenset[str]] = {
    SurfaceDimension.WEB_ASSETS.value: frozenset(
        {AssetKind.HOSTS.value, AssetKind.HTTP_ASSETS.value}
    ),
    SurfaceDimension.ENDPOINTS.value: frozenset({AssetKind.ENDPOINTS.value}),
    SurfaceDimension.SERVICES.value: frozenset({AssetKind.PORTS.value}),
    SurfaceDimension.IPS.value: frozenset({AssetKind.ADDRESSES.value}),
    SurfaceDimension.VULNERABILITIES.value: frozenset(
        {AssetKind.VULNERABILITIES.value}
    ),
    # inferred from what the probe stages report, never produced by a stage of its own
    SurfaceDimension.SOFTWARE.value: frozenset(
        {AssetKind.HTTP_ASSETS.value, AssetKind.PORTS.value}
    ),
}

SURFACE_COUNT_COLUMNS: dict[str, tuple[str, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: ("subdomains_found", "http_assets_found"),
    SurfaceDimension.ENDPOINTS.value: ("endpoints_found",),
    SurfaceDimension.SERVICES.value: ("open_ports_found",),
    SurfaceDimension.IPS.value: ("ips_found",),
    SurfaceDimension.VULNERABILITIES.value: ("vulnerabilities_found",),
}

# the columns a person reads, in the order an export writes them
SURFACE_COLUMNS: dict[str, tuple[str, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: (
        "name",
        "http_status",
        "page_title",
        "http_url",
        "tech",
        "webserver",
        "resolved_ips",
        "cname",
        "is_cdn",
        "cdn_name",
        "waf",
        "asn_org",
        "ports",
        "tls_expired",
        "endpoint_count",
        "vuln_count",
        "vuln_severity",
        "vuln_kev",
    ),
    SurfaceDimension.ENDPOINTS.value: (
        "url",
        "host",
        "path",
        "status_code",
        "content_type",
        "content_length",
        "title",
        "methods",
        "param_count",
        "endpoint_class",
        "interest",
        "primary_source",
        "is_probed",
        "is_new",
    ),
    SurfaceDimension.SERVICES.value: (
        "ip",
        "port",
        "protocol",
        "service_name",
        "service_class",
        "product",
        "version",
        "is_http",
        "tls",
        "status_code",
        "title",
        "url",
        "hosts",
        "asn_org",
        "country",
        "is_cdn",
        "is_sensitive",
        "source",
        "is_new",
    ),
    SurfaceDimension.IPS.value: (
        "ip",
        "version",
        "asn",
        "asn_org",
        "country",
        "prefix",
        "is_cdn",
        "cdn_name",
        "is_alive",
        "ports",
        "port_count",
        "host_count",
        "hosts",
        "has_sensitive",
    ),
    SurfaceDimension.VULNERABILITIES.value: (
        "fingerprint",
        "template_id",
        "template_name",
        "severity",
        "scanner",
        "matched_at",
        "host",
        "ip",
        "port",
        "cve_ids",
        "cvss_score",
        "epss_score",
        "is_kev",
        "state",
        "is_new",
        "tags",
    ),
}

# the column a human reads first
SURFACE_IDENTITY: dict[str, str] = {
    SurfaceDimension.WEB_ASSETS.value: "name",
    SurfaceDimension.ENDPOINTS.value: "url",
    SurfaceDimension.SERVICES.value: "ip",
    SurfaceDimension.IPS.value: "ip",
    SurfaceDimension.VULNERABILITIES.value: "template_name",
}

# the one value a plain text export writes per line, for piping into the next tool
SURFACE_TEXT_VALUE: dict[str, tuple[str, ...]] = {
    SurfaceDimension.WEB_ASSETS.value: ("name",),
    SurfaceDimension.ENDPOINTS.value: ("url",),
    SurfaceDimension.SERVICES.value: ("ip", "port"),
    SurfaceDimension.IPS.value: ("ip",),
    SurfaceDimension.VULNERABILITIES.value: ("matched_at",),
}
