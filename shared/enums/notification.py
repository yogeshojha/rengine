from enum import Enum


class NotificationType(str, Enum):
    SCAN = "scan"  # scan specific notifications
    SYSTEM = "system"  # system-wide notifications like updates
    SECURITY = "security"  # security alerts like invalid logins
    VULNERABILITY = "vulnerability"  # vulnerability related notifications
    TARGET = "target"  # target related notifications like imports
    RESOURCE = "resource"  # resource related notifications like storage etc limits
    INTEGRATION = "integration"  # like failed telegram/webhook notifications


class NotificationSeverity(str, Enum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
