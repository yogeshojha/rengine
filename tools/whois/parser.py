from ipaddress import IPv4Network, IPv6Network
from typing import Any

from shared.utils.coerce import safe_bool, safe_datetime, safe_int, safe_list, safe_str
from tools.whois.models import (
    WhoisAddress,
    WhoisASNResponse,
    WhoisDomainResponse,
    WhoisEntities,
    WhoisEntity,
    WhoisIPResponse,
)


def _parse_address(raw: Any) -> WhoisAddress | None:
    if not isinstance(raw, dict):
        return None
    return WhoisAddress(
        po_box=safe_str(raw.get("po_box")),
        ext_address=safe_str(raw.get("ext_address")),
        street_address=safe_str(raw.get("street_address")),
        locality=safe_str(raw.get("locality")),
        region=safe_str(raw.get("region")),
        postal_code=safe_str(raw.get("postal_code")),
        country=safe_str(raw.get("country")),
    )


def _parse_entity(raw: dict[str, Any]) -> WhoisEntity:
    return WhoisEntity(
        handle=safe_str(raw.get("handle")),
        name=safe_str(raw.get("name")),
        email=safe_str(raw.get("email")),
        tel=safe_str(raw.get("tel")),
        type=safe_str(raw.get("type")),
        url=safe_str(raw.get("url")),
        rir=safe_str(raw.get("rir")),
        whois_server=safe_str(raw.get("whois_server")),
        address=_parse_address(raw.get("address")),
    )


def _parse_entities(raw: Any) -> WhoisEntities:
    """Parse whoisit's role-keyed entity lists into WhoisEntity objects; unknown roles are ignored."""
    if not isinstance(raw, dict):
        return WhoisEntities()

    known_roles = {
        "registrant",
        "administrative",
        "technical",
        "abuse",
        "billing",
        "registrar",
        "sponsor",
        "noc",
        "routing",
    }

    parsed: dict[str, list[WhoisEntity]] = {}
    for role in known_roles:
        role_entities = raw.get(role)
        if not isinstance(role_entities, list):
            parsed[role] = []
            continue
        parsed[role] = [_parse_entity(e) for e in role_entities if isinstance(e, dict)]

    return WhoisEntities(**parsed)


def _parse_base_fields(raw: dict[str, Any], query: str) -> dict[str, Any]:
    return {
        "query": query,
        "handle": safe_str(raw.get("handle")),
        "parent_handle": safe_str(raw.get("parent_handle")),
        "name": safe_str(raw.get("name")),
        "whois_server": safe_str(raw.get("whois_server")),
        "object_class": safe_str(raw.get("type")),
        "terms_of_service_url": safe_str(raw.get("terms_of_service_url")),
        "copyright_notice": safe_str(raw.get("copyright_notice")),
        "description": [safe_str(d) for d in safe_list(raw.get("description"))],
        "registration_date": safe_datetime(raw.get("registration_date")),
        "last_changed_date": safe_datetime(raw.get("last_changed_date")),
        "expiration_date": safe_datetime(raw.get("expiration_date")),
        "rir": safe_str(raw.get("rir")),
        "url": safe_str(raw.get("url")),
        "entities": _parse_entities(raw.get("entities")),
    }


def _network_to_str(value: Any) -> str:
    if isinstance(value, (IPv4Network, IPv6Network)):
        return str(value)
    if value is not None:
        return safe_str(value)
    return ""


def parse_domain_response(raw: dict[str, Any], query: str) -> WhoisDomainResponse:
    """Parse a raw whoisit domain response into a typed model."""
    base = _parse_base_fields(raw, query)
    return WhoisDomainResponse(
        **base,
        unicode_name=safe_str(raw.get("unicode_name")),
        nameservers=[safe_str(ns) for ns in safe_list(raw.get("nameservers"))],
        status=[safe_str(s) for s in safe_list(raw.get("status"))],
        dnssec=safe_bool(raw.get("dnssec")),
    )


def parse_ip_response(raw: dict[str, Any], query: str) -> WhoisIPResponse:
    """Parse a raw whoisit IP response into a typed model."""
    base = _parse_base_fields(raw, query)
    return WhoisIPResponse(
        **base,
        # upper-cased for case-insensitive correlation
        country=safe_str(raw.get("country")).strip().upper(),
        ip_version=safe_int(raw.get("ip_version")),
        assignment_type=safe_str(raw.get("assignment_type")),
        network=_network_to_str(raw.get("network")),
    )


def parse_asn_response(raw: dict[str, Any], query: str) -> WhoisASNResponse:
    """Parse a raw whoisit ASN response into a typed model."""
    base = _parse_base_fields(raw, query)

    # asn_range comes as [start, end] list e.g. [38565, 38565]
    asn_range = raw.get("asn_range")
    asn_range_start = None
    asn_range_end = None
    if isinstance(asn_range, list) and len(asn_range) >= 2:  # noqa: PLR2004
        asn_range_start = safe_int(asn_range[0])
        asn_range_end = safe_int(asn_range[1])

    return WhoisASNResponse(
        **base,
        asn_range_start=asn_range_start,
        asn_range_end=asn_range_end,
    )
