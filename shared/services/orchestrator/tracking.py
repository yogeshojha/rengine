import logging
import uuid
from collections.abc import Callable

from sqlalchemy import update
from sqlalchemy.orm import Session

from shared.definitions.constants import MAX_COMMAND_OUTPUT
from shared.enums.scan import ScanActivityStatus
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.scan_command import ScanCommand
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.scan_resolve import redact_command
from shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class ScanActivityService:
    """Per-stage activity timeline (create RUNNING, transition to terminal)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        scan: Scan,
        *,
        name: str,
        title: str,
        celery_task_id: str | None = None,
    ) -> ScanActivity:
        activity = ScanActivity(
            scan_id=scan.id,
            project_id=scan.project_id,
            name=name,
            title=title,
            status=ScanActivityStatus.RUNNING.value,
            celery_task_id=celery_task_id,
            started_at=utc_now(),
        )
        self.session.add(activity)
        self.session.commit()
        self.session.refresh(activity)
        return activity

    def finish(
        self,
        activity: ScanActivity,
        *,
        status: ScanActivityStatus,
        result: dict | None = None,
        error: str | None = None,
        traceback: str | None = None,
    ) -> None:
        # Conditional update: only transition from RUNNING, so a concurrent cancel
        # that flipped this row to ABORTED is never clobbered back to success/failed.
        self.session.execute(
            update(ScanActivity)
            .where(
                ScanActivity.id == activity.id,
                ScanActivity.status == ScanActivityStatus.RUNNING.value,
            )
            .values(
                status=status.value,
                result=result or {},
                error=redact_command(error)[:2000] if error else None,
                traceback=redact_command(traceback) if traceback else None,
                completed_at=utc_now(),
            )
        )
        self.session.commit()


class ScanCommandRecorder:
    """Registers every command + captures its log; thread-safe (fresh session per write)."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        scan_id: uuid.UUID,
        project_id: uuid.UUID,
        activity_id: uuid.UUID | None = None,
        events: ScanEventPublisher | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._scan_id = scan_id
        self._project_id = project_id
        self._activity_id = activity_id
        self._events = events

    def start(self, tool: str, command: str) -> uuid.UUID:
        cmd = ScanCommand(
            scan_id=self._scan_id,
            project_id=self._project_id,
            activity_id=self._activity_id,
            tool=tool,
            command=redact_command(command),
            status=ScanActivityStatus.RUNNING.value,
            started_at=utc_now(),
        )
        with self._session_factory() as session:
            session.add(cmd)
            session.commit()
            session.refresh(cmd)
            command_id = cmd.id
            stored_command = cmd.command
        if self._events is not None:
            try:
                self._events.command_started(
                    command_id=command_id,
                    activity_id=self._activity_id,
                    tool=tool,
                    command=stored_command,
                )
            except Exception:
                logger.debug("command_started event emit failed", exc_info=True)
        return command_id

    def finish(
        self,
        command_id: uuid.UUID,
        *,
        return_code: int,
        output: str,
        error: str | None,
        duration_seconds: float,
    ) -> None:
        status = (
            ScanActivityStatus.SUCCESS
            if return_code == 0
            else ScanActivityStatus.FAILED
        )
        try:
            with self._session_factory() as session:
                cmd = session.get(ScanCommand, command_id)
                # skip if a cancel already flipped this command to a terminal status
                if cmd is None or cmd.status != ScanActivityStatus.RUNNING.value:
                    return
                cmd.status = status.value
                cmd.return_code = return_code
                cmd.output = redact_command(output or "")[:MAX_COMMAND_OUTPUT]
                cmd.error = redact_command(error)[:2000] if error else None
                cmd.duration_seconds = duration_seconds
                cmd.completed_at = utc_now()
                session.add(cmd)
                session.commit()
                tool = cmd.tool
        except Exception:
            logger.warning("scan command finish failed", exc_info=True)
            return
        if self._events is not None:
            try:
                self._events.command_finished(
                    command_id=command_id,
                    activity_id=self._activity_id,
                    tool=tool,
                    return_code=return_code,
                    status=status.value,
                    duration_seconds=duration_seconds,
                )
            except Exception:
                logger.debug("command_finished event emit failed", exc_info=True)
