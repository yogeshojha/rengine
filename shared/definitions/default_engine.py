"""The built-in engine every project starts with."""

from __future__ import annotations

from shared.enums.scan import Intensity

DEFAULT_ENGINE_NAME = "Default"
DEFAULT_ENGINE_DESCRIPTION = (
    "Subdomain discovery on subfinder, port scan, HTTP probe, screenshots, "
    "URL discovery and a nuclei vulnerability scan at Normal intensity. Built in."
)
DEFAULT_ENGINE_INTENSITY = Intensity.NORMAL.value
SUBDOMAIN_STAGE = "subdomain_discovery"
VULNERABILITY_STAGE = "vulnerability_scan"
DEFAULT_PASSIVE_SOURCES: tuple[str, ...] = ("subfinder",)
DEFAULT_VULN_SCANNERS: tuple[str, ...] = ("nuclei",)


def default_engine_stages() -> dict[str, dict]:
    """Only the settings that differ from the stage defaults."""
    return {
        SUBDOMAIN_STAGE: {"passive_tools": list(DEFAULT_PASSIVE_SOURCES)},
        VULNERABILITY_STAGE: {"enabled": True, "scanners": list(DEFAULT_VULN_SCANNERS)},
    }


__all__ = [
    "DEFAULT_ENGINE_DESCRIPTION",
    "DEFAULT_ENGINE_INTENSITY",
    "DEFAULT_ENGINE_NAME",
    "DEFAULT_PASSIVE_SOURCES",
    "DEFAULT_VULN_SCANNERS",
    "SUBDOMAIN_STAGE",
    "VULNERABILITY_STAGE",
    "default_engine_stages",
]
