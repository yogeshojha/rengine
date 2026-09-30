from enum import Enum


class NotificationType(Enum):
    SCAN = "scan"
    SYSTEM = "system"
    SECURITY = "security"
    VULNERABILITY = "vulnerability"
    TARGET = "target"
    RESOURCE = "resource"
    INTEGRATION = "integration"
    WATCH = "watch"
    NEW_CHECKS = "new_checks"
    TRIPWIRE = "tripwire"


class NotificationSeverity(Enum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
