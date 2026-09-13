"""The export vocabulary: what a run writes, where it lands and how long it stays."""

from __future__ import annotations

from enum import StrEnum

EXPORT_ROOT = "/app/exports-out"
RETENTION_DAYS = 30
MAX_EXPORT_ROWS = 50_000
EXPORT_CHUNK = 1_000
MAX_RUNNING_PER_PROJECT = 3
# a run that has not reported in this long is not running any more
STALE_AFTER_SECONDS = 3_600
BUNDLE = "bundle"


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    TXT = "txt"


EXPORT_FORMATS: tuple[str, ...] = tuple(f.value for f in ExportFormat)

FORMAT_LABELS: dict[str, str] = {
    ExportFormat.CSV.value: "CSV",
    ExportFormat.JSON.value: "JSON",
    ExportFormat.TXT.value: "Text",
}

FORMAT_MEDIA_TYPES: dict[str, str] = {
    ExportFormat.CSV.value: "text/csv",
    ExportFormat.JSON.value: "application/json",
    ExportFormat.TXT.value: "text/plain",
}

FORMAT_EXTENSIONS: dict[str, str] = {
    ExportFormat.CSV.value: "csv",
    ExportFormat.JSON.value: "json",
    ExportFormat.TXT.value: "txt",
}

BUNDLE_MEDIA_TYPE = "application/zip"
BUNDLE_EXTENSION = "zip"


class ExportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


EXPORT_STATUS_LABELS: dict[str, str] = {
    ExportStatus.QUEUED.value: "Queued",
    ExportStatus.RUNNING.value: "Preparing",
    ExportStatus.COMPLETED.value: "Ready",
    ExportStatus.FAILED.value: "Failed",
    ExportStatus.EXPIRED.value: "Expired",
}

TERMINAL_STATUSES: tuple[str, ...] = (
    ExportStatus.COMPLETED.value,
    ExportStatus.FAILED.value,
    ExportStatus.EXPIRED.value,
)

LIVE_STATUSES: tuple[str, ...] = (
    ExportStatus.QUEUED.value,
    ExportStatus.RUNNING.value,
)


class ExportScope(StrEnum):
    SCAN = "scan"
    TARGET = "target"
    PROJECT = "project"


EXPORT_SCOPES: tuple[str, ...] = tuple(s.value for s in ExportScope)
