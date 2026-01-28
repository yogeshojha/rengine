import ipaddress
import re

import validators
from zxcvbn import zxcvbn

from app.config import settings
from app.enums.target import TargetType

# Password policy
MIN_PASSWORD_SCORE = 3
MIN_PASSWORD_LENGTH = 10


# Username policy
MIN_USERNAME_LENGTH = 4
MAX_USERNAME_LENGTH = 50


def validate_password_strength(
    password: str,
    user_inputs: list[str] | None = None,
) -> str:
    """
    Validate password strength using zxcvbn.

    Args:
        password: The password to validate
        user_inputs: Optional list of user-specific inputs (email, username) to check against

    Returns:
        The validated password

    Raises:
        ValueError: If password doesn't meet requirements
    """
    # Skip validation in DEBUG mode
    if settings.DEBUG:
        return password

    if len(password) < MIN_PASSWORD_LENGTH:
        return_error = (
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )
        raise ValueError(return_error)

    result = zxcvbn(password, user_inputs=user_inputs or [])

    if result["score"] < MIN_PASSWORD_SCORE:
        return_error = (
            "Password is too weak. Consider using a stronger password with a "
            "mix of uppercase, lowercase, numbers, and special characters."
        )
        raise ValueError(return_error)

    if result["guesses_log10"] < MIN_PASSWORD_SCORE:
        return_error = "Password is too guessable. Choose a less common password."
        raise ValueError(return_error)

    return password


def validate_username(username: str) -> str:
    """
    Validate username format and length.

    Args:
        username: The username to validate

    Returns:
        The validated username

    Raises:
        ValueError: If username doesn't meet requirements
    """
    if len(username) < MIN_USERNAME_LENGTH:
        return_error = (
            f"Username must be at least {MIN_USERNAME_LENGTH} characters long"
        )
        raise ValueError(return_error)

    if len(username) > MAX_USERNAME_LENGTH:
        return_error = f"Username must be at most {MAX_USERNAME_LENGTH} characters long"
        raise ValueError(return_error)

    # change the conditions if needed for organization specific but not recommended
    # COndition: Must start with a letter
    if not re.match(r"^[a-zA-Z]", username):
        return_error = "Username must start with a letter"
        raise ValueError(return_error)

    # Condition: Can only contain letters, numbers, underscores, and dots
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_.]*$", username):
        return_error = (
            "Username can only contain letters, numbers, underscores, and dots"
        )
        raise ValueError(return_error)

    return username


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
