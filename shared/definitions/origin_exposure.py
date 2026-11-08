from __future__ import annotations

from enum import StrEnum


class OriginKind(StrEnum):
    ORIGIN_EXPOSED = "origin_exposed"
    DEFAULT_VHOST = "default_vhost"


class OriginConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
