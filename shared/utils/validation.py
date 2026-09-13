import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

import validators

from shared.enums.target import TargetType

HEX_COLOR_LENGTH = 7  # #RRGGBB
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
    """An update that omits the name leaves it alone."""
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


MAX_ASN = 4294967295
_ASN_SHAPE = re.compile(r"^AS(\d+)$")


def validate_asn(value: str) -> bool:
    match = _ASN_SHAPE.match(value.upper())
    return bool(match) and 0 < int(match.group(1)) <= MAX_ASN


WEB_SCHEMES = ("http://", "https://")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def validate_url(value: str) -> bool:
    return value.lower().startswith(WEB_SCHEMES) and validators.url(value) is True


def _lower_host(netloc: str) -> str:
    """Case-fold the host, leaving any userinfo as written."""
    userinfo, sep, host = netloc.rpartition("@")
    return f"{userinfo}{sep}{host.lower()}"


def _normalize_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit(
        parts._replace(scheme=parts.scheme.lower(), netloc=_lower_host(parts.netloc))
    )


def normalize_target_value(value: str) -> str:
    """Normalized target value. Host names are case-folded so one host is one target."""
    v = (value or "").strip()
    if not v:
        return v
    if _SCHEME.match(v):
        return _normalize_url(v)
    v = v.removeprefix("*.")
    return v.rstrip("/").rstrip(".").lower()


TARGET_FORMAT_HINT = "Enter a domain, IP address, CIDR range, URL or ASN."
_MAX_ECHO = 120


def unrecognised_target(value: str) -> str:
    """Wording for a target value the scanner will not take."""
    shown = (value or "").strip()[:_MAX_ECHO]
    return _refusal(normalize_target_value(shown), shown) or (
        f"Unrecognised target: {shown}. {TARGET_FORMAT_HINT}"
    )


def _refusal(value: str, shown: str) -> str | None:
    """The reason, when the value has the right shape but is out of bounds."""
    if _ASN_SHAPE.match(value.upper()):
        return f"{shown} is out of range. An AS number runs from 1 to {MAX_ASN}."
    try:
        block = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return None
    if block.prefixlen == 0:
        return f"{shown} covers every address. Enter the range you own."
    return (
        f"{shown} is out of scope. Loopback, link-local, multicast and reserved "
        "address space are not scanned."
    )


def _routable(address) -> bool:
    return not (
        address.is_unspecified
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
    )


def scannable_address(value: str) -> bool:
    """Address space a scan may be aimed at. Private ranges stay in for corporate estates."""
    try:
        return _routable(ipaddress.ip_address(value))
    except ValueError:
        return False


def _scannable(value: str, target_type: TargetType) -> bool:
    """Address space a scan may be aimed at. Private ranges stay in for corporate estates."""
    if target_type is TargetType.IP_RANGE:
        block = ipaddress.ip_network(value, strict=False)
        return block.prefixlen > 0 and _routable(block.network_address)
    if target_type is TargetType.IP:
        return scannable_address(value)
    return True


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
            return target_type if _scannable(value, target_type) else None

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
        msg = f"Color must be {HEX_COLOR_LENGTH} characters in the form #RRGGBB"
        raise ValueError(msg)
    hex_pattern = r"^#[0-9A-Fa-f]{6}$"
    if not re.match(hex_pattern, color):
        msg = "Color must use hexadecimal digits 0-9 and A-F"
        raise ValueError(msg)
    return color.upper()


_HOST_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9_](?:[a-z0-9_-]{0,62}[a-z0-9_])?\.)+[a-z0-9][a-z0-9-]{0,62}$"
)


def normalize_host(raw: str) -> str | None:
    """A bare host name, wildcard label and trailing dot stripped. None when it is not one."""
    if not raw:
        return None
    name = raw.strip().lower().rstrip(".")
    if name.startswith("*."):
        name = name[2:]
    if not name or "." not in name or " " in name or "/" in name or "@" in name:
        return None
    if not _HOST_RE.match(name):
        return None
    return name
