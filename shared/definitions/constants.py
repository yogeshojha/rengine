import re

from shared.config import APP_VERSION
from shared.definitions.about import DOCUMENTATION_URL

MAX_TARGET_BULK = 1000
MAX_TARGETS_IMPORT = 500
MAX_SCAN_BATCH = 500
MAX_LABELS = 50

MAX_COMMAND_OUTPUT = 200_000

SCANS_QUEUE = "scans"
SCAN_CONTROL_QUEUE = "scan_control"
SCAN_QUEUES = (SCANS_QUEUE, SCAN_CONTROL_QUEUE)
CRITICAL_QUEUE = "critical"
DEFAULT_QUEUE = "default"

MAX_RATE = 10000
MAX_THREADS = 1000
MAX_TIMEOUT = 3600

# bytes of a response body httpx keeps
HTTPX_RESPONSE_CAP = 131072

_RELEASE = re.match(r"\d+\.\d+", APP_VERSION)
SCAN_USER_AGENT = (
    f"reNgine/{_RELEASE.group(0) if _RELEASE else '3.0'} (+{DOCUMENTATION_URL})"
)

# entries each memoised pure helper keeps per process
PURE_CACHE = 1 << 16
