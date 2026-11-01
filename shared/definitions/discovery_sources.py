"""What each subdomain source contributed to a run, as the stage records it."""

from __future__ import annotations

from enum import StrEnum


class SourceStatus(StrEnum):
    FOUND = "found"
    EMPTY = "empty"
    FAILED = "failed"
    SKIPPED = "skipped"


SOURCES_KEY = "sources"
UNKEYED_KEY = "sources_without_key"
NOTE_KEY = "sources_note"
