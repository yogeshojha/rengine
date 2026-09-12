from __future__ import annotations

from pydantic import Field, field_validator

from shared.definitions.endpoints import (
    CRAWL_SCOPES,
    MAX_NOISE_KEEP_PER_FAMILY,
    MAX_NOISE_SIBLING_CAP,
    NOISE_IGNORED_PARAMS,
    NOISE_KEEP_PER_FAMILY,
    NOISE_SIBLING_CAP,
    NOISE_STATIC_EXTENSIONS,
    CrawlScope,
    EndpointSource,
)
from stages.config import StageConfig, rate, threads, timeout

DEFAULT_PROVIDERS: list[str] = [
    EndpointSource.RESPONSE_MINING.value,
    EndpointSource.SITEMAP.value,
    EndpointSource.CRAWL.value,
    EndpointSource.ARCHIVE.value,
    EndpointSource.JS.value,
]

_PROVIDER_LABELS = {
    EndpointSource.RESPONSE_MINING.value: "Response mining",
    EndpointSource.SITEMAP.value: "robots.txt and sitemaps",
    EndpointSource.CRAWL.value: "Crawl",
    EndpointSource.ARCHIVE.value: "Public archives",
    EndpointSource.JS.value: "Source maps",
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
        description="Sources URLs are collected from. Response mining reads stored response bodies and sends no request.",
        json_schema_extra={"options": list(_PROVIDER_LABELS)},
    )
    threads: int = threads(50, title="Threads")
    timeout: int = timeout(15, title="Timeout (s)")
    rate: int = rate(150, tool="katana", title="Requests/s")
    crawl_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        title="Crawl depth",
        description="Link depth followed from each site root.",
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
        description="Render each page in a browser before reading links. Slower.",
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
    max_source_maps: int = Field(
        default=200,
        ge=1,
        le=5_000,
        title="Bundles to ask for a map",
        description="JavaScript bundles asked for the .map beside them.",
    )
    max_archive_domains: int = Field(
        default=10,
        ge=1,
        le=200,
        title="Domains to query archives for",
        description="Registrable domains queried in public archives.",
    )
    max_hosts: int = Field(
        default=500,
        ge=1,
        le=10000,
        title="Hosts to crawl",
        description="Cap the live web assets handed to the crawler.",
    )

    drop_noise: bool = Field(
        default=True,
        title="Drop noise",
        description="Static files, crawler artifacts, platform noise and URLs past the family and sibling caps are not stored. Every drop is counted.",
    )
    static_extensions: list[str] = Field(
        default_factory=lambda: list(NOISE_STATIC_EXTENSIONS),
        max_length=200,
        title="Static extensions",
        description="File extensions dropped as static.",
    )
    ignored_params: list[str] = Field(
        default_factory=lambda: list(NOISE_IGNORED_PARAMS),
        max_length=400,
        title="Ignored parameters",
        description="Query parameters removed from every URL. Tracking and cache-busting names by default.",
    )
    keep_per_family: int = Field(
        default=NOISE_KEEP_PER_FAMILY,
        ge=1,
        le=MAX_NOISE_KEEP_PER_FAMILY,
        title="URLs kept per family",
        description="URLs stored for one path shape and parameter set. The rest are dropped.",
    )
    sibling_cap: int = Field(
        default=NOISE_SIBLING_CAP,
        ge=1,
        le=MAX_NOISE_SIBLING_CAP,
        title="Sibling cap",
        description="Children of one folder, of one kind, stored before the rest are dropped.",
    )

    @field_validator("providers")
    @classmethod
    def _known_providers(cls, value: list[str]) -> list[str]:
        return [v for v in dict.fromkeys(value) if v in _PROVIDER_LABELS]

    @field_validator("static_extensions", "ignored_params")
    @classmethod
    def _clean_names(cls, value: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                v.strip().lower().lstrip(".") for v in value if v and v.strip()
            )
        )

    @field_validator("crawl_scope")
    @classmethod
    def _known_scope(cls, value: str) -> str:
        return value if value in CRAWL_SCOPES else CrawlScope.RDN.value
