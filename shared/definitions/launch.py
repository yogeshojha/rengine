from shared.enums.scan import AssetKind, Intensity, StageGroup
from shared.enums.target import TargetType

DEFAULT_LAUNCH_INTENSITY = Intensity.NORMAL.value
QUICK_SCAN_LABEL = "Quick scan"
MAX_LABEL_STAGES = 3

STAGE_GROUP_LABELS: dict[str, str] = {
    StageGroup.HOSTS.value: "Hosts",
    StageGroup.ADDRESSES.value: "Addresses",
    StageGroup.SERVICES.value: "Services",
    StageGroup.WEB.value: "Web",
    StageGroup.ENDPOINTS.value: "Endpoints",
    StageGroup.VULNERABILITIES.value: "Vulnerabilities",
}

ASSET_KIND_LABELS: dict[str, str] = {
    AssetKind.HOSTS.value: "hosts",
    AssetKind.ADDRESSES.value: "addresses",
    AssetKind.PORTS.value: "open ports",
    AssetKind.HTTP_ASSETS.value: "HTTP assets",
    AssetKind.ENDPOINTS.value: "endpoints",
    AssetKind.VULNERABILITIES.value: "findings",
}

# asset kinds the seed itself supplies before any stage runs
SEED_PRODUCES: dict[str, frozenset[str]] = {
    TargetType.URL.value: frozenset({AssetKind.HOSTS.value}),
}


def seed_produces(target_type: str) -> frozenset[str]:
    return SEED_PRODUCES.get(target_type, frozenset())
