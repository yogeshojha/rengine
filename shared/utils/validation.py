import ipaddress
import re

import validators

from shared.enums.target import TargetType

HEX_COLOR_LENGTH = 7  # e.g., #RRGGBB


def validate_domain(value: str) -> bool:
    """Validate domain/subdomain format"""
    return validators.domain(value) is True


def validate_ip(value: str) -> bool:
    """Validate single IP address"""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def validate_ip_range(value: str) -> bool:
    """Validate IP range in CIDR notation"""
    try:
        ipaddress.ip_network(value, strict=False)
        return "/" in value
    except ValueError:
        return False


def validate_asn(value: str) -> bool:
    """Validate ASN format (AS followed by numbers)"""
    asn_pattern = r"^AS\d+$"
    return bool(re.match(asn_pattern, value.upper()))


def validate_url(value: str) -> bool:
    """Validate fully qualified URL"""
    return validators.url(value) is True


def validate_target(target_value: str) -> TargetType | None:
    """
    Validate and auto-detect target type from value.
    This is our main validator for targets, each target MUST pass this validation before being accepted.
    Also needs to be ported to frontend for immediate feedback to users by either copying the logic or creating an API endpoint for validation.

    Returns: TargetType if valid, None if invalid
    """
    _validators = [
        (TargetType.IP_RANGE, validate_ip_range),
        (TargetType.IP, validate_ip),
        (TargetType.URL, validate_url),
        (TargetType.ASN, validate_asn),
        (TargetType.DOMAIN, validate_domain),
    ]

    for target_type, validator_func in _validators:
        if validator_func(target_value):
            return target_type

    return None


def normalize_query(query: str, target_type: TargetType) -> str:
    """Normalize query value for WHOIS cache key dedup."""
    match target_type:
        case TargetType.DOMAIN:
            return normalize_domain(query)
        case TargetType.URL:
            return normalize_domain(extract_domain_from_url(query))
        case TargetType.ASN:
            return str(extract_asn_number(query))
        case _:
            return query.strip()


def normalize_domain(domain: str) -> str:
    """Normalize a domain name for consistent lookups."""
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
    return domain.rstrip(".")


def extract_asn_number(query: str) -> int:
    """Extract the numeric ASN from a query like 'AS13335' or '13335'."""
    cleaned = re.sub(r"^[Aa][Ss]", "", query.strip())
    return int(cleaned)


def extract_domain_from_url(url: str) -> str:
    """Extract the domain from a URL."""
    return normalize_domain(url)


def validate_hex_color(color: str) -> str:
    """
    Validate hex color format (#RRGGBB).
    """
    color = color.strip()
    if not color.startswith("#"):
        msg = "Color must start with #"
        raise ValueError(msg)
    if len(color) != HEX_COLOR_LENGTH:
        msg = f"Color must be in format #RRGGBB ({HEX_COLOR_LENGTH} characters)"
        raise ValueError(msg)
    hex_pattern = r"^#[0-9A-Fa-f]{6}$"
    if not re.match(hex_pattern, color):
        msg = "Color must contain valid hexadecimal characters (0-9, A-F)"
        raise ValueError(msg)
    return color.upper()
