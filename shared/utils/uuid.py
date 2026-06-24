import uuid


def uuid_list(items) -> list[uuid.UUID]:
    return [uuid.UUID(str(i)) for i in (items or [])]
