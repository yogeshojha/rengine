import ipaddress
import re

import validators

from shared.enums.target import TargetType


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
    validators = [
        (TargetType.IP_RANGE, validate_ip_range),
        (TargetType.IP, validate_ip),
        (TargetType.URL, validate_url),
        (TargetType.ASN, validate_asn),
        (TargetType.DOMAIN, validate_domain),
    ]

    for target_type, validator_func in validators:
        if validator_func(target_value):
            return target_type

    return None
