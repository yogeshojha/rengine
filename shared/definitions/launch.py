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
    StageGroup.ANALYSIS.value: "Analysis",
}

ASSET_KIND_LABELS: dict[str, str] = {
    AssetKind.HOSTS.value: "host names",
    AssetKind.ADDRESSES.value: "addresses",
    AssetKind.PORTS.value: "open ports",
    AssetKind.HTTP_ASSETS.value: "web assets",
    AssetKind.ENDPOINTS.value: "endpoints",
    AssetKind.VULNERABILITIES.value: "findings",
    AssetKind.SECRETS.value: "secrets",
}

SEED_PRODUCES: dict[str, frozenset[str]] = {
    TargetType.URL.value: frozenset({AssetKind.HOSTS.value}),
}


def seed_produces(target_type: str) -> frozenset[str]:
    return SEED_PRODUCES.get(target_type, frozenset())


CONTEXT_NOUN = "Context"
ENGINE_NOUN = "Engine"
CREDENTIAL_LAUNCH = (
    "{noun} {name} carries credentials. "
    "Its creator or an administrator can launch with it."
)
CREDENTIAL_CHANGE = (
    "{noun} {name} carries credentials. Its creator or an administrator can change it."
)
