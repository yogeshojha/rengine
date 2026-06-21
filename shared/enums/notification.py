from enum import Enum


class NotificationType(Enum):
    SCAN = "scan"
    SYSTEM = "system"
    SECURITY = "security"
    VULNERABILITY = "vulnerability"
    TARGET = "target"
    RESOURCE = "resource"
    INTEGRATION = "integration"


class NotificationSeverity(Enum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
