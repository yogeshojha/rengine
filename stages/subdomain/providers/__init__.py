from __future__ import annotations

from stages.subdomain.providers.amass import AmassProvider
from stages.subdomain.providers.assetfinder import AssetfinderProvider
from stages.subdomain.providers.base import (
    ProviderContext,
    ProviderResult,
    SubdomainProvider,
)
from stages.subdomain.providers.crtname import CrtNameProvider
from stages.subdomain.providers.ctfr import CtfrProvider
from stages.subdomain.providers.github import GithubProvider
from stages.subdomain.providers.netlas import NetlasProvider
from stages.subdomain.providers.subfinder import SubfinderProvider
from stages.subdomain.providers.tlsx import TlsxProvider

PASSIVE_PROVIDERS: dict[str, type[SubdomainProvider]] = {
    SubfinderProvider.tool: SubfinderProvider,
    CtfrProvider.tool: CtfrProvider,
    CrtNameProvider.tool: CrtNameProvider,
    GithubProvider.tool: GithubProvider,
    AssetfinderProvider.tool: AssetfinderProvider,
    AmassProvider.tool: AmassProvider,
    TlsxProvider.tool: TlsxProvider,
    NetlasProvider.tool: NetlasProvider,
    "crtsh": CtfrProvider,  # saved engines name the crt.sh source this way
}

__all__ = [
    "PASSIVE_PROVIDERS",
    "ProviderContext",
    "ProviderResult",
    "SubdomainProvider",
]
