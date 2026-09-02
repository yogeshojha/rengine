from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Preset(StrEnum):
    STANDARD = "standard"
    PASSIVE = "passive"
    FULL = "full"
    BLANK = "blank"


@dataclass(frozen=True)
class PresetSpec:
    name: str
    title: str
    description: str


PRESETS: tuple[PresetSpec, ...] = (
    PresetSpec(
        Preset.STANDARD.value,
        "Standard Recon",
        "Balanced coverage — every engine at its own defaults.",
    ),
    PresetSpec(
        Preset.PASSIVE.value,
        "Passive Recon",
        "Only stages that send no traffic to the target.",
    ),
    PresetSpec(
        Preset.FULL.value,
        "Full Sweep",
        "Every stage enabled — most thorough, noisiest.",
    ),
    PresetSpec(
        Preset.BLANK.value,
        "Blank",
        "Nothing enabled — switch on what you need.",
    ),
)


def preset_stages(name: str) -> dict[str, dict]:
    from stages.registry import stages  # noqa: PLC0415

    if name == Preset.STANDARD.value:
        return {}
    return {
        spec.name: {"enabled": _enabled(name, spec)}
        for spec in stages()
        if _enabled(name, spec) != spec.defaults["enabled"]
    }


def _enabled(preset: str, spec) -> bool:
    if preset == Preset.FULL.value:
        return True
    if preset == Preset.BLANK.value:
        return False
    return not spec.touches_target
