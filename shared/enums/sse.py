from enum import StrEnum


class SSEChannel(StrEnum):
    BROADCAST = "broadcast"
    PROJECT = "project"
    SCAN = "scan"
    REPORT = "report"

    @staticmethod
    def project(project_id: str) -> str:
        return f"{SSEChannel.PROJECT}:{project_id}"

    @staticmethod
    def scan(scan_id: str) -> str:
        return f"{SSEChannel.SCAN}:{scan_id}"

    @staticmethod
    def report(report_id: str) -> str:
        return f"{SSEChannel.REPORT}:{report_id}"


class SSEEventType(StrEnum):
    NOTIFICATION = "notification"
    ACTIVITY = "activity"
    SCAN = "scan"
    REPORT = "report"
