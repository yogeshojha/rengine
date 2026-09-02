from __future__ import annotations

from stages.subdomain.providers.amass import AmassProvider
from stages.subdomain.providers.assetfinder import AssetfinderProvider
from stages.subdomain.providers.base import (
    ProviderContext,
    ProviderResult,
    SubdomainProvider,
)
from stages.subdomain.providers.ctfr import CtfrProvider
from stages.subdomain.providers.netlas import NetlasProvider
from stages.subdomain.providers.oneforall import OneForAllProvider
from stages.subdomain.providers.subfinder import SubfinderProvider
from stages.subdomain.providers.sublist3r import Sublist3rProvider
from stages.subdomain.providers.sudomy import SudomyProvider
from stages.subdomain.providers.tlsx import TlsxProvider

PASSIVE_PROVIDERS: dict[str, type[SubdomainProvider]] = {
    SubfinderProvider.tool: SubfinderProvider,
    CtfrProvider.tool: CtfrProvider,
    Sublist3rProvider.tool: Sublist3rProvider,
    AssetfinderProvider.tool: AssetfinderProvider,
    AmassProvider.tool: AmassProvider,
    TlsxProvider.tool: TlsxProvider,
    OneForAllProvider.tool: OneForAllProvider,
    NetlasProvider.tool: NetlasProvider,
    SudomyProvider.tool: SudomyProvider,
    # alias: legacy/UI name for the crt.sh (CTFR) source
    "crtsh": CtfrProvider,
}

__all__ = [
    "PASSIVE_PROVIDERS",
    "ProviderContext",
    "ProviderResult",
    "SubdomainProvider",
]
