"""Notice derivation."""

from __future__ import annotations

from shared.definitions.connectors import COMMON_METHODS, NoticeKind
from shared.definitions.endpoints import ADMIN_INTERESTS, SENSITIVE_INTERESTS

_SERVER_ERROR = 500


def notices_for(
    *,
    interests: list[str],
    methods: list[str],
    status_code: int | None,
    known: bool,
    in_scope: bool,
    out_of_scope: bool = False,
) -> list[str]:
    found: set[str] = set()
    if out_of_scope:
        found.add(NoticeKind.OUT_OF_SCOPE.value)
    interest = set(interests)
    if interest & SENSITIVE_INTERESTS:
        found.add(NoticeKind.SENSITIVE.value)
    if interest & ADMIN_INTERESTS:
        found.add(NoticeKind.ADMIN.value)
    if in_scope and not known:
        found.add(NoticeKind.UNSEEN_BY_SCANS.value)
    if status_code is not None and status_code >= _SERVER_ERROR:
        found.add(NoticeKind.SERVER_ERROR.value)
    if any(method.upper() not in COMMON_METHODS for method in methods):
        found.add(NoticeKind.NON_STANDARD_METHOD.value)
    return sorted(found)
