import ipaddress
import re

import validators

from shared.enums.target import TargetType

HEX_COLOR_LENGTH = 7  # e.g., #RRGGBB
MAX_NAME_LEN = 120


def clean_name(v: str, *, max_len: int = MAX_NAME_LEN) -> str:
    v = (v or "").strip()
    if not v:
        msg = "Name must not be empty."
        raise ValueError(msg)
    if len(v) > max_len:
        msg = f"Name must be {max_len} characters or fewer."
        raise ValueError(msg)
    return v


def clean_optional_name(v: str | None, *, max_len: int = MAX_NAME_LEN) -> str | None:
    """An update that omits the name leaves it alone; one that sends it must send a real one."""
    return None if v is None else clean_name(v, max_len=max_len)


def validate_domain(value: str) -> bool:
    return validators.domain(value) is True


def validate_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def validate_ip_range(value: str) -> bool:
    try:
        ipaddress.ip_network(value, strict=False)
        return "/" in value
    except ValueError:
        return False


def validate_asn(value: str) -> bool:
    asn_pattern = r"^AS\d+$"
    return bool(re.match(asn_pattern, value.upper()))


WEB_SCHEMES = ("http://", "https://")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def validate_url(value: str) -> bool:
    # reNgine scans over HTTP; another scheme is not a target it can do anything with
    return value.lower().startswith(WEB_SCHEMES) and validators.url(value) is True


def normalize_target_value(value: str) -> str:
    """What a user typed, reduced to the form reNgine validates and stores."""
    v = (value or "").strip()
    if not v or _SCHEME.match(v):
        return v
    # a scope list writes *.example.com for a domain and everything under it
    v = v.removeprefix("*.")
    # a pasted hostname often carries a trailing slash or the root dot
    return v.rstrip("/").rstrip(".")


TARGET_FORMAT_HINT = "Enter a domain, IP address, CIDR range, URL or ASN."
_MAX_ECHO = 120


def unrecognised_target(value: str) -> str:
    """The one wording for a target value reNgine cannot read."""
    shown = (value or "").strip()[:_MAX_ECHO]
    return f"Unrecognised target: {shown}. {TARGET_FORMAT_HINT}"


def validate_target(target_value: str) -> TargetType | None:
    value = normalize_target_value(target_value)
    if not value:
        return None
    _validators = [
        (TargetType.IP_RANGE, validate_ip_range),
        (TargetType.IP, validate_ip),
        (TargetType.URL, validate_url),
        (TargetType.ASN, validate_asn),
        (TargetType.DOMAIN, validate_domain),
    ]

    for target_type, validator_func in _validators:
        if validator_func(value):
            return target_type

    return None


def normalize_query(query: str, target_type: TargetType) -> str:
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
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
    return domain.rstrip(".")


def extract_asn_number(query: str) -> int:
    cleaned = re.sub(r"^[Aa][Ss]", "", query.strip())
    return int(cleaned)


def extract_domain_from_url(url: str) -> str:
    return normalize_domain(url)


def validate_hex_color(color: str) -> str:
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
