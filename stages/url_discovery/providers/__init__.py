from __future__ import annotations

from stages.url_discovery.providers.api_spec import ApiSpecProvider
from stages.url_discovery.providers.archive import ArchiveProvider
from stages.url_discovery.providers.base import Host, ProviderContext, UrlProvider
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
    ApiSpecProvider.source: ApiSpecProvider,
}

__all__ = [
    "URL_PROVIDERS",
    "Host",
    "ProviderContext",
]
