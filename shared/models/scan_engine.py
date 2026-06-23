import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from shared.utils.datetime import utc_now


class DiscoveryConfig(BaseModel):
    related_domains_enabled: bool = False
    related_by_whois_registrant: bool = True
    related_by_nameservers: bool = True
    related_by_cert_san: bool = True
    related_by_ip_neighbors: bool = False
    related_by_ga_id: bool = False
    related_by_favicon_hash: bool = False
    related_by_asn: bool = False
    related_tld_variations: bool = False
    related_tlds: list[str] = Field(
        default_factory=lambda: [".net", ".org", ".io", ".co", ".dev"]
    )
    related_confidence_threshold: float = 0.7
    related_require_confirmation: bool = True
    related_action: str = "scan"
    org_whois_search: bool = True
    org_cert_transparency: bool = True
    org_asn_lookup: bool = True
    org_custom_patterns: list[str] = Field(default_factory=list)
    org_name_variations: list[str] = Field(default_factory=list)
    asn_scan_mode: str = "smart"
    cidr_skip_rfc1918: bool = True
    cidr_skip_cdn_ranges: bool = True
    ip_reverse_dns: bool = True
    ip_vhost_discovery: bool = False
    dns_timeout: int = 5
    dns_threads: int = 30
    whois_timeout: int = 10


class ExpansionConfig(BaseModel):
    subdomain_passive: bool = True
    subdomain_passive_tools: list[str] = Field(
        default_factory=lambda: [
            "subfinder",
            "ctfr",
            "assetfinder",
            "amass",
        ]
    )
    subdomain_securitytrails: bool = True
    subdomain_censys: bool = True
    subdomain_virustotal: bool = True
    subdomain_chaos: bool = True
    subdomain_binaryedge: bool = True
    subdomain_active: bool = False
    subdomain_wordlist: str = "deepmagic.com-prefixes-top50000"
    amass_config: bool = False
    subfinder_config: bool = False
    subdomain_tls_discovery: bool = True
    subdomain_scraping: bool = True
    subdomain_permutation: bool = False
    subdomain_permutation_tools: list[str] = Field(
        default_factory=lambda: ["gotator", "ripgen"]
    )
    subdomain_ai_permutation: bool = False
    subdomain_noerror: bool = False
    subdomain_recursive: bool = False
    dns_zone_transfer: bool = True
    subdomain_takeover: bool = True
    reverse_ip_lookup: bool = False
    cloud_bucket_enum: bool = False
    port_scan_enabled: bool = True
    port_scan_ports: str = "top-100"
    port_scan_rate_limit: int = 150
    port_scan_timeout: int = 5
    port_scan_threads: int = 30
    port_scan_passive_shodan: bool = False
    nmap_enabled: bool = False
    nmap_cmd: str | None = None
    nmap_script: str | None = None
    nmap_script_args: str | None = None
    http_crawl: bool = True
    cdn_detection: bool = True
    waf_detection: bool = True
    ip_geolocation: bool = True
    tech_detection: bool = True
    cms_detection: bool = False
    vhost_bruteforce: bool = False
    screenshot: bool = True
    screenshot_timeout: int = 10
    screenshot_threads: int = 40


class DepthConfig(BaseModel):
    dir_fuzz_enabled: bool = True
    dir_fuzz_wordlist: str = "dicc"
    dir_fuzz_extensions: list[str] = Field(
        default_factory=lambda: [
            "html",
            "php",
            "git",
            "yaml",
            "conf",
            "env",
            "log",
            "db",
            "sql",
            "json",
        ]
    )
    dir_fuzz_recursive_depth: int = 2
    dir_fuzz_rate_limit: int = 150
    dir_fuzz_threads: int = 30
    dir_fuzz_auto_calibration: bool = True
    dir_fuzz_match_status: list[int] = Field(default_factory=lambda: [200, 204])
    dir_fuzz_timeout: int = 5
    url_discovery_enabled: bool = True
    url_discovery_tools: list[str] = Field(
        default_factory=lambda: [
            "gospider",
            "hakrawler",
            "waybackurls",
            "katana",
            "gau",
        ]
    )
    url_gf_patterns: list[str] = Field(
        default_factory=lambda: [
            "idor",
            "sqli",
            "ssrf",
            "xss",
            "lfi",
            "rce",
            "redirect",
            "ssti",
            "debug_logic",
        ]
    )
    url_dedup: bool = True
    url_dedup_fields: list[str] = Field(
        default_factory=lambda: ["content_length", "page_title"]
    )
    url_ignore_extensions: list[str] = Field(
        default_factory=lambda: ["png", "jpg", "jpeg", "gif", "mp4", "mpeg", "mp3"]
    )
    url_threads: int = 30
    js_secret_scan: bool = True
    js_secret_tools: list[str] = Field(
        default_factory=lambda: ["secretfinder", "mantra"]
    )
    param_discovery: bool = False
    param_discovery_tools: list[str] = Field(default_factory=lambda: ["x8", "arjun"])
    nuclei_enabled: bool = True
    nuclei_severities: list[str] = Field(
        default_factory=lambda: ["low", "medium", "high", "critical"]
    )
    nuclei_tags: list[str] = Field(default_factory=list)
    nuclei_templates: list[str] = Field(default_factory=list)
    nuclei_custom_templates: list[str] = Field(default_factory=list)
    nuclei_use_config: bool = False
    nuclei_concurrency: int = 50
    nuclei_rate_limit: int = 150
    nuclei_retries: int = 1
    nuclei_timeout: int = 5
    dalfox_enabled: bool = False
    crlfuzz_enabled: bool = False
    sqlmap_enabled: bool = False
    ssrf_enabled: bool = False
    cors_check: bool = True
    ssl_tls_analysis: bool = True
    bypass_403: bool = False
    http_smuggling: bool = False
    prototype_pollution: bool = False
    graphql_detection: bool = False
    report_enabled: bool = False
    report_formats: list[str] = Field(default_factory=lambda: ["html"])
    report_ai_summary: bool = False
    report_notify_slack: bool = False
    report_notify_discord: bool = False
    report_notify_telegram: bool = False
    report_webhook_url: str | None = None
    report_send_on: str = "completion"


class ScanEngine(SQLModel, table=True):
    __tablename__ = "scan_engines"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    intensity: str = Field(default="normal")
    global_threads: int = Field(default=30)
    global_http_crawl: bool = Field(default=True)
    global_headers: list = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    discovery: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    expansion: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    depth: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    tool_options: dict = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime | None = Field(default=None)


class ScanEngineCreate(BaseModel):
    name: str
    description: str | None = None
    intensity: str = "normal"
    global_threads: int = 30
    global_http_crawl: bool = True
    global_headers: list[str] = Field(default_factory=list)
    discovery: DiscoveryConfig | None = None
    expansion: ExpansionConfig | None = None
    depth: DepthConfig | None = None
    tool_options: dict[str, str] = Field(default_factory=dict)


class ScanEngineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    intensity: str | None = None
    global_threads: int | None = None
    global_http_crawl: bool | None = None
    global_headers: list[str] | None = None
    discovery: DiscoveryConfig | None = None
    expansion: ExpansionConfig | None = None
    depth: DepthConfig | None = None
    tool_options: dict[str, str] | None = None


class ScanEngineRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: str | None
    intensity: str
    global_threads: int
    global_http_crawl: bool
    global_headers: list[str]
    discovery: DiscoveryConfig
    expansion: ExpansionConfig
    depth: DepthConfig
    tool_options: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
