from enum import StrEnum


class SSEChannel(StrEnum):
    BROADCAST = "broadcast"
    PROJECT = "project"

    @staticmethod
    def project(project_id: str) -> str:
        return f"{SSEChannel.PROJECT}:{project_id}"


class SSEEventType(StrEnum):
    NOTIFICATION = "notification"
    ACTIVITY = "activity"
    # TODO: Add target scan details
