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
from stages.config import StageConfig, advanced

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
    crawl_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        title="Crawl depth",
        description="Link depth followed from each site root.",
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
    crawl_scope: str = advanced(
        CrawlScope.RDN.value,
        title="Crawl scope",
        description="Which hosts the crawler may follow links to.",
        json_schema_extra={"options": list(CRAWL_SCOPES)},
    )
    max_hosts: int = advanced(
        500,
        ge=1,
        le=10000,
        title="Hosts to crawl",
        description="Cap the live web assets handed to the crawler.",
    )
    drop_noise: bool = advanced(
        True,
        title="Drop noise",
        description="Static files, crawler artifacts, platform noise and URLs past the family and sibling caps are not stored. Every drop is counted.",
    )
    static_extensions: list[str] = advanced(
        None,
        default_factory=lambda: list(NOISE_STATIC_EXTENSIONS),
        max_length=200,
        title="Static extensions",
        description="File extensions dropped as static.",
    )
    ignored_params: list[str] = advanced(
        None,
        default_factory=lambda: list(NOISE_IGNORED_PARAMS),
        max_length=400,
        title="Ignored parameters",
        description="Query parameters removed from every URL. Tracking and cache-busting names by default.",
    )
    keep_per_family: int = advanced(
        NOISE_KEEP_PER_FAMILY,
        ge=1,
        le=MAX_NOISE_KEEP_PER_FAMILY,
        title="URLs kept per family",
        description="URLs stored for one path shape and parameter set. The rest are dropped.",
    )
    sibling_cap: int = advanced(
        NOISE_SIBLING_CAP,
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


MAX_URLS = 50_000
MAX_KNOWN_FILE_HOSTS = 200
MAX_SOURCE_MAPS = 200
MAX_ARCHIVE_DOMAINS = 10
