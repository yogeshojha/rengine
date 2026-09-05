from enum import Enum


class ScanStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanActivityStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ABORTED = "aborted"


SCAN_LIVE_STATUSES = (ScanStatus.PENDING.value, ScanStatus.RUNNING.value)
SCAN_TERMINAL_STATUSES = (
    ScanStatus.COMPLETED.value,
    ScanStatus.FAILED.value,
    ScanStatus.CANCELLED.value,
)
ACTIVITY_TERMINAL_STATUSES = (
    ScanActivityStatus.SUCCESS.value,
    ScanActivityStatus.FAILED.value,
    ScanActivityStatus.SKIPPED.value,
    ScanActivityStatus.ABORTED.value,
)


class Intensity(Enum):
    PASSIVE = "passive"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"


INTENSITIES = tuple(i.value for i in Intensity)


class Phase(Enum):
    DISCOVERY = "discovery"
    EXPANSION = "expansion"
    DEPTH = "depth"
    FINALIZE = "finalize"


PHASE_ORDER: dict[str, int] = {
    Phase.DISCOVERY.value: 0,
    Phase.EXPANSION.value: 1,
    Phase.DEPTH.value: 2,
    Phase.FINALIZE.value: 3,
}


class AssetKind(Enum):
    HOSTS = "hosts"
    ADDRESSES = "addresses"
    PORTS = "ports"
    HTTP_ASSETS = "http_assets"
    ENDPOINTS = "endpoints"
    VULNERABILITIES = "vulnerabilities"


class StageRole(Enum):
    CAPABILITY = "capability"
    SUPPORT = "support"


class StageGroup(Enum):
    HOSTS = "hosts"
    ADDRESSES = "addresses"
    SERVICES = "services"
    WEB = "web"
    ENDPOINTS = "endpoints"
    VULNERABILITIES = "vulnerabilities"


class ScanEventKind(Enum):
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    SCAN_CANCELLED = "scan_cancelled"
    STAGE_STARTED = "stage_started"
    STAGE_PROGRESS = "stage_progress"
    STAGE_COMPLETED = "stage_completed"
    COMMAND_STARTED = "command_started"
    COMMAND_FINISHED = "command_finished"
