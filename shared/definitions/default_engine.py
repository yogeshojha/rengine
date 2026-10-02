"""The built-in engine every project starts with."""

from __future__ import annotations

from shared.enums.scan import Intensity

DEFAULT_ENGINE_NAME = "Default"
DEFAULT_ENGINE_DESCRIPTION = (
    "Subdomain discovery on subfinder and crt.name, HTTP probe, screenshots, "
    "response mining and a nuclei vulnerability scan at Normal intensity."
)
DEFAULT_ENGINE_INTENSITY = Intensity.NORMAL.value
VULNERABILITY_STAGE = "vulnerability_scan"
DEFAULT_VULN_SCANNERS: tuple[str, ...] = ("nuclei",)


def default_engine_stages() -> dict[str, dict]:
    """Only the settings that differ from the stage defaults."""
    return {
        VULNERABILITY_STAGE: {"enabled": True, "scanners": list(DEFAULT_VULN_SCANNERS)},
    }


__all__ = [
    "DEFAULT_ENGINE_DESCRIPTION",
    "DEFAULT_ENGINE_INTENSITY",
    "DEFAULT_ENGINE_NAME",
    "DEFAULT_VULN_SCANNERS",
    "VULNERABILITY_STAGE",
    "default_engine_stages",
]
