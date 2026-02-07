import re

from zxcvbn import zxcvbn

from app.config import settings

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
