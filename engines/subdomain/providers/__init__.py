from __future__ import annotations

from engines.subdomain.providers.amass import AmassProvider
from engines.subdomain.providers.assetfinder import AssetfinderProvider
from engines.subdomain.providers.base import (
    ProviderContext,
    ProviderResult,
    SubdomainProvider,
)
from engines.subdomain.providers.ctfr import CtfrProvider
from engines.subdomain.providers.netlas import NetlasProvider
from engines.subdomain.providers.oneforall import OneForAllProvider
from engines.subdomain.providers.subfinder import SubfinderProvider
from engines.subdomain.providers.sublist3r import Sublist3rProvider
from engines.subdomain.providers.sudomy import SudomyProvider
from engines.subdomain.providers.tlsx import TlsxProvider

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
