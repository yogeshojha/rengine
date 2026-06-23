import logging
import uuid
from typing import Any

from shared.enums.scan import ScanEventKind
from shared.enums.sse import SSEChannel, SSEEventType
from shared.services.event_publisher import SyncEventPublisher

logger = logging.getLogger(__name__)


def _opt_id(value: uuid.UUID | str | None) -> str | None:
    return str(value) if value else None


class ScanEventPublisher:
    def __init__(self, redis_url: str, *, scan_id: str, project_id: str) -> None:
        self._pub = SyncEventPublisher(redis_url)
        self._scan_id = str(scan_id)
        self._project_id = str(project_id)

    def _emit(self, kind: ScanEventKind, data: dict[str, Any]) -> None:
        payload = {"kind": kind.value, "scan_id": self._scan_id, **data}
        self._pub.publish(SSEChannel.scan(self._scan_id), SSEEventType.SCAN, payload)
        self._pub.publish(
            SSEChannel.project(self._project_id), SSEEventType.SCAN, payload
        )

    def scan_started(self, *, status: str, engine: str) -> None:
        self._emit(ScanEventKind.SCAN_STARTED, {"status": status, "engine": engine})

    def scan_completed(
        self, *, status: str, counts: dict, duration_seconds: float | None
    ) -> None:
        self._emit(
            ScanEventKind.SCAN_COMPLETED,
            {"status": status, "counts": counts, "duration_seconds": duration_seconds},
        )

    def scan_failed(self, *, status: str, error: str | None) -> None:
        self._emit(ScanEventKind.SCAN_FAILED, {"status": status, "error": error})

    def scan_cancelled(self, *, status: str) -> None:
        self._emit(ScanEventKind.SCAN_CANCELLED, {"status": status})

    def stage_started(
        self, *, activity_id: uuid.UUID | str | None, stage: str, title: str
    ) -> None:
        self._emit(
            ScanEventKind.STAGE_STARTED,
            {"activity_id": _opt_id(activity_id), "stage": stage, "title": title},
        )

    def stage_progress(
        self,
        *,
        activity_id: uuid.UUID | str | None,
        stage: str,
        message: str,
        source: str | None = None,
    ) -> None:
        self._emit(
            ScanEventKind.STAGE_PROGRESS,
            {
                "activity_id": _opt_id(activity_id),
                "stage": stage,
                "message": message,
                "source": source,
            },
        )

    def stage_completed(
        self,
        *,
        activity_id: uuid.UUID | str | None,
        stage: str,
        status: str,
        counts: dict | None = None,
    ) -> None:
        self._emit(
            ScanEventKind.STAGE_COMPLETED,
            {
                "activity_id": _opt_id(activity_id),
                "stage": stage,
                "status": status,
                "counts": counts or {},
            },
        )

    def command_started(
        self,
        *,
        command_id: uuid.UUID | str,
        activity_id: uuid.UUID | str | None,
        tool: str,
        command: str,
    ) -> None:
        self._emit(
            ScanEventKind.COMMAND_STARTED,
            {
                "command_id": _opt_id(command_id),
                "activity_id": _opt_id(activity_id),
                "tool": tool,
                "command": command,
            },
        )

    def command_finished(
        self,
        *,
        command_id: uuid.UUID | str,
        activity_id: uuid.UUID | str | None,
        tool: str,
        return_code: int,
        status: str,
        duration_seconds: float,
    ) -> None:
        self._emit(
            ScanEventKind.COMMAND_FINISHED,
            {
                "command_id": _opt_id(command_id),
                "activity_id": _opt_id(activity_id),
                "tool": tool,
                "return_code": return_code,
                "status": status,
                "duration_seconds": duration_seconds,
            },
        )
