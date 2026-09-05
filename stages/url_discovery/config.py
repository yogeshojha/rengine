from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.endpoints import CRAWL_SCOPES, CrawlScope, EndpointSource
from stages.config import StageConfig, rate, threads, timeout

DEFAULT_PROVIDERS: list[str] = [
    EndpointSource.RESPONSE_MINING.value,
    EndpointSource.SITEMAP.value,
    EndpointSource.CRAWL.value,
    EndpointSource.ARCHIVE.value,
]

_PROVIDER_LABELS = {
    EndpointSource.RESPONSE_MINING.value: "Response mining",
    EndpointSource.SITEMAP.value: "robots.txt and sitemaps",
    EndpointSource.CRAWL.value: "Crawl",
    EndpointSource.ARCHIVE.value: "Public archives",
}


class UrlDiscoveryConfig(StageConfig):
    enabled: bool = Field(
        default=True,
        title="Discover URLs",
        description="Collect the URLs and paths that exist on every live web asset.",
    )
    providers: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PROVIDERS),
        title="Sources",
        description="Where URLs are collected from. Response mining reads bodies this scan already stored and sends no request.",
        json_schema_extra={"options": list(_PROVIDER_LABELS)},
    )
    threads: int = threads(10, title="Threads")
    timeout: int = timeout(15, title="Timeout (s)")
    rate: int = rate(150, tool="katana", title="Requests/s")
    crawl_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        title="Crawl depth",
        description="How many links deep to follow from each site root.",
    )
    crawl_scope: str = Field(
        default=CrawlScope.RDN.value,
        title="Crawl scope",
        description="Which hosts the crawler may follow links to.",
        json_schema_extra={"options": list(CRAWL_SCOPES)},
    )
    crawl_javascript: bool = Field(
        default=True,
        title="Parse JavaScript",
        description="Read URLs out of the JavaScript each page loads.",
    )
    headless: bool = Field(
        default=False,
        title="Use a browser",
        description="Render each page in a browser before reading links. Much slower.",
    )
    max_crawl_minutes: int = Field(
        default=20,
        ge=0,
        le=600,
        title="Crawl budget (min)",
        description="Stop crawling after this long. 0 means no limit.",
    )
    max_urls: int = Field(
        default=50000,
        ge=100,
        le=200000,
        title="URLs per source",
        description="Cap the URLs any one source may contribute.",
    )
    max_known_file_hosts: int = Field(
        default=200,
        ge=1,
        le=5000,
        title="Hosts for robots and sitemaps",
        description="Cap the hosts whose robots.txt and sitemap are fetched.",
    )
    max_archive_domains: int = Field(
        default=10,
        ge=1,
        le=200,
        title="Domains to query archives for",
        description="Cap the registrable domains sent to public archives. One request set per domain.",
    )
    max_hosts: int = Field(
        default=500,
        ge=1,
        le=10000,
        title="Hosts to crawl",
        description="Cap the live web assets handed to the crawler.",
    )

    @field_validator("providers")
    @classmethod
    def _known_providers(cls, value: list[str]) -> list[str]:
        return [v for v in dict.fromkeys(value) if v in _PROVIDER_LABELS]

    @field_validator("crawl_scope")
    @classmethod
    def _known_scope(cls, value: str) -> str:
        return value if value in CRAWL_SCOPES else CrawlScope.RDN.value
