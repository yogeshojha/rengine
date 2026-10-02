"""Note anchors, and the asset identity each dimension uses."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import VulnState


class NoteStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


NOTE_STATUSES: tuple[str, ...] = tuple(s.value for s in NoteStatus)


# what a note with no asset is written on
class NoteSubject(StrEnum):
    TARGET = "target"
    SCAN = "scan"


NOTE_SUBJECTS: tuple[str, ...] = tuple(s.value for s in NoteSubject)

# the review states a triage reason records
TRIAGE_REASON_STATES: tuple[str, ...] = tuple(
    s.value for s in VulnState if s is not VulnState.OPEN
)

MAX_NOTE_BODY = 20000
MAX_NOTE_TITLE = 200
MAX_NOTE_TAGS = 20
MAX_NOTE_TAG_CHARS = 32
MAX_NOTE_TAG_SUGGESTIONS = 50
MAX_NOTE_FACET_VALUES = 50
# joins a dimension and an asset key in the asset filter
NOTE_ASSET_SEPARATOR = ":"
# allowed in a note tag beside letters and digits
NOTE_TAG_PUNCTUATION = "._-:"
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
    SurfaceDimension.SECRETS.value: "fingerprint",
}
