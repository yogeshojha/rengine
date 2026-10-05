"""Tools the worker image ships, at the versions worker/Dockerfile pins."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PinKind(StrEnum):
    GO = "go"
    RELEASE = "release"
    PIP = "pip"


@dataclass(frozen=True)
class PinnedTool:
    name: str
    version: str
    repository: str
    kind: PinKind
    # go module path, Dockerfile ARG name or pip package
    pin: str
    tag: str = ""

    @property
    def release_url(self) -> str:
        return f"https://github.com/{self.repository}/releases/tag/{self.tag or self.version}"


def _go(name: str, repository: str, module: str, version: str) -> PinnedTool:
    return PinnedTool(name, version, repository, PinKind.GO, module)


TOOLCHAIN: tuple[PinnedTool, ...] = (
    _go(
        "dnsx",
        "projectdiscovery/dnsx",
        "github.com/projectdiscovery/dnsx/cmd/dnsx",
        "v1.3.1",
    ),
    _go(
        "subfinder",
        "projectdiscovery/subfinder",
        "github.com/projectdiscovery/subfinder/v2/cmd/subfinder",
        "v2.16.0",
    ),
    _go(
        "tlsx",
        "projectdiscovery/tlsx",
        "github.com/projectdiscovery/tlsx/cmd/tlsx",
        "v1.4.0",
    ),
    _go(
        "alterx",
        "projectdiscovery/alterx",
        "github.com/projectdiscovery/alterx/cmd/alterx",
        "v0.1.0",
    ),
    _go(
        "assetfinder",
        "tomnomnom/assetfinder",
        "github.com/tomnomnom/assetfinder",
        "v0.1.1",
    ),
    _go(
        "github-subdomains",
        "gwen001/github-subdomains",
        "github.com/gwen001/github-subdomains",
        "v1.2.2",
    ),
    _go("amass", "owasp-amass/amass", "github.com/owasp-amass/amass/v4/...", "v4.2.0"),
    _go(
        "naabu",
        "projectdiscovery/naabu",
        "github.com/projectdiscovery/naabu/v2/cmd/naabu",
        "v2.6.1",
    ),
    _go(
        "httpx",
        "projectdiscovery/httpx",
        "github.com/projectdiscovery/httpx/cmd/httpx",
        "v1.12.0",
    ),
    _go(
        "cdncheck",
        "projectdiscovery/cdncheck",
        "github.com/projectdiscovery/cdncheck/cmd/cdncheck",
        "v1.3.0",
    ),
    _go("ffuf", "ffuf/ffuf", "github.com/ffuf/ffuf/v2", "v2.3.0"),
    _go(
        "katana",
        "projectdiscovery/katana",
        "github.com/projectdiscovery/katana/cmd/katana",
        "v1.7.0",
    ),
    _go(
        "urlfinder",
        "projectdiscovery/urlfinder",
        "github.com/projectdiscovery/urlfinder/cmd/urlfinder",
        "v0.0.3",
    ),
    _go(
        "nuclei",
        "projectdiscovery/nuclei",
        "github.com/projectdiscovery/nuclei/v3/cmd/nuclei",
        "v3.11.1",
    ),
    _go(
        "certspotter",
        "SSLMate/certspotter",
        "software.sslmate.com/src/certspotter/cmd/certspotter",
        "v0.24.2",
    ),
    PinnedTool("dalfox", "v3.2.2", "hahwul/dalfox", PinKind.RELEASE, "DALFOX_VERSION"),
    PinnedTool(
        "julius", "v1.4.19", "praetorian-inc/julius", PinKind.RELEASE, "JULIUS_VERSION"
    ),
    PinnedTool(
        "wafw00f",
        "2.4.2",
        "EnableSecurity/wafw00f",
        PinKind.PIP,
        "wafw00f",
        tag="v2.4.2",
    ),
)
