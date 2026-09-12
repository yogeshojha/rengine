"""Note anchors, and the asset identity each dimension uses."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.surface import SurfaceDimension


class NoteStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


NOTE_STATUSES: tuple[str, ...] = tuple(s.value for s in NoteStatus)

MAX_NOTE_BODY = 20000
MAX_NOTE_TITLE = 200
MAX_NOTE_TAGS = 20
MAX_ASSET_KEY = 500
MAX_ASSET_LABEL = 500

# each dimension's identity column
ASSET_IDENTITY: dict[str, str] = {
    SurfaceDimension.WEB_ASSETS.value: "name",
    SurfaceDimension.ENDPOINTS.value: "signature",
    SurfaceDimension.SERVICES.value: "ip",
    SurfaceDimension.IPS.value: "ip",
    SurfaceDimension.VULNERABILITIES.value: "fingerprint",
    SurfaceDimension.SOFTWARE.value: "fingerprint",
}

STATUS_LABELS: dict[str, str] = {
    NoteStatus.OPEN.value: "Open",
    NoteStatus.RESOLVED.value: "Resolved",
}


def service_key(ip: str, port: int) -> str:
    return f"{ip}:{port}"
