from shared.definitions.bounty_programs import API_PLATFORMS
from shared.enums.instance import InstanceMode

CAP_BOUNTY_PLATFORMS = "bounty_platforms"
CAP_BOUNTY_PROGRAMS = "bounty_programs"
CAP_PROGRAM_WATCHES = "program_watches"

_MODE_CAPABILITIES: dict[str, set[str]] = {
    InstanceMode.BUG_BOUNTY.value: {
        CAP_BOUNTY_PLATFORMS,
        CAP_BOUNTY_PROGRAMS,
        CAP_PROGRAM_WATCHES,
    },
    InstanceMode.CORPORATE.value: set(),
}

BUG_BOUNTY_PROVIDERS: frozenset[str] = frozenset(p.api_provider for p in API_PLATFORMS)

VALID_MODES: frozenset[str] = frozenset(
    {InstanceMode.BUG_BOUNTY.value, InstanceMode.CORPORATE.value}
)


def capabilities_for(mode: str | None) -> list[str]:
    if mode not in _MODE_CAPABILITIES:
        return sorted(_MODE_CAPABILITIES[InstanceMode.BUG_BOUNTY.value])
    return sorted(_MODE_CAPABILITIES[mode])


def has_capability(mode: str | None, capability: str) -> bool:
    return capability in capabilities_for(mode)


def provider_allowed(mode: str | None, provider: str) -> bool:
    if provider in BUG_BOUNTY_PROVIDERS:
        return has_capability(mode, CAP_BOUNTY_PLATFORMS)
    return True
