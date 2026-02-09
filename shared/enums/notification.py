from enum import Enum


class NotificationType(Enum):
    SCAN = "scan"  # scan specific notifications
    SYSTEM = "system"  # system-wide notifications like updates
    SECURITY = "security"  # security alerts like invalid logins
    VULNERABILITY = "vulnerability"  # vulnerability related notifications
    TARGET = "target"  # target related notifications like imports
    RESOURCE = "resource"  # resource related notifications like storage etc limits
    INTEGRATION = "integration"  # like failed telegram/webhook notifications


class NotificationSeverity(Enum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
