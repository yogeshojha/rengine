import re

from zxcvbn import zxcvbn

from app.config import settings

MIN_PASSWORD_SCORE = 3
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 1024


MIN_USERNAME_LENGTH = 4
MAX_USERNAME_LENGTH = 50


def validate_password_strength(
    password: str,
    user_inputs: list[str] | None = None,
) -> str:
    if len(password) > MAX_PASSWORD_LENGTH:
        return_error = f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        raise ValueError(return_error)

    if settings.DEBUG:
        return password

    if len(password) < MIN_PASSWORD_LENGTH:
        return_error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        raise ValueError(return_error)

    result = zxcvbn(password, user_inputs=user_inputs or [])

    if result["score"] < MIN_PASSWORD_SCORE:
        return_error = (
            "Password is too weak. Use a longer password that is not a common "
            "word or pattern."
        )
        raise ValueError(return_error)

    return password


def validate_username(username: str) -> str:
    if len(username) < MIN_USERNAME_LENGTH:
        return_error = f"Username must be at least {MIN_USERNAME_LENGTH} characters."
        raise ValueError(return_error)

    if len(username) > MAX_USERNAME_LENGTH:
        return_error = f"Username must be at most {MAX_USERNAME_LENGTH} characters."
        raise ValueError(return_error)

    if not re.match(r"^[a-zA-Z]", username):
        return_error = "Username must start with a letter."
        raise ValueError(return_error)

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_.]*$", username):
        return_error = (
            "Username can contain only letters, digits, underscores and dots."
        )
        raise ValueError(return_error)

    return username
