from shared.enums.instance import InstanceMode

CAP_HACKERONE = "hackerone"
CAP_BOUNTY_PROGRAMS = "bounty_programs"
CAP_BB_RECON_PRESETS = "bb_recon_presets"

_MODE_CAPABILITIES: dict[str, set[str]] = {
    InstanceMode.BUG_BOUNTY.value: {
        CAP_HACKERONE,
        CAP_BOUNTY_PROGRAMS,
        CAP_BB_RECON_PRESETS,
    },
    InstanceMode.CORPORATE.value: set(),
}

BUG_BOUNTY_PROVIDERS: frozenset[str] = frozenset({"hackerone"})

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
        return has_capability(mode, CAP_HACKERONE)
    return True
