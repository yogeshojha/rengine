from enum import StrEnum


class SSEChannel(StrEnum):
    BROADCAST = "broadcast"
    PROJECT = "project"
    SCAN = "scan"

    @staticmethod
    def project(project_id: str) -> str:
        return f"{SSEChannel.PROJECT}:{project_id}"

    @staticmethod
    def scan(scan_id: str) -> str:
        return f"{SSEChannel.SCAN}:{scan_id}"


class SSEEventType(StrEnum):
    NOTIFICATION = "notification"
    ACTIVITY = "activity"
    SCAN = "scan"
