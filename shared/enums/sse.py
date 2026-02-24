"""SSE channel and event type definitions.

Single source of truth for all channel patterns and event types.

Channels define the routing scope:
    - BROADCAST: these are system wide like notifications
    - PROJECT: scoped to a project, only subscribers receive

Event types define what happened within a channel:
    - NOTIFICATION: system notification
    - ACTIVITY: activity log entry
"""

from enum import StrEnum


class SSEChannel(StrEnum):
    """SSE channel prefixes."""

    BROADCAST = "broadcast"
    PROJECT = "project"

    @staticmethod
    def project(project_id: str) -> str:
        """Build a project-scoped channel name."""
        return f"{SSEChannel.PROJECT}:{project_id}"


class SSEEventType(StrEnum):
    """Event types published within SSE channels."""

    NOTIFICATION = "notification"
    ACTIVITY = "activity"
    # TODO: Add target scan details
