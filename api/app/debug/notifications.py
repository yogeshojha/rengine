from app.enums.notification import NotificationSeverity, NotificationType
from app.models.notification import NotificationMetadata

DEBUG_NOTIFICATION_TEMPLATES = [
    # Scan notifications
    {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.SUCCESS,
        "title": "Debug: Scan Completed",
        "message": "Subdomain enumeration scan completed successfully",
        "metadata": NotificationMetadata(
            url="/scans/debug-123",
            scan_id="debug-123",
            action_label="View Results",
        ),
    },
    {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.ERROR,
        "title": "Debug: Scan Failed",
        "message": "Connection timeout while scanning target",
        "metadata": NotificationMetadata(
            url="/scans/debug-456",
            scan_id="debug-456",
        ),
    },
    {
        "type": NotificationType.SCAN,
        "severity": NotificationSeverity.INFO,
        "title": "Debug: Scan Started",
        "message": "Port scan initiated for example.com",
        "metadata": NotificationMetadata(
            url="/scans/debug-789",
            scan_id="debug-789",
        ),
    },
    # System notifications
    {
        "type": NotificationType.SYSTEM,
        "severity": NotificationSeverity.INFO,
        "title": "Debug: Update Available",
        "message": "reNgine v3.1.0 is now available",
        "metadata": NotificationMetadata(
            url="https://github.com/yogeshojha/rengine/releases",
            open_new_tab=True,
            action_label="View Release",
        ),
    },
    {
        "type": NotificationType.SYSTEM,
        "severity": NotificationSeverity.WARNING,
        "title": "Debug: Maintenance Scheduled",
        "message": "System maintenance scheduled for tonight at 2 AM",
        "metadata": NotificationMetadata(),
    },
    # Vulnerability notifications
    {
        "type": NotificationType.VULNERABILITY,
        "severity": NotificationSeverity.ERROR,
        "title": "Debug: Critical Vulnerability Found",
        "message": "CVE-2024-1234 detected on api.example.com",
        "metadata": NotificationMetadata(
            url="/vulnerabilities/debug-001",
            action_label="View Details",
        ),
    },
    {
        "type": NotificationType.VULNERABILITY,
        "severity": NotificationSeverity.WARNING,
        "title": "Debug: Medium Severity Vulnerability",
        "message": "XSS vulnerability found on login page",
        "metadata": NotificationMetadata(
            url="/vulnerabilities/debug-002",
        ),
    },
    # Target notifications
    {
        "type": NotificationType.TARGET,
        "severity": NotificationSeverity.WARNING,
        "title": "Debug: Target Unreachable",
        "message": "Target example.com is not responding",
        "metadata": NotificationMetadata(
            url="/targets/debug-target-2",
            target_id="debug-target-2",
        ),
    },
    # Resource notifications
    {
        "type": NotificationType.RESOURCE,
        "severity": NotificationSeverity.WARNING,
        "title": "Debug: Low Disk Space",
        "message": "Available disk space is below 10GB",
        "metadata": NotificationMetadata(
            url="/settings/storage",
            action_label="Manage Storage",
        ),
    },
    {
        "type": NotificationType.RESOURCE,
        "severity": NotificationSeverity.ERROR,
        "title": "Debug: High Memory Usage",
        "message": "Memory usage exceeded 90%",
        "metadata": NotificationMetadata(
            url="/settings/resources",
        ),
    },
    # Integration notifications
    {
        "type": NotificationType.INTEGRATION,
        "severity": NotificationSeverity.ERROR,
        "title": "Debug: Slack Integration Failed",
        "message": "Failed to send notification to Slack. Check credentials.",
        "metadata": NotificationMetadata(
            url="/settings/integrations",
        ),
    },
    {
        "type": NotificationType.INTEGRATION,
        "severity": NotificationSeverity.SUCCESS,
        "title": "Debug: Integration Connected",
        "message": "Successfully connected to GitHub API",
        "metadata": NotificationMetadata(
            url="/settings/integrations",
        ),
    },
]
