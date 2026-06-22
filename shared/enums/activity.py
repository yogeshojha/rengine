from enum import Enum


class ActivityLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class ActivityEvent(Enum):
    # target events
    TARGET_CREATED = "target.created"
    TARGET_UPDATED = "target.updated"
    TARGET_DELETED = "target.deleted"
    TARGET_BULK_IMPORTED = "target.bulk_imported"

    # target enrichment events
    TARGET_ENRICHMENT_STARTED = "target.enrichment.started"
    TARGET_ENRICHMENT_WHOIS_COMPLETED = "target.enrichment.whois.completed"
    TARGET_ENRICHMENT_WHOIS_FAILED = "target.enrichment.whois.failed"
    TARGET_ENRICHMENT_DNS_COMPLETED = "target.enrichment.dns.completed"
    TARGET_ENRICHMENT_DNS_FAILED = "target.enrichment.dns.failed"
    TARGET_ENRICHMENT_BGP_COMPLETED = "target.enrichment.bgp.completed"
    TARGET_ENRICHMENT_BGP_FAILED = "target.enrichment.bgp.failed"

    # scan events
    SCAN_STARTED = "scan.started"
    SCAN_PROGRESS = "scan.progress"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"

    # project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"

    # system events
    SYSTEM_USER_LOGIN = "system.user.login"
    SYSTEM_USER_LOGOUT = "system.user.logout"
    SYSTEM_USER_CREATED = "system.user.created"
    SYSTEM_CONFIG_UPDATED = "system.config.updated"
