from __future__ import annotations

from stages.url_discovery.providers.archive import ArchiveProvider
from stages.url_discovery.providers.base import (
    Host,
    ProviderContext,
    ProviderResult,
    UrlProvider,
)
from stages.url_discovery.providers.katana import KatanaProvider
from stages.url_discovery.providers.known_files import KnownFilesProvider
from stages.url_discovery.providers.response_mining import ResponseMiningProvider
from stages.url_discovery.providers.source_maps import SourceMapProvider

URL_PROVIDERS: dict[str, type[UrlProvider]] = {
    ResponseMiningProvider.source: ResponseMiningProvider,
    KnownFilesProvider.source: KnownFilesProvider,
    KatanaProvider.source: KatanaProvider,
    ArchiveProvider.source: ArchiveProvider,
    SourceMapProvider.source: SourceMapProvider,
}

PROVIDER_NAMES: tuple[str, ...] = tuple(URL_PROVIDERS)

__all__ = [
    "PROVIDER_NAMES",
    "URL_PROVIDERS",
    "Host",
    "ProviderContext",
    "ProviderResult",
    "UrlProvider",
]
