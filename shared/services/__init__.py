__all__ = [
    "get_or_create_organization",
    "get_or_create_tag",
]


def __getattr__(name: str):
    if name == "get_or_create_organization":
        from shared.services.organization import (  # noqa: PLC0415
            get_or_create_organization,
        )

        return get_or_create_organization
    if name == "get_or_create_tag":
        from shared.services.tag import (  # noqa: PLC0415
            get_or_create_tag,
        )

        return get_or_create_tag
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
