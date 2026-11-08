"""Seed a large synthetic estate into the dev database for query profiling."""

# ruff: noqa: S608

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import sys
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg

from shared.config import base_settings
from shared.definitions.ai_services import SERVICES as AI_SERVICES
from shared.definitions.domain_posture import (
    MAX_ZONES_PER_SCAN,
    DnssecState,
    MtaStsMode,
    PostureCheck,
    SpfAll,
)
from shared.definitions.endpoints import (
    EndpointClass,
    EndpointSource,
    classify,
    family_shape,
    interests_for,
    is_ignored_param,
    param_interests,
    shape_for,
    split_path,
)
from shared.definitions.evidence import Evidence
from shared.definitions.hygiene import HygieneCheck
from shared.definitions.interest import (
    BAND_FLOOR,
    InterestBand,
    InterestKind,
)
from shared.definitions.ports import (
    PortSource,
    PortState,
    ScanPolicy,
    ScanPolicyReason,
    likely_tls,
    service_class,
    service_for_port,
)
from shared.definitions.scan_surface import (
    ClusterSignal,
    DropReason,
    SurfaceClass,
    SurfaceState,
    Tier,
)
from shared.definitions.secrets import (
    DETECTORS,
    SecretSource,
    SecretState,
)
from shared.definitions.software import (
    PRODUCTS_BY_KEY,
    Caveat,
    Confidence,
    VersionSource,
)
from shared.definitions.threat_intel import ExploitSignal
from shared.definitions.vulnerabilities import (
    OFFICIAL_ROOT,
    CoverageStatus,
    Protocol,
    Scanner,
    Severity,
)
from shared.enums.ip import IpSource
from shared.enums.scan import (
    Intensity,
    ScanActivityStatus,
    ScanScope,
    ScanStatus,
)
from shared.enums.subdomain import SubdomainSource
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.utils.software import components_of, normalize_product

CENSUS_RUNS = 3
RUN_FRACTIONS = (0.90, 0.95, 1.00)
RUN_DAYS_AGO = (60, 32, 4)
RUNNING_FRACTION = 0.5
CDN_POOL = 2048
VARIANTS = 512
CHUNK = 100_000
PRIMARY_TABLES = (
    "subdomains",
    "http_assets",
    "endpoints",
    "ports",
    "ip_addresses",
    "vulnerabilities",
)
PATH_TEMPLATES = 6000
PARAM_SETS = 40
DROP_MOD = 50
ENDPOINT_DROP_MOD = 40
STALL_GUARD_DAYS = 30
HEALTH_URL = "http://127.0.0.1:8000/api/v1/health/health"
AI_SERVICE = AI_SERVICES[0]
STYLE_CUTS = (0.55, 0.80, 0.88, 0.96)
DIRECTORY_SHARE = 0.1

# ---------- vocabulary pools ----------

PREFIXES = [
    "www",
    "mail",
    "api",
    "dev",
    "staging",
    "test",
    "vpn",
    "portal",
    "admin",
    "app",
    "beta",
    "cdn",
    "static",
    "assets",
    "auth",
    "sso",
    "login",
    "shop",
    "store",
    "blog",
    "docs",
    "support",
    "help",
    "m",
    "mobile",
    "git",
    "gitlab",
    "jenkins",
    "ci",
    "jira",
    "wiki",
    "confluence",
    "grafana",
    "kibana",
    "monitor",
    "status",
    "intranet",
    "remote",
    "owa",
    "autodiscover",
    "smtp",
    "imap",
    "ftp",
    "ns1",
    "ns2",
    "db",
    "mysql",
    "redis",
    "backup",
    "files",
    "upload",
    "media",
    "img",
    "video",
    "legacy",
    "old",
    "new",
    "demo",
    "sandbox",
    "uat",
    "qa",
    "prod",
    "internal",
    "partner",
    "b2b",
    "crm",
    "erp",
    "hr",
    "pay",
    "billing",
    "invoice",
    "careers",
    "events",
    "news",
    "search",
    "analytics",
    "metrics",
    "tracking",
    "ads",
    "lb",
    "edge",
    "proxy",
    "gateway",
    "k8s",
    "rancher",
    "vault",
    "consul",
]
ENVS = ["dev", "stg", "qa", "uat", "prod", "int", "eu", "us", "ap", "corp"]
BRANDS = [
    "globex",
    "initech",
    "umbrella",
    "hooli",
    "vandelay",
    "wayne",
    "stark",
    "wonka",
    "tyrell",
    "cyberdyne",
    "soylent",
    "oscorp",
    "aperture",
    "massive",
    "gringotts",
    "monarch",
    "piedpiper",
    "nakatomi",
    "acme",
]
TITLES_200 = [
    "",
    "Welcome to nginx!",
    "Login",
    "Just a moment...",
    "Home",
    "IIS Windows Server",
    "Apache2 Ubuntu Default Page: It works",
    "Dashboard",
    "Sign in",
    "Index of /",
    "Swagger UI",
    "Grafana",
    "Sign in [Jenkins]",
    "Kibana",
    "Sign in · GitLab",
    "Outlook",
    "Citrix Gateway",
    "GlobalProtect Portal",
    "phpMyAdmin",
    "Coming Soon",
    "Test Page for the Apache HTTP Server",
    "Microsoft Azure App Service - Welcome",
    "Jira",
    "Log In - Confluence",
    "RabbitMQ Management",
    "Keycloak",
    "Roundcube Webmail",
    "Under Construction",
    "API Documentation",
    "Default Web Site Page",
    "Site Maintenance",
]
TITLES_403 = [
    "403 Forbidden",
    "Access Denied",
    "Attention Required! | Cloudflare",
    "ERROR: The request could not be satisfied",
]
TITLES_404 = ["404 Not Found", "Not Found", "Page Not Found"]
TITLES_401 = ["401 Authorization Required", "Sign in"]
TITLES_5XX = [
    "502 Bad Gateway",
    "503 Service Temporarily Unavailable",
    "Internal Server Error",
]
TECH = [
    "HSTS",
    "Nginx",
    "jQuery",
    "Bootstrap",
    "Cloudflare",
    "Google Analytics",
    "Google Tag Manager",
    "PHP",
    "Amazon Web Services",
    "Amazon CloudFront",
    "React",
    "Font Awesome",
    "Apache HTTP Server",
    "WordPress",
    "Nginx:1.18.0",
    "Microsoft IIS:10.0",
    "Vue.js",
    "Google Font API",
    "Lodash",
    "Java",
    "Node.js",
    "Express",
    "Amazon S3",
    "jQuery:3.5.1",
    "PHP:7.4.33",
    "Microsoft ASP.NET",
    "Windows Server",
    "Ubuntu",
    "Debian",
    "Next.js",
    "Angular",
    "OpenResty",
    "Varnish",
    "Fastly",
    "Akamai",
    "Envoy",
    "Apache Tomcat:9.0.31",
    "Jetty:9.4.43",
    "Spring Boot",
    "Jenkins:2.401.1",
    "Grafana:8.3.0",
    "Kibana",
    "Elasticsearch",
    "GitLab",
    "Atlassian Confluence",
    "Atlassian Jira",
    "Swagger UI:4.15.5",
    "WordPress:5.8.1",
    "Drupal:7.58",
    "Joomla",
    "Magento",
    "Laravel",
    "Django",
    "Python",
    "Ruby on Rails",
    "Moment.js",
    "core-js",
    "Webpack",
    "Apache HTTP Server:2.4.49",
    "Node.js:16.14.0",
]
WEBSERVERS = [
    "nginx",
    "cloudflare",
    "Apache",
    "nginx/1.18.0",
    "Microsoft-IIS/10.0",
    "AmazonS3",
    "openresty",
    "Apache/2.4.49 (Unix)",
    "envoy",
    "Jetty(9.4.43.v20210629)",
    "gunicorn",
    "Kestrel",
    "LiteSpeed",
    "AkamaiGHost",
    "Varnish",
    "nginx/1.24.0",
    "Apache/2.4.41 (Ubuntu)",
    "Microsoft-IIS/8.5",
    "",
]
ISSUERS = [
    ("Let's Encrypt", "R11"),
    ("DigiCert Inc", "DigiCert Global G2 TLS RSA SHA256 2020 CA1"),
    ("Amazon", "Amazon RSA 2048 M02"),
    ("Google Trust Services", "WE1"),
    ("Sectigo Limited", "Sectigo RSA Domain Validation Secure Server CA"),
    ("GlobalSign nv-sa", "GlobalSign GCC R3 DV TLS CA 2020"),
    ("Cloudflare, Inc.", "Cloudflare Inc ECC CA-3"),
]
COUNTRIES = [
    "US",
    "DE",
    "GB",
    "NL",
    "SG",
    "IN",
    "FR",
    "JP",
    "CY",
    "NP",
    "CA",
    "AU",
    "BR",
    "IE",
    "SE",
]
ENDPOINT_TITLES = [
    "",
    "Login",
    "Home",
    "404 Not Found",
    "Dashboard",
    "Search results",
    "Product details",
    "My account",
    "Checkout",
    "Blog",
    "Documentation",
    "API Reference",
    "Forbidden",
    "Contact us",
    "Settings",
]
VULN_PATHS = [
    "",
    "/",
    "/login",
    "/admin/",
    "/.env",
    "/api/v1/users",
    "/wp-login.php",
    "/server-status",
    "/.git/config",
    "/actuator/env",
]
ASNS = [
    (16509, "AMAZON-02"),
    (14618, "AMAZON-AES"),
    (15169, "GOOGLE"),
    (8075, "MICROSOFT-CORP-MSN-AS-BLOCK"),
    (24940, "Hetzner Online GmbH"),
    (16276, "OVH SAS"),
    (14061, "DIGITALOCEAN-ASN"),
    (63949, "Akamai Connected Cloud"),
]
CLOUDFLARE_ASN = 13335
DOC_ASN = 64496
PRIVATE_ASN_BASE = 4_200_000_000
PORT_PROBS = {
    443: 0.85,
    80: 0.70,
    22: 0.30,
    8080: 0.10,
    8443: 0.08,
    21: 0.04,
    25: 0.05,
    53: 0.03,
    110: 0.02,
    143: 0.02,
    993: 0.02,
    995: 0.01,
    3306: 0.03,
    5432: 0.02,
    6379: 0.015,
    27017: 0.01,
    9200: 0.01,
    3389: 0.03,
    5900: 0.01,
    9090: 0.02,
    2083: 0.01,
    11434: 0.005,
    8000: 0.03,
    3000: 0.02,
}
HTTP_PORTS = frozenset({80, 443, 8080, 8443, 8000, 3000, 9090, 2083, 11434, 9200})
BANNERS = {
    22: ("OpenSSH", "8.9p1", "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"),
    21: ("vsftpd", "3.0.3", "220 (vsFTPd 3.0.3)"),
    25: ("Postfix", None, "220 mail ESMTP Postfix"),
    3306: ("MySQL", "8.0.36", None),
    6379: ("Redis", "7.2.4", None),
    80: ("nginx", "1.24.0", None),
    443: ("nginx", "1.24.0", None),
}
PARAMS = [
    "id",
    "page",
    "q",
    "search",
    "redirect",
    "url",
    "next",
    "file",
    "lang",
    "sort",
    "token",
    "callback",
    "ref",
    "user",
    "debug",
    "cmd",
    "path",
    "category",
    "limit",
    "offset",
    "utm_source",
]
DIRS_1 = [
    "api",
    "static",
    "assets",
    "admin",
    "blog",
    "docs",
    "user",
    "account",
    "shop",
    "products",
    "search",
    "wp-content",
    "wp-json",
    "images",
    "js",
    "css",
    "downloads",
    "support",
    "help",
    "news",
    "media",
    "uploads",
    "v1",
    "v2",
    "graphql",
    "auth",
    "dashboard",
    "cart",
    "checkout",
    ".well-known",
    "cgi-bin",
    "backup",
    "config",
    "internal",
    "dev",
    "test",
    "old",
    "legacy",
    "portal",
]
DIRS_2 = [
    "v1",
    "v2",
    "v3",
    "public",
    "private",
    "files",
    "data",
    "reports",
    "orders",
    "items",
    "users",
    "posts",
    "pages",
    "themes",
    "plugins",
    "vendor",
    "lib",
    "dist",
    "build",
    "modules",
    "components",
    "admin",
    "settings",
    "export",
    "import",
]
LEAVES = [
    "index",
    "main",
    "app",
    "vendor",
    "config",
    "login",
    "logout",
    "register",
    "settings",
    "profile",
    "list",
    "view",
    "edit",
    "delete",
    "export",
    "import",
    "report",
    "status",
    "health",
    "metrics",
    "debug",
    "info",
    "robots",
    "sitemap",
    "feed",
    "rss",
    "manifest",
    "service-worker",
    "bundle",
    "style",
    "theme",
    "logo",
    "favicon",
    "readme",
    "changelog",
    ".env",
    "backup",
    "dump",
    "users",
    "orders",
    "items",
]
EXTENSIONS = [
    None,
    None,
    None,
    "php",
    "js",
    "css",
    "html",
    "json",
    "aspx",
    "jsp",
    "png",
    "svg",
    "pdf",
    "xml",
    "txt",
    "map",
    "do",
    "bak",
]
NOUNS = [
    "users",
    "orders",
    "products",
    "posts",
    "invoices",
    "accounts",
    "items",
    "tickets",
    "files",
    "articles",
]
ACTIONS = ["", "", "edit", "view", "delete", "download"]
LANGS = ["en", "de", "fr", "es", "ja", "pt"]
CONTENT_TYPES = {
    "js": "application/javascript",
    "css": "text/css",
    "json": "application/json",
    "png": "image/png",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
    "xml": "application/xml",
    "txt": "text/plain",
    "map": "application/json",
}
SECRET_PREFIXES = {
    "aws_access_key": "AKIA",
    "github_token": "ghp_",
    "github_fine_grained_token": "github_pat_",
    "gitlab_token": "glpat-",
    "npm_token": "npm_",
    "stripe_secret_key": "sk_live_",
    "stripe_publishable_key": "pk_live_",
    "google_api_key": "AIza",
    "slack_token": "xoxb-",
    "huggingface_token": "hf_",
}
RESULT_TABLES = (
    "subdomains",
    "http_assets",
    "endpoints",
    "endpoint_responses",
    "ports",
    "ip_addresses",
    "vulnerabilities",
    "scan_surface_items",
    "secrets",
    "software_cves",
    "domain_posture",
    "scan_activities",
    "scan_revisions",
)
SCANNED_STAGES = (
    "seed_resolution",
    "target_enrichment",
    "subdomain_discovery",
    "cdn_check",
    "passive_ports",
    "port_scan",
    "http_probe",
    "screenshot",
    "dns_posture",
    "takeover",
    "url_discovery",
    "endpoint_probe",
    "vulnerability_scan",
    "secret_mining",
    "ip_enrichment",
    "waf_detect",
)
NETWORK_STAGES = (
    "seed_resolution",
    "netblock_sweep",
    "host_discovery",
    "port_scan",
    "http_probe",
    "url_discovery",
    "endpoint_probe",
    "vulnerability_scan",
    "secret_mining",
    "ip_enrichment",
)
URL_STAGES = (
    "asset_seed",
    "seed_resolution",
    "http_probe",
    "url_discovery",
    "endpoint_probe",
    "vulnerability_scan",
    "secret_mining",
    "ip_enrichment",
)
RUNNING_DONE = ("seed_resolution", "target_enrichment", "subdomain_discovery")
RUNNING_NOW = "http_probe"
RUNNING_QUEUED = "vulnerability_scan"


def lit(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def text_array(values) -> str:
    return "ARRAY[" + ",".join(lit(v) for v in values) + "]::text[]"


def weighted(pairs: list[tuple[str, int]]) -> list[str]:
    return [value for value, weight in pairs for _ in range(weight)]


# ---------- plan ----------


@dataclass
class TargetPlan:
    number: int
    value: str
    kind: str
    apex: str
    brand: str
    names: int = 0
    zones: int = 0
    pool: int = 0
    endpoints: int = 0
    findings: int = 0
    secrets: int = 0
    software: int = 0
    addresses: int = 0
    octet: int = 0
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    config: dict = field(default_factory=dict)

    @property
    def seed(self) -> str:
        return f"st{self.number:02d}"

    @property
    def network(self) -> bool:
        return self.kind == TargetType.IP_RANGE.value

    @property
    def web_names(self) -> int:
        return (self.names // 20) * 11 + min(self.names % 20, 11)


@dataclass
class ScanPlan:
    target: TargetPlan
    run: int
    fraction: float
    started: datetime
    completed: datetime | None
    status: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def census(self) -> bool:
        return self.status == ScanStatus.COMPLETED.value


def scaled(value: float, scale: float, floor: int = 1) -> int:
    return max(floor, round(value * scale))


def build_targets(scale: float) -> list[TargetPlan]:
    domain_sizes = [
        20000,
        9000,
        6000,
        5000,
        4000,
        3500,
        3000,
        2800,
        2500,
        2200,
        2000,
        1800,
        1500,
        1200,
        1000,
        800,
        600,
        400,
        250,
    ]
    plans: list[TargetPlan] = []
    registry = TargetPlan(
        number=1,
        value="gov.cy",
        kind=TargetType.DOMAIN.value,
        apex="gov.cy",
        brand="government",
        names=scaled(150000, scale, 40),
        zones=scaled(3000, scale, 4),
        pool=scaled(14000, scale, 8),
        endpoints=scaled(400000, scale),
        findings=scaled(20000, scale),
        secrets=scaled(5000, scale),
        software=scaled(3600, scale),
    )
    plans.append(registry)
    for offset, size in enumerate(domain_sizes):
        brand = BRANDS[offset]
        apex = f"{brand}-stress.example"
        names = scaled(size, scale, 6)
        weight = 7.0 if offset == 0 else 5.3
        plans.append(
            TargetPlan(
                number=len(plans) + 1,
                value=apex,
                kind=TargetType.DOMAIN.value,
                apex=apex,
                brand=brand,
                names=names,
                pool=max(4, names // (7 if offset == 0 else 6)),
                endpoints=max(1, round(names * weight)),
                findings=max(1, round(names * 0.28)),
                secrets=max(1, round(names * 0.07)),
                software=max(1, round(names * 0.05)),
            )
        )
    for offset, (size, eps) in enumerate(((2048, 4000), (2048, 4000), (2048, 4000))):
        octet = 200 + offset
        plans.append(
            TargetPlan(
                number=len(plans) + 1,
                value=f"23.{octet}.0.0/21",
                kind=TargetType.IP_RANGE.value,
                apex="",
                brand=f"range{offset + 1}",
                addresses=scaled(size, scale, 8),
                endpoints=scaled(eps, scale),
                findings=scaled(800, scale),
                secrets=scaled(100, scale),
                software=scaled(100, scale),
                octet=octet,
            )
        )
    for offset, (host, eps, finds) in enumerate(
        (
            ("portal.hooli-stress.example", 60000, 1500),
            ("app.wonka-stress.example", 25000, 1000),
        )
    ):
        plans.append(
            TargetPlan(
                number=len(plans) + 1,
                value=f"https://{host}/app",
                kind=TargetType.URL.value,
                apex=host,
                brand=BRANDS[3 if offset == 0 else 8],
                names=1,
                pool=2,
                endpoints=scaled(eps, scale),
                findings=scaled(finds, scale),
                secrets=scaled(800 - 300 * offset, scale),
                software=scaled(300 - 100 * offset, scale),
            )
        )
    return plans


def stage_list(plan: TargetPlan) -> tuple[str, ...]:
    if plan.network:
        return NETWORK_STAGES
    if plan.kind == TargetType.URL.value:
        return URL_STAGES
    return SCANNED_STAGES


def execution_config(plan: TargetPlan) -> dict:
    from shared.services.scan_resolve import (  # noqa: PLC0415
        merge_engine_context,
        seal_run_config,
    )

    stages = {name: {"enabled": True} for name in stage_list(plan)}
    stages["vulnerability_scan"]["scanners"] = [Scanner.NUCLEI.value]
    engine = SimpleNamespace(
        intensity=Intensity.NORMAL.value,
        stages=stages,
        transport_overrides={},
        global_headers=[],
    )
    resolved = merge_engine_context(engine, None, plan.value, plan.kind)
    config = seal_run_config(resolved.model_dump(mode="json"))
    config["_auth_header_names"] = []
    config["_auth"] = {"auth_type": "none"}
    return config


def build_scans(targets: list[TargetPlan], now: datetime) -> list[ScanPlan]:
    scans: list[ScanPlan] = []
    for run in range(CENSUS_RUNS):
        for plan in targets:
            started = now - timedelta(days=RUN_DAYS_AGO[run], hours=24 - plan.number)
            hours = 18 if plan.number == 1 else 1 + plan.number % 5
            scans.append(
                ScanPlan(
                    target=plan,
                    run=run + 1,
                    fraction=RUN_FRACTIONS[run],
                    started=started,
                    completed=started + timedelta(hours=hours, minutes=plan.number),
                    status=ScanStatus.COMPLETED.value,
                )
            )
    running_target = targets[4]
    scans.append(
        ScanPlan(
            target=running_target,
            run=CENSUS_RUNS + 1,
            fraction=RUNNING_FRACTION,
            started=now - timedelta(minutes=45),
            completed=None,
            status=ScanStatus.RUNNING.value,
        )
    )
    return scans


# ---------- path and parameter catalogs ----------


def path_templates() -> list[tuple]:
    rng = random.Random(42)  # noqa: S311
    sample = {"{n}": "12345", "{u}": str(uuid.UUID(int=7)), "{h}": "ab12c345"}
    out: list[tuple] = []
    seen: set[str] = set()
    while len(out) < PATH_TEMPLATES:
        style = rng.random()
        if style < STYLE_CUTS[0]:
            parts = [rng.choice(DIRS_1)]
            for _ in range(rng.randint(0, 2)):
                parts.append(rng.choice(DIRS_2))
            if rng.random() < DIRECTORY_SHARE:
                path = "/" + "/".join(parts) + "/"
            else:
                ext = rng.choice(EXTENSIONS)
                leaf = rng.choice(LEAVES)
                if ext and not leaf.startswith("."):
                    leaf = f"{leaf}.{ext}"
                path = "/" + "/".join([*parts, leaf])
        elif style < STYLE_CUTS[1]:
            action = rng.choice(ACTIONS)
            path = f"/{rng.choice(DIRS_1)}/{rng.choice(NOUNS)}/{{n}}" + (
                f"/{action}" if action else ""
            )
        elif style < STYLE_CUTS[2]:
            path = f"/{rng.choice(DIRS_1)}/{rng.choice(NOUNS)}/{{u}}"
        elif style < STYLE_CUTS[3]:
            ext = rng.choice(["js", "css"])
            path = f"/static/{ext}/{rng.choice(LEAVES).strip('.')}-{{h}}.{ext}"
        else:
            path = f"/{rng.choice(LANGS)}/{rng.choice(DIRS_1)}/{rng.choice(LEAVES).strip('.')}"
        if path in seen:
            continue
        seen.add(path)
        concrete = path
        for marker, value in sample.items():
            concrete = concrete.replace(marker, value)
        dir_tpl, file_tpl, ext, depth = split_path(path)
        klass = classify(concrete, ext)
        shaped, _ = shape_for(concrete)
        interests = interests_for(concrete, [], endpoint_class=klass, extension=ext)
        ctype = CONTENT_TYPES.get(ext or "", "text/html; charset=utf-8")
        out.append(
            (
                len(out) + 1,
                path,
                dir_tpl,
                file_tpl,
                ext,
                depth,
                shaped,
                family_shape(concrete),
                klass,
                interests,
                ctype,
            )
        )
    return out


def param_sets() -> list[tuple]:
    rng = random.Random(7)  # noqa: S311
    out: list[tuple] = [(0, "", "", "", "[]", [], [])]
    seen: set[str] = set()
    while len(out) <= PARAM_SETS:
        names = sorted(set(rng.sample(PARAMS, rng.randint(1, 3))))
        csv = ",".join(names)
        if csv in seen:
            continue
        seen.add(csv)
        kept = ",".join(n for n in names if not is_ignored_param(n))
        query = "&".join(f"{n}={{v}}" for n in names)
        samples = json.dumps([dict.fromkeys(names, "{v}")])
        out.append((len(out), csv, kept, query, samples, param_interests(names), names))
    return out


def port_catalog() -> list[tuple]:
    out = []
    for number, prob in PORT_PROBS.items():
        is_http = number in HTTP_PORTS
        service = service_for_port(number)
        product, version, banner = BANNERS.get(number, (None, None, None))
        out.append(
            (
                number,
                service,
                service_class(service, number, is_http=is_http),
                is_http,
                likely_tls(number),
                prob,
                product,
                version,
                banner,
            )
        )
    return out


def tech_components() -> list[tuple[str, str]]:
    rows = [
        (entry, json.dumps(comp))
        for entry in TECH
        for comp in components_of([entry], None)
    ]
    rows += [
        (f"ws:{server}", json.dumps(comp))
        for server in WEBSERVERS
        for comp in components_of([], server)
    ]
    return rows


def software_products() -> list[tuple[str, str, str, str]]:
    seen: set[tuple[str, str]] = set()
    out = []
    comps = [json.loads(c) for _, c in tech_components()]
    for comp in comps:
        key = (comp["name"], comp["version"])
        if key in seen:
            continue
        seen.add(key)
        product = PRODUCTS_BY_KEY.get(normalize_product(comp["name"]))
        if product is None:
            continue
        out.append(
            (
                comp["name"],
                comp["version"],
                product.vendor or product.product,
                product.product,
            )
        )
    return out


# ---------- session helpers ----------


def picker(name: str, values, kind: str = "text") -> str:
    array = (
        text_array(values)
        if kind == "text"
        else "ARRAY[" + ",".join(str(v) for v in values) + f"]::{kind}[]"
    )
    return (
        f"CREATE FUNCTION pg_temp.{name}(float8) RETURNS {kind} STABLE LANGUAGE sql AS "
        f"$f$ SELECT ({array})[1 + floor(least($1, 0.999999) * {len(values)})::int] $f$;"
    )


def session_sql() -> str:
    hygiene = [c.value for c in HygieneCheck]
    https_only = {HygieneCheck.NO_HSTS.value, HygieneCheck.HSTS_SHORT.value}
    http_only = {HygieneCheck.NO_HTTPS_REDIRECT.value}
    scopes = [
        "https" if c in https_only else "http" if c in http_only else "any"
        for c in hygiene
    ]
    rates = [round(0.08 + (hash_of(c) % 50) / 100, 2) for c in hygiene]
    posture = [c.value for c in PostureCheck]
    posture_rates = [round(0.1 + (hash_of(c) % 60) / 100, 2) for c in posture]
    asn_case = " ".join(f"WHEN {i} THEN {asn}" for i, (asn, _org) in enumerate(ASNS))
    org_case = " ".join(f"WHEN {asn} THEN {lit(org)}" for asn, org in ASNS)
    titles_200 = TITLES_200
    sources = weighted(
        [
            (EndpointSource.CRAWL.value, 40),
            (EndpointSource.ARCHIVE.value, 25),
            (EndpointSource.JS.value, 10),
            (EndpointSource.RESPONSE_MINING.value, 9),
            (EndpointSource.FUZZ.value, 8),
            (EndpointSource.SITEMAP.value, 5),
            (EndpointSource.ROBOTS.value, 2),
            (EndpointSource.SEED.value, 1),
        ]
    )
    statuses = [200] * 50 + [404] * 15 + [403] * 10 + [301] * 10 + [302] * 3 + [500] * 3
    statuses += [401] * 4 + [400] * 5
    kinds = [k.value for k in InterestKind]
    parts = [
        "CREATE FUNCTION pg_temp.u(text) RETURNS float8 STABLE LANGUAGE sql AS "
        "$f$ SELECT (hashtext($1)::float8 + 2147483648.0) / 4294967296.0 $f$;",
        "CREATE FUNCTION pg_temp.hn(text) RETURNS int8 STABLE LANGUAGE sql AS "
        "$f$ SELECT hashtext($1)::int8 + 2147483648 $f$;",
        "CREATE FUNCTION pg_temp.sha(text) RETURNS text STABLE LANGUAGE sql AS "
        "$f$ SELECT encode(sha256(convert_to($1, 'UTF8')), 'hex') $f$;",
        picker("p_prefix", PREFIXES),
        picker("p_env", ENVS),
        picker("p_title200", titles_200),
        picker("p_title403", TITLES_403),
        picker("p_title404", TITLES_404),
        picker("p_title401", TITLES_401),
        picker("p_title5xx", TITLES_5XX),
        picker("p_tech", TECH),
        picker("p_webserver", WEBSERVERS),
        picker("p_issuer", [i for i, _ in ISSUERS]),
        picker("p_issuer_cn", [c for _, c in ISSUERS]),
        picker("p_country", COUNTRIES),
        picker("p_etitle", ENDPOINT_TITLES),
        picker("p_vpath", VULN_PATHS),
        picker("p_esource", sources),
        picker("p_estatus", statuses, "int"),
        picker("p_kind", kinds),
        picker(
            "p_jarm",
            [hashlib.sha256(f"jarm{i}".encode()).hexdigest()[:62] for i in range(10)],
        ),
        picker(
            "p_favicon", [str(-(10**9) + 7919 * i * 104729 % 2**31) for i in range(30)]
        ),
        """CREATE FUNCTION pg_temp.sub_name(i int, zones int, apex text) RETURNS text
        STABLE LANGUAGE sql AS $f$ SELECT CASE
          WHEN zones > 0 AND i / zones = 0
            THEN 'stress-agency-' || lpad((i % zones)::text, 4, '0') || '.' || apex
          WHEN zones > 0
            THEN pg_temp.p_prefix(pg_temp.u('p:' || i)) || (i / zones) || '.stress-agency-'
                 || lpad((i % zones)::text, 4, '0') || '.' || apex
          WHEN i = 1 THEN apex
          WHEN i = 2 THEN 'www.' || apex
          WHEN i % 7 = 0
            THEN pg_temp.p_prefix(pg_temp.u('p:' || i)) || i || '.'
                 || pg_temp.p_env(pg_temp.u('e:' || i)) || '.' || apex
          ELSE pg_temp.p_prefix(pg_temp.u('p:' || i)) || '-' || i || '.' || apex
        END $f$;""",
        f"""CREATE FUNCTION pg_temp.asn_of(ip text) RETURNS int8 STABLE LANGUAGE sql AS $f$
        SELECT CASE
          WHEN ip LIKE '104.18.%' THEN {CLOUDFLARE_ASN}
          WHEN strpos(ip, ':') > 0 THEN {DOC_ASN}
          WHEN split_part(ip, '.', 2)::int % 5 = 0
            THEN {PRIVATE_ASN_BASE} + split_part(ip, '.', 2)::int
          ELSE CASE split_part(ip, '.', 3)::int % {len(ASNS)} {asn_case} END
        END $f$;""",
        f"""CREATE FUNCTION pg_temp.asn_org(asn int8) RETURNS text STABLE LANGUAGE sql AS $f$
        SELECT CASE asn WHEN {CLOUDFLARE_ASN} THEN 'CLOUDFLARENET'
          WHEN {DOC_ASN} THEN 'Documentation ASN' {org_case}
          ELSE 'Stress Private Network ' || (asn - {PRIVATE_ASN_BASE}) END $f$;""",
        f"""CREATE FUNCTION pg_temp.hyg(key text, https bool, issues bool) RETURNS json
        STABLE LANGUAGE sql AS $f$
        SELECT coalesce(json_agg(c ORDER BY c), '[]'::json)
          FROM unnest({text_array(hygiene)}, ARRAY{rates}::float8[], {text_array(scopes)})
               AS x(c, r, s)
         WHERE (s = 'any' OR (s = 'https') = https)
           AND pg_temp.u(key || c) > 0.08
           AND (NOT issues OR pg_temp.u(key || c || '!') < r) $f$;""",
        f"""CREATE FUNCTION pg_temp.posture(zone text, issues bool) RETURNS json
        STABLE LANGUAGE sql AS $f$
        SELECT coalesce(json_agg(c), '[]'::json)
          FROM unnest({text_array(posture)}, ARRAY{posture_rates}::float8[]) AS x(c, r)
         WHERE pg_temp.u(zone || c) > 0.1
           AND (NOT issues OR pg_temp.u(zone || c || '!') < r) $f$;""",
        """CREATE FUNCTION pg_temp.inst(tpl text, j int, seed text) RETURNS text
        STABLE LANGUAGE sql AS $f$
        SELECT CASE WHEN strpos(tpl, '{') = 0 THEN tpl ELSE
               replace(replace(replace(tpl, '{n}', (10000 + j)::text),
               '{u}', md5(seed || j)::uuid::text),
               '{h}', substr(md5(j::text), 1, 5) || lpad((j % 1000)::text, 3, '0')) END $f$;""",
        comp_function(),
        f"""CREATE TEMP TABLE hyg_var AS
        SELECT h.https, v, pg_temp.hyg('hv' || v, h.https, true) AS issues,
               pg_temp.hyg('hv' || v, h.https, false) AS checked
          FROM generate_series(0, {VARIANTS - 1}) v, (VALUES (true), (false)) AS h(https);
        CREATE UNIQUE INDEX ON hyg_var (https, v);
        CREATE TEMP TABLE posture_var AS
        SELECT v, pg_temp.posture('pv' || v, true) AS issues,
               pg_temp.posture('pv' || v, false) AS checked
          FROM generate_series(0, {VARIANTS - 1}) v;
        CREATE UNIQUE INDEX ON posture_var (v);""",
        """CREATE TEMP TABLE sub_k (
          i int, zone text, sub_id uuid, ha_id uuid, wkey int, key text, name text,
          sources json, resolved_ips json, cname text, is_active bool, is_wildcard bool,
          is_important bool, discovered_at timestamptz, http_url text, http_status int,
          page_title text, content_type text, content_length int, response_time float8,
          webserver text, tech json, is_cdn bool, cdn_name text, final_url text, waf text,
          asn int8, asn_org text, favicon_hash text, tls_not_after timestamptz,
          tls_expired bool, tls_self_signed bool, interest_score int, interest_band text,
          interest_kinds json, hygiene_issues json, hygiene_checked json,
          screenshot_path text, screenshot_phash int8, posture_issues json,
          posture_checked json, port int, scheme text, ip text);""",
        """CREATE TEMP TABLE web (
          wkey int, id uuid, url text, host text, port int, scheme text, ip text,
          subdomain_id uuid, tech json, software json);
        CREATE INDEX ON web (wkey);""",
        """CREATE TEMP TABLE zone_all (scan_id uuid, zone text, hosts int);""",
        """CREATE TEMP TABLE paths (
          pid int PRIMARY KEY, path text, dir text, file text, ext text, depth int,
          shape text, fshape text, klass text, interests text[], ctype text);""",
        """CREATE TEMP TABLE psets (
          psid int PRIMARY KEY, csv text, fcsv text, query text, samples text,
          interests text[], names text[]);""",
        """CREATE TEMP TABLE port_catalog (
          number int, service text, klass text, is_http bool, tls bool, prob float8,
          product text, version text, banner text);""",
        """CREATE TEMP TABLE det (
          rn int, key text, vendor text, grp text, public bool, prefix text);""",
        """CREATE TEMP TABLE swp (name text, version text, vendor text, product text);""",
    ]
    return "\n".join(parts)


def comp_function() -> str:
    arms = " ".join(
        f"WHEN {lit(item)} THEN {lit(comp)}::json" for item, comp in tech_components()
    )
    return (
        "CREATE FUNCTION pg_temp.comp(text) RETURNS json STABLE LANGUAGE sql AS "
        f"$f$ SELECT CASE $1 {arms} END $f$;"
    )


def software_expr(tech: str, server: str) -> str:
    return (
        "(SELECT coalesce(json_agg(x.c ORDER BY x.o), '[]'::json) FROM ("
        f"SELECT pg_temp.comp(t.v) AS c, t.o FROM json_array_elements_text({tech}) "
        "WITH ORDINALITY AS t(v, o) "
        f"UNION ALL SELECT pg_temp.comp('ws:' || {server}), 1000) x WHERE x.c IS NOT NULL)"
    )


def hash_of(value: str) -> int:
    return int(hashlib.md5(value.encode(), usedforsecurity=False).hexdigest()[:8], 16)


TEMPLATES_SQL = f"""
CREATE TEMP TABLE tpl AS
WITH base AS (
  SELECT t.template_id, t.name, {lit(OFFICIAL_ROOT + "/")} || t.path AS path, t.severity,
         t.protocol, t.tags, t.authors, t."references" AS refs, t.cwe_ids, t.cvss_score,
         t.description, t.remediation,
         coalesce(t.cve_ids::jsonb ->> 0,
                  CASE WHEN upper(t.template_id) ~ '^CVE-[0-9]+-[0-9]+$'
                       THEN upper(t.template_id) END) AS cve
    FROM vuln_templates t
   WHERE t.enabled AND NOT t.needs_oast
     AND t.protocol IN ({lit(Protocol.HTTP.value)}, {lit(Protocol.SSL.value)},
                        {lit(Protocol.DNS.value)}, {lit(Protocol.NETWORK.value)})
     AND t.severity <> {lit(Severity.UNKNOWN.value)}
     AND t.path NOT LIKE 'dast/%' AND t.path NOT LIKE 'cloud/%'
), linked AS (
  SELECT b.*, n.cve IS NOT NULL AS has_cve, e.score AS epss, e.percentile AS pct,
         k.cve IS NOT NULL AS kev, coalesce(k.known_ransomware, false) AS ransom,
         k.due_date AS due
    FROM base b
    LEFT JOIN nvd_cves n ON n.cve = b.cve
    LEFT JOIN epss_scores e ON e.cve = n.cve
    LEFT JOIN kev_entries k ON k.cve = n.cve
), ranked AS (
  SELECT l.*, row_number() OVER (PARTITION BY severity, has_cve ORDER BY hashtext(template_id)) AS rn
    FROM linked l
)
SELECT * FROM ranked WHERE rn <= 400;
CREATE INDEX ON tpl (severity, has_cve, rn);
CREATE TEMP TABLE tpl_counts AS SELECT severity, has_cve, count(*)::int AS n FROM tpl GROUP BY 1, 2;
"""

SOFTWARE_SQL = """
CREATE TEMP TABLE swc AS
SELECT p.name, p.version, p.vendor, p.product, c.cve, c.severity, c.cvss_score,
       e.score AS epss, e.percentile AS pct, k.cve IS NOT NULL AS kev,
       coalesce(k.known_ransomware, false) AS ransom, k.due_date AS due, c.rn
  FROM swp p
  CROSS JOIN LATERAL (
    SELECT n.cve, lower(coalesce(n.severity, 'unknown')) AS severity, n.cvss_score,
           row_number() OVER (ORDER BY n.cvss_score DESC NULLS LAST, n.cve) AS rn
      FROM (SELECT DISTINCT m.cve FROM nvd_cpe_matches m
             WHERE m.product = p.product AND m.vendor = p.vendor) d
      JOIN nvd_cves n ON n.cve = d.cve
     ORDER BY n.cvss_score DESC NULLS LAST, n.cve
     LIMIT 40 OFFSET 0
  ) c
  LEFT JOIN epss_scores e ON e.cve = c.cve
  LEFT JOIN kev_entries k ON k.cve = c.cve;
CREATE INDEX ON swc (name, version, rn);
"""

# ---------- per-scan statements ----------

SUB_K_SQL = f"""
INSERT INTO sub_k
SELECT g.i, b.pzone, gen_random_uuid(),
       CASE WHEN h.web THEN gen_random_uuid() END,
       CASE WHEN h.web THEN ((g.i - 1) / 20) * 11 + (g.i - 1) % 20 END,
       b.key, b.name,
       CASE WHEN b.us < 0.70 THEN json_build_array({lit(SubdomainSource.SUBFINDER.value)})
            WHEN b.us < 0.85 THEN json_build_array({lit(SubdomainSource.SUBFINDER.value)},
                                                   {lit(SubdomainSource.CRTNAME.value)})
            WHEN b.us < 0.90 THEN json_build_array({lit(SubdomainSource.TLS_CERT.value)})
            WHEN b.us < 0.95 THEN json_build_array({lit(SubdomainSource.BRUTEFORCE.value)})
            ELSE json_build_array({lit(SubdomainSource.CRTNAME.value)}) END,
       CASE WHEN NOT b.active THEN '[]'::json
            WHEN n.ip2 IS NULL THEN json_build_array(n.ip1)
            ELSE json_build_array(n.ip1, n.ip2) END,
       CASE WHEN h.cdn AND b.active THEN b.name || '.cdn.cloudflare.net'
            WHEN b.active AND pg_temp.u(b.key || ':cn') < 0.12 THEN
              (ARRAY['d' || substr(md5(b.name), 1, 14) || '.cloudfront.net',
                     'lb-' || (g.i % 9) || '.' || $7::text,
                     $8::text || '.azurewebsites.net',
                     'ghs.googlehosted.com'])[1 + (pg_temp.hn(b.key || ':cv') % 4)::int]
            WHEN NOT b.active AND pg_temp.u(b.key || ':dn') < 0.03
              THEN $8::text || '-' || g.i || '.s3.amazonaws.com' END,
       b.active,
       $6::int > 0 AND pg_temp.u(b.key || ':wc') < 0.01,
       pg_temp.u(b.key || ':imp') < 0.002,
       b.seen,
       CASE WHEN h.web THEN p.scheme || '://' || b.name
                       || CASE WHEN p.port IN (80, 443) THEN '' ELSE ':' || p.port END END,
       s.status,
       CASE s.status / 100
         WHEN 2 THEN CASE WHEN pg_temp.u(b.key || ':tb') < 0.1 THEN initcap($8::text) || ' Portal'
                          ELSE pg_temp.p_title200(power(pg_temp.u(b.key || ':t'), 1.8)) END
         WHEN 3 THEN CASE WHEN pg_temp.u(b.key || ':t') < 0.5 THEN '' ELSE s.status || ' Moved' END
         WHEN 4 THEN CASE s.status WHEN 403 THEN pg_temp.p_title403(pg_temp.u(b.key || ':t'))
                                   WHEN 401 THEN pg_temp.p_title401(pg_temp.u(b.key || ':t'))
                                   ELSE pg_temp.p_title404(pg_temp.u(b.key || ':t')) END
         WHEN 5 THEN pg_temp.p_title5xx(pg_temp.u(b.key || ':t')) END,
       CASE WHEN h.web THEN CASE WHEN pg_temp.u(b.key || ':ct') < 0.1 THEN 'application/json'
                                 ELSE 'text/html; charset=utf-8' END END,
       CASE WHEN h.web THEN (200 + power(pg_temp.u(b.key || ':cl'), 3) * 200000)::int END,
       CASE WHEN h.web THEN round((0.05 + pg_temp.u(b.key || ':rt') * 1.5)::numeric, 4)::float8 END,
       CASE WHEN h.web THEN pg_temp.p_webserver(power(pg_temp.u(b.key || ':ws'), 1.5)) END,
       CASE WHEN h.web THEN (SELECT to_json(array_agg(DISTINCT
                 pg_temp.p_tech(power(pg_temp.u(b.key || ':tc' || q), 1.6))))
               FROM generate_series(1, 1 + (pg_temp.hn(b.key || ':tn') % 4)::int) q)
            ELSE '[]'::json END,
       h.cdn AND b.active,
       CASE WHEN h.cdn AND b.active THEN 'cloudflare'
            WHEN b.active AND pg_temp.asn_of(n.ip1) IN (16509, 14618) THEN 'aws' END,
       CASE WHEN s.status IN (301, 302) THEN 'https://' || b.name || '/'
            WHEN h.web THEN p.scheme || '://' || b.name
                       || CASE WHEN p.port IN (80, 443) THEN '' ELSE ':' || p.port END END,
       CASE WHEN h.web AND h.cdn AND pg_temp.u(b.key || ':waf') < 0.6 THEN 'Cloudflare'
            WHEN h.web AND pg_temp.u(b.key || ':waf') < 0.05 THEN 'AWS WAF' END,
       CASE WHEN b.active THEN pg_temp.asn_of(n.ip1) END,
       CASE WHEN b.active THEN pg_temp.asn_org(pg_temp.asn_of(n.ip1)) END,
       CASE WHEN h.web AND pg_temp.u(b.key || ':fv') < 0.6
            THEN pg_temp.p_favicon(power(pg_temp.u(b.key || ':fh'), 2)) END,
       CASE WHEN p.scheme = 'https' THEN t.not_after END,
       CASE WHEN p.scheme = 'https' THEN t.not_after < $5::timestamptz END,
       CASE WHEN p.scheme = 'https' THEN pg_temp.u(b.key || ':ss') < 0.04 END,
       CASE WHEN h.web AND pg_temp.u(b.key || ':int') < 0.12
            THEN 1 + floor(power(pg_temp.u(b.key || ':is'), 1.5) * 94)::int ELSE 0 END,
       NULL, '[]'::json,
       CASE WHEN h.web THEN hv.issues END,
       CASE WHEN h.web THEN hv.checked END,
       CASE WHEN s.status = 200 AND pg_temp.u(b.key || ':shot') < 0.3
            THEN $1::text || '/screenshot/' || b.name || '/index.webp' END,
       CASE WHEN s.status = 200 AND pg_temp.u(b.key || ':shot') < 0.3
            THEN hashtextextended(b.name || CASE WHEN pg_temp.u(b.key || ':shc' || $4::int) < 0.05
                                               THEN $4::text ELSE '' END, 0) END,
       pv.issues,
       pv.checked,
       CASE WHEN h.web THEN p.port END,
       CASE WHEN h.web THEN p.scheme END,
       CASE WHEN b.active THEN n.ip1 END
  FROM generate_series(1, $3::int) AS g(i)
  CROSS JOIN LATERAL (
    SELECT pg_temp.sub_name(g.i, $6::int, $7::text) AS name,
           (g.i - 1) % 20 < 16 AS active,
           $2::text || ':' || g.i AS key,
           pg_temp.u($2::text || ':' || g.i || ':src') AS us,
           $5::timestamptz + make_interval(secs => 300 + g.i % 5400) AS seen,
           CASE WHEN $6::int > 0 THEN
                  CASE WHEN g.i % $6::int < {MAX_ZONES_PER_SCAN}
                       THEN 'stress-agency-' || lpad((g.i % $6::int)::text, 4, '0') || '.' || $7::text END
                ELSE $9::text END AS pzone OFFSET 0
  ) b
  CROSS JOIN LATERAL (
    SELECT b.active AND (g.i - 1) % 20 < 11 AND $11::bool AS web,
           pg_temp.u(b.key || ':cdn') < 0.15 AS cdn OFFSET 0
  ) h
  CROSS JOIN LATERAL (
    SELECT CASE
             WHEN h.cdn THEN '104.18.' || (pg_temp.hn('c' || b.key) % 8) || '.'
                             || (pg_temp.hn('c' || b.key) / 8 % 256)
             WHEN pg_temp.u(b.key || ':v6') < 0.03
               THEN '2001:db8:' || to_hex($10::int) || '::' || to_hex((pg_temp.hn(b.key || ':ip') % $12::int)::int)
             ELSE '23.' || (100 + $10::int) || '.' || (pg_temp.hn(b.key || ':ip') % $12::int / 256 % 256)
                  || '.' || (pg_temp.hn(b.key || ':ip') % $12::int % 256) END AS ip1,
           CASE WHEN pg_temp.u(b.key || ':ip2') >= 0.25 THEN NULL
                WHEN h.cdn THEN '104.18.' || (pg_temp.hn('d' || b.key) % 8) || '.'
                                || (pg_temp.hn('d' || b.key) / 8 % 256)
                ELSE '23.' || (100 + $10::int) || '.' || (pg_temp.hn(b.key || ':ipb') % $12::int / 256 % 256)
                     || '.' || (pg_temp.hn(b.key || ':ipb') % $12::int % 256) END AS ip2 OFFSET 0
  ) n
  CROSS JOIN LATERAL (
    SELECT CASE WHEN NOT h.web THEN NULL
                ELSE CASE WHEN x < 0.58 THEN 200 WHEN x < 0.70 THEN 301 WHEN x < 0.74 THEN 302
                          WHEN x < 0.86 THEN 403 WHEN x < 0.94 THEN 404 WHEN x < 0.96 THEN 401
                          WHEN x < 0.98 THEN 500 ELSE 503 END END AS status
      FROM (SELECT CASE WHEN pg_temp.u(b.key || ':flip' || $4::int) < 0.03
                        THEN pg_temp.u(b.key || ':st' || $4::int)
                        ELSE pg_temp.u(b.key || ':st') END AS x) q OFFSET 0
  ) s
  CROSS JOIN LATERAL (
    SELECT CASE WHEN x < 0.72 THEN 443 WHEN x < 0.92 THEN 80
                ELSE (ARRAY[8080, 8443, 8000, 3000, 9000, 11434, 5000, 8888])
                       [1 + least(7, floor((x - 0.92) / 0.08 * 8)::int)] END AS port,
           CASE WHEN x < 0.72 OR (x >= 0.92 AND least(7, floor((x - 0.92) / 0.08 * 8)::int) = 1)
                THEN 'https' ELSE 'http' END AS scheme
      FROM (SELECT pg_temp.u(b.key || ':port') AS x) q OFFSET 0
  ) p
  CROSS JOIN LATERAL (
    SELECT $5::timestamptz + make_interval(days => (pg_temp.u(b.key || ':tls') * 420)::int - 25) AS not_after OFFSET 0
  ) t
  LEFT JOIN hyg_var hv ON hv.https = (p.scheme = 'https') AND hv.v = pg_temp.hn(b.key || ':hv') % {VARIANTS}
  LEFT JOIN posture_var pv ON pv.v = pg_temp.hn(b.pzone) % {VARIANTS}
 WHERE g.i <= 2 OR (g.i::int8 * 7919 + $4::int8 * 104729) % {DROP_MOD} <> 0
"""

SUB_K_BANDS_SQL = f"""
UPDATE sub_k SET
  interest_band = CASE WHEN interest_score >= {BAND_FLOOR[InterestBand.CRITICAL.value]}
                         THEN {lit(InterestBand.CRITICAL.value)}
                       WHEN interest_score >= {BAND_FLOOR[InterestBand.HIGH.value]}
                         THEN {lit(InterestBand.HIGH.value)}
                       ELSE {lit(InterestBand.NOTABLE.value)} END,
  interest_kinds = json_build_array(pg_temp.p_kind(pg_temp.u(key || ':k1')))
 WHERE interest_score > 0
"""

SUBDOMAINS_SQL = """
INSERT INTO subdomains (
  id, scan_id, target_id, project_id, name, sources, resolved_ips, cname, is_active,
  is_wildcard, discovered_at, created_at, is_excluded, is_important, http_url, http_status,
  page_title, content_type, content_length, response_time, webserver, tech, is_cdn, cdn_name,
  screenshot_path, final_url, waf, asn, asn_org, favicon_hash, tls_not_after, tls_expired,
  tls_self_signed, interest_score, interest_band, interest_kinds, hygiene_issues,
  hygiene_checked, screenshot_phash, posture_issues, posture_checked)
SELECT sub_id, $1::uuid, $2::uuid, $3::uuid, name, sources, resolved_ips, cname, is_active,
       is_wildcard, discovered_at, discovered_at, false, is_important, http_url, http_status,
       page_title, content_type, content_length, response_time, webserver, tech, is_cdn,
       cdn_name, screenshot_path, final_url, waf, asn, asn_org, favicon_hash, tls_not_after,
       tls_expired, tls_self_signed, interest_score, interest_band, interest_kinds,
       hygiene_issues, hygiene_checked, screenshot_phash, posture_issues, posture_checked
  FROM sub_k WHERE i > $4::int AND i <= $5::int ORDER BY name
"""

HTTP_ASSETS_SQL = f"""
INSERT INTO http_assets (
  id, scan_id, target_id, project_id, url, host, port, scheme, status_code, title, webserver,
  content_length, content_type, location, tech, ip, cname, asn, asn_org, is_cdn, cdn_name, waf,
  jarm, favicon_hash, content_hash, tls_issuer, tls_subject_cn, tls_sans, tls_not_after,
  tls_self_signed, tls_expired, tls_version, screenshot_path, discovered_at, created_at,
  final_url, method, path, chain_status_codes, response_time, words, lines, cpe, header_hash,
  supports_http2, supports_pipeline, a_records, aaaa_records, cdn_type, tls_cipher,
  tls_subject_dn, tls_issuer_cn, tls_issuer_org, tls_serial, tls_fingerprint, tls_not_before,
  raw_request, raw_response_header, response_body, response_headers, body_preview, software,
  hygiene_issues, hygiene_checked, not_found, screenshot_phash, tracking_ids, ai_checked,
  ai_service, ai_category, ai_endpoint, ai_models)
SELECT a.id, $1::uuid, $2::uuid, $3::uuid, a.url, s.name, a.port, a.scheme, a.status,
       a.title, s.webserver, s.content_length, s.content_type, a.location, s.tech, s.ip, s.cname,
       s.asn, s.asn_org, s.is_cdn, s.cdn_name, s.waf,
       CASE WHEN a.scheme = 'https' THEN pg_temp.p_jarm(pg_temp.u(s.key || ':jarm')) END,
       s.favicon_hash,
       CASE WHEN pg_temp.u(s.key || ':uniq') < 0.25 THEN pg_temp.sha(a.url)
            ELSE pg_temp.sha(a.status || '|' || coalesce(a.title, '') || '|' || (pg_temp.hn(s.key) % 4)) END,
       c.issuer, c.cn, c.sans, s.tls_not_after, s.tls_self_signed, s.tls_expired,
       CASE WHEN a.scheme = 'https' THEN CASE WHEN pg_temp.u(s.key || ':tv') < 0.8 THEN 'tls13' ELSE 'tls12' END END,
       s.screenshot_path, s.discovered_at + interval '20 minutes', s.discovered_at + interval '20 minutes',
       CASE WHEN a.location IS NOT NULL THEN a.location ELSE s.final_url END, 'GET', '/',
       a.chain, s.response_time, greatest(1, s.content_length / 7), greatest(1, s.content_length / 60),
       '[]'::json, pg_temp.sha(coalesce(s.webserver, '') || '|' || a.status || '|' || (pg_temp.hn(s.key) % 3)),
       a.scheme = 'https' AND pg_temp.u(s.key || ':h2') < 0.6, false,
       coalesce((SELECT json_agg(v) FROM json_array_elements_text(s.resolved_ips) v WHERE strpos(v, ':') = 0), '[]'::json),
       coalesce((SELECT json_agg(v) FROM json_array_elements_text(s.resolved_ips) v WHERE strpos(v, ':') > 0), '[]'::json),
       CASE WHEN s.is_cdn THEN 'cdn' WHEN s.cdn_name IS NOT NULL THEN 'cloud' END,
       CASE WHEN a.scheme = 'https' THEN 'TLS_AES_128_GCM_SHA256' END,
       CASE WHEN a.scheme = 'https' THEN 'CN=' || c.cn || ', O=' || initcap($4::text) END,
       c.issuer_cn, c.issuer,
       CASE WHEN a.scheme = 'https' THEN upper(substr(md5(c.cn || c.issuer), 1, 32)) END,
       CASE WHEN a.scheme = 'https' THEN pg_temp.sha(c.cn || '|' || c.issuer) END,
       CASE WHEN a.scheme = 'https' THEN s.tls_not_after - interval '90 days' END,
       'GET / HTTP/1.1' || E'\\r\\n' || 'Host: ' || s.name || E'\\r\\n'
         || 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0' || E'\\r\\n'
         || 'Accept: */*' || E'\\r\\n\\r\\n',
       'HTTP/1.1 ' || a.status || E'\\r\\n' || 'Server: ' || coalesce(s.webserver, '') || E'\\r\\n'
         || 'Content-Type: ' || coalesce(s.content_type, '') || E'\\r\\n'
         || CASE WHEN a.location IS NOT NULL THEN 'Location: ' || a.location || E'\\r\\n' ELSE '' END
         || 'Set-Cookie: session=' || md5(s.key) || '; Path=/; HttpOnly' || E'\\r\\n',
       a.body, a.headers, left(a.body, 512),
       {software_expr("s.tech", "s.webserver")},
       s.hygiene_issues, s.hygiene_checked,
       CASE WHEN pg_temp.u(s.key || ':soft404') < 0.15 THEN
              json_build_array(json_build_object('status', 200, 'hash', pg_temp.sha(a.status || '|' || coalesce(a.title, '') || '|' || (pg_temp.hn(s.key) % 4)),
                                                 'words', 40, 'lines', 9, 'title', a.title))
            ELSE (SELECT json_agg(json_build_object('status', 404, 'hash', pg_temp.sha(coalesce(s.webserver, '') || coalesce(s.cdn_name, '')),
                                                    'words', 5 + n.c, 'lines', 1, 'title', '404 Not Found'))
                    FROM generate_series(1, 3) AS n(c)) END,
       s.screenshot_phash, '[]'::json,
       a.port = 11434 OR pg_temp.u(s.key || ':ai') < 0.4,
       CASE WHEN a.port = 11434 THEN $6::text END,
       CASE WHEN a.port = 11434 THEN $5::text END,
       CASE WHEN a.port = 11434 THEN a.url || '/api/tags' END,
       CASE WHEN a.port = 11434 THEN '["llama3:8b", "qwen2.5:7b"]'::json END
  FROM sub_k s
  CROSS JOIN LATERAL (
    SELECT s.ha_id AS id, s.http_url AS url, s.port, s.scheme, s.http_status AS status,
           s.page_title AS title,
           CASE WHEN s.http_status IN (301, 302) THEN s.final_url END AS location,
           CASE WHEN s.http_status IN (301, 302) THEN '[301, 200]'::json ELSE '[]'::json END AS chain,
           '<!DOCTYPE html><html><head><title>' || coalesce(s.page_title, '') || '</title></head><body>'
             || repeat('<div class="section"><h2>' || initcap($4::text) || '</h2><p>Services, news and '
                       || 'contact details for the ' || $4::text || ' team.</p></div>',
                       1 + (pg_temp.hn(s.key || ':body') % 40)::int)
             || '</body></html>' AS body,
           json_strip_nulls(json_build_object(
             'content_type', s.content_type, 'server', nullif(s.webserver, ''),
             'strict_transport_security',
               CASE WHEN s.scheme = 'https' AND NOT (s.hygiene_issues::jsonb ? {lit(HygieneCheck.NO_HSTS.value)})
                    THEN 'max-age=31536000; includeSubDomains' END,
             'x_frame_options', CASE WHEN NOT (s.hygiene_issues::jsonb ? {lit(HygieneCheck.NO_FRAME_PROTECTION.value)}) THEN 'SAMEORIGIN' END)) AS headers
    UNION ALL
    SELECT gen_random_uuid(), 'http://' || s.name, 80, 'http', 301, '301 Moved Permanently',
           'https://' || s.name || '/', '[301, 200]'::json,
           '<html><body>Moved</body></html>',
           json_build_object('content_type', 'text/html', 'location', 'https://' || s.name || '/')
     WHERE s.port = 443 AND pg_temp.u(s.key || ':extra') < 0.04
  ) a
  CROSS JOIN LATERAL (
    SELECT CASE WHEN a.scheme = 'https' THEN pg_temp.p_issuer(pg_temp.u(s.key || ':iss')) END AS issuer,
           CASE WHEN a.scheme = 'https' THEN pg_temp.p_issuer_cn(pg_temp.u(s.key || ':iss')) END AS issuer_cn,
           CASE WHEN a.scheme <> 'https' THEN NULL
                WHEN pg_temp.u(s.key || ':wild') < 0.4 THEN '*.' || coalesce(s.zone, regexp_replace(s.name, '^[^.]+[.]', ''))
                ELSE s.name END AS cn,
           CASE WHEN a.scheme = 'https'
                THEN json_build_array(s.name, '*.' || coalesce(s.zone, regexp_replace(s.name, '^[^.]+[.]', '')))
                ELSE '[]'::json END AS sans OFFSET 0
  ) c
 WHERE s.ha_id IS NOT NULL AND s.i > $7::int AND s.i <= $8::int
"""

IP_FROM_NAMES_SQL = f"""
INSERT INTO ip_addresses (
  id, scan_id, target_id, project_id, ip, version, source, ptr_hostnames, asn, asn_org, prefix,
  country, is_cdn, cdn_name, is_alive, discovered_at, created_at, cdn_type, scan_policy,
  scan_policy_reason)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, a.ip,
       CASE WHEN strpos(a.ip, ':') > 0 THEN 6 ELSE 4 END,
       {lit(IpSource.DNS_RESOLUTION.value)},
       CASE WHEN pg_temp.u(a.ip || ':ptr') < 0.2 AND strpos(a.ip, ':') = 0
            THEN json_build_array('ip-' || replace(a.ip, '.', '-') || '.static.example.net')
            ELSE '[]'::json END,
       pg_temp.asn_of(a.ip), pg_temp.asn_org(pg_temp.asn_of(a.ip)),
       CASE WHEN strpos(a.ip, ':') = 0
            THEN split_part(a.ip, '.', 1) || '.' || split_part(a.ip, '.', 2) || '.'
                 || split_part(a.ip, '.', 3) || '.0/24' END,
       CASE WHEN a.ip LIKE '104.18.%' THEN 'US' ELSE pg_temp.p_country(pg_temp.u(a.ip)) END,
       a.ip LIKE '104.18.%',
       CASE WHEN a.ip LIKE '104.18.%' THEN 'cloudflare'
            WHEN pg_temp.asn_of(a.ip) IN (16509, 14618) THEN 'aws' END,
       NULL, a.seen, a.seen,
       CASE WHEN a.ip LIKE '104.18.%' THEN 'cdn'
            WHEN pg_temp.asn_of(a.ip) IN (16509, 14618) THEN 'cloud' END,
       CASE WHEN a.ip LIKE '104.18.%' THEN {lit(ScanPolicy.WEB.value)} ELSE {lit(ScanPolicy.FULL.value)} END,
       CASE WHEN a.ip LIKE '104.18.%' THEN {lit(ScanPolicyReason.CDN.value)} END
  FROM (SELECT v.ip, min(s.discovered_at) AS seen
          FROM sub_k s CROSS JOIN LATERAL json_array_elements_text(s.resolved_ips) AS v(ip)
         GROUP BY v.ip) a
 ORDER BY a.ip
"""

IP_FROM_RANGE_SQL = f"""
INSERT INTO ip_addresses (
  id, scan_id, target_id, project_id, ip, version, source, ptr_hostnames, asn, asn_org, prefix,
  country, is_cdn, is_alive, discovered_at, created_at, scan_policy)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, x.ip, 4,
       {lit(IpSource.CIDR_EXPANSION.value)}, '[]'::json,
       pg_temp.asn_of(x.ip), pg_temp.asn_org(pg_temp.asn_of(x.ip)),
       split_part(x.ip, '.', 1) || '.' || split_part(x.ip, '.', 2) || '.' || split_part(x.ip, '.', 3) || '.0/24',
       pg_temp.p_country(pg_temp.u('23.' || $5::int)), false, true,
       $7::timestamptz + make_interval(secs => 60 + g.p % 1800),
       $7::timestamptz + make_interval(secs => 60 + g.p % 1800),
       {lit(ScanPolicy.FULL.value)}
  FROM generate_series(0, $4::int - 1) AS g(p)
  CROSS JOIN LATERAL (SELECT '23.' || $5::int || '.' || (g.p / 256) || '.' || (g.p % 256) AS ip OFFSET 0
  ) x
 WHERE pg_temp.u(x.ip || ':alive') < 0.6
   AND pg_temp.u(x.ip || ':gone' || $6::int) >= 0.03
"""

PORTS_FROM_WEB_SQL = f"""
INSERT INTO ports (
  id, scan_id, target_id, project_id, ip, number, protocol, state, service_name, source,
  discovered_at, created_at, service_class, is_http, tls, cpe)
SELECT DISTINCT ON (s.ip, s.port) gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, s.ip, s.port,
       'tcp', {lit(PortState.OPEN.value)}, coalesce(c.service, CASE WHEN s.scheme = 'https' THEN 'https' ELSE 'http' END),
       {lit(PortSource.HTTP_PROBE.value)}, s.discovered_at + interval '15 minutes',
       s.discovered_at + interval '15 minutes', coalesce(c.klass, 'web'), true, s.scheme = 'https', '[]'::json
  FROM sub_k s LEFT JOIN port_catalog c ON c.number = s.port
 WHERE s.ha_id IS NOT NULL AND s.ip IS NOT NULL AND strpos(s.ip, ':') = 0
 ORDER BY s.ip, s.port
ON CONFLICT (scan_id, ip, number, protocol) DO NOTHING
"""

PORTS_FROM_CATALOG_SQL = f"""
INSERT INTO ports (
  id, scan_id, target_id, project_id, ip, number, protocol, state, service_name, source,
  discovered_at, created_at, service_class, is_http, tls, product, version, banner, cpe)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, a.ip, c.number, 'tcp',
       {lit(PortState.OPEN.value)}, c.service,
       CASE WHEN c.is_http AND pg_temp.u(a.ip || c.number || ':src') < 0.5 THEN {lit(PortSource.HTTP_PROBE.value)}
            ELSE (ARRAY[{lit(PortSource.NAABU.value)}, {lit(PortSource.NAABU.value)},
                        {lit(PortSource.NAABU.value)}, {lit(PortSource.NAABU.value)},
                        {lit(PortSource.INTERNETDB.value)}, {lit(PortSource.SHODAN.value)},
                        {lit(PortSource.BANNER.value)}])
                 [1 + (pg_temp.hn(a.ip || c.number || ':s2') % 7)::int] END,
       a.discovered_at + interval '40 minutes', a.discovered_at + interval '40 minutes',
       c.klass, c.is_http, c.tls,
       CASE WHEN pg_temp.u(a.ip || c.number || ':prod') < 0.4 THEN c.product END,
       CASE WHEN pg_temp.u(a.ip || c.number || ':prod') < 0.4 THEN c.version END,
       CASE WHEN pg_temp.u(a.ip || c.number || ':prod') < 0.4 THEN c.banner END,
       '[]'::json
  FROM ip_addresses a
  JOIN port_catalog c
    ON (a.is_cdn AND c.number IN (80, 443))
    OR (NOT a.is_cdn AND pg_temp.u(a.ip || ':' || c.number) < c.prob)
 WHERE a.scan_id = $1::uuid AND a.version = 4
 ORDER BY a.ip, c.number
ON CONFLICT (scan_id, ip, number, protocol) DO NOTHING
"""

HTTP_FROM_PORTS_SQL = f"""
INSERT INTO http_assets (
  id, scan_id, target_id, project_id, url, host, port, scheme, status_code, title, webserver,
  content_length, content_type, tech, ip, asn, asn_org, content_hash, discovered_at, created_at,
  final_url, method, path, words, lines, header_hash, a_records, raw_request,
  raw_response_header, response_body, response_headers, body_preview, software,
  hygiene_issues, hygiene_checked, not_found, ai_checked)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, x.url, p.ip, p.number, x.scheme,
       x.status, x.title, x.ws, x.len, 'text/html', x.tech, p.ip, pg_temp.asn_of(p.ip),
       pg_temp.asn_org(pg_temp.asn_of(p.ip)), pg_temp.sha(x.status || '|' || x.title || '|' || coalesce(x.ws, '')),
       p.discovered_at + interval '10 minutes', p.discovered_at + interval '10 minutes', x.url,
       'GET', '/', greatest(1, x.len / 7), greatest(1, x.len / 60), pg_temp.sha(coalesce(x.ws, '') || x.status),
       json_build_array(p.ip),
       'GET / HTTP/1.1' || E'\\r\\n' || 'Host: ' || p.ip || E'\\r\\n\\r\\n',
       'HTTP/1.1 ' || x.status || E'\\r\\n' || 'Server: ' || coalesce(x.ws, '') || E'\\r\\n',
       '<html><head><title>' || x.title || '</title></head><body>' || repeat('<p>default page</p>', 20) || '</body></html>',
       json_strip_nulls(json_build_object('content_type', 'text/html', 'server', nullif(x.ws, ''))),
       '<html><head><title>' || x.title || '</title></head>',
       {software_expr("x.tech", "x.ws")},
       hv.issues, hv.checked,
       json_build_array(json_build_object('status', 404, 'hash', pg_temp.sha(coalesce(x.ws, '')),
                                          'words', 6, 'lines', 1, 'title', '404 Not Found')),
       false
  FROM ports p
  CROSS JOIN LATERAL (
    SELECT CASE WHEN p.tls THEN 'https' ELSE 'http' END AS scheme,
           CASE WHEN p.tls THEN 'https' ELSE 'http' END || '://' || p.ip
             || CASE WHEN p.number IN (80, 443) THEN '' ELSE ':' || p.number END AS url,
           (ARRAY[200, 200, 200, 200, 404, 404, 404, 403, 403, 400])[1 + (pg_temp.hn(p.ip || p.number) % 10)::int] AS status,
           pg_temp.p_title200(power(pg_temp.u(p.ip || p.number || ':t'), 1.5)) AS title,
           pg_temp.p_webserver(pg_temp.u(p.ip || p.number || ':ws')) AS ws,
           (300 + pg_temp.u(p.ip || ':len') * 20000)::int AS len,
           json_build_array(pg_temp.p_tech(power(pg_temp.u(p.ip || p.number || ':tc'), 1.5))) AS tech OFFSET 0
  ) x
  JOIN hyg_var hv ON hv.https = (x.scheme = 'https') AND hv.v = pg_temp.hn(p.ip || p.number) % {VARIANTS}
 WHERE p.scan_id = $1::uuid AND p.is_http
"""

WEB_FROM_NAMES_SQL = """
INSERT INTO web
SELECT s.wkey, s.ha_id, s.http_url, s.name, s.port, s.scheme, s.ip, s.sub_id, s.tech, h.software
  FROM sub_k s JOIN http_assets h ON h.id = s.ha_id
 WHERE s.ha_id IS NOT NULL
"""

WEB_FROM_DB_SQL = """
INSERT INTO web
SELECT (row_number() OVER (ORDER BY h.host, h.port) - 1)::int, h.id, h.url, h.host, h.port,
       h.scheme, h.ip, s.id, h.tech, h.software
  FROM http_assets h
  LEFT JOIN subdomains s ON s.scan_id = h.scan_id AND s.name = h.host
 WHERE h.scan_id = $1::uuid AND NOT (h.port = 80 AND h.status_code = 301 AND h.title = '301 Moved Permanently')
"""

ZONES_SQL = """
INSERT INTO zone_all
SELECT $1::uuid, z.zone, count(*)
  FROM subdomains s
  CROSS JOIN LATERAL (
    SELECT coalesce(substring(s.name FROM '(stress-agency-[0-9]+[.].*)$'), $2::text) AS zone OFFSET 0
  ) z
 WHERE s.scan_id = $1::uuid AND s.posture_issues IS NOT NULL
 GROUP BY z.zone
"""

WEB_FROM_ASSETS_SQL = """
INSERT INTO web
SELECT (row_number() OVER (ORDER BY h.host, h.port) - 1)::int, h.id, h.url, h.host, h.port,
       h.scheme, h.ip, NULL, h.tech, h.software
  FROM http_assets h WHERE h.scan_id = $1::uuid
"""

ENDPOINTS_SQL = f"""
INSERT INTO endpoints (
  id, scan_id, target_id, project_id, signature, url, host, port, scheme, path, dir_path,
  filename, extension, depth, params, param_count, param_samples, variants, more_variants,
  methods, sources, primary_source, discovery, found_on, is_probed, status_code, content_type,
  content_length, title, words, lines, response_time, redirect_location, content_hash, tech,
  endpoint_class, interest, http_asset_id, subdomain_id, archive_last_seen, discovered_at,
  created_at, shape, family)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid,
       pg_temp.sha(w.scheme || '://' || w.host || ':' || w.port || '|' || x.path || '|' || ps.csv),
       left(w.url || x.path || CASE WHEN ps.query <> '' THEN '?' || replace(ps.query, '{{v}}', (g.j % 997)::text) ELSE '' END, 2000),
       w.host, w.port, w.scheme, x.path, x.dir, x.file, p.ext, p.depth,
       to_json(ps.names), coalesce(array_length(ps.names, 1), 0),
       replace(ps.samples, '{{v}}', (g.j % 997)::text)::json, 1, false,
       CASE WHEN pg_temp.u(x.key || ':post') < 0.05 THEN '["GET", "POST"]'::json ELSE '["GET"]'::json END,
       to_json(m.srcs), m.first, m.discovery,
       CASE WHEN m.first = {lit(EndpointSource.CRAWL.value)} THEN w.url || '/' END,
       r.probed, r.status, CASE WHEN r.probed THEN p.ctype END,
       CASE WHEN r.probed THEN (100 + power(pg_temp.u(x.key || ':len'), 3) * 90000)::int END,
       CASE WHEN r.probed AND r.status = 200 AND p.klass IN ({lit(EndpointClass.PAGE.value)}, {lit(EndpointClass.API.value)})
            THEN pg_temp.p_etitle(pg_temp.u(x.key || ':title'))
            WHEN r.probed THEN '' END,
       CASE WHEN r.probed THEN 1 + (pg_temp.hn(x.key || ':len') % 4000)::int END,
       CASE WHEN r.probed THEN 1 + (pg_temp.hn(x.key || ':len') % 300)::int END,
       CASE WHEN r.probed THEN round((0.05 + pg_temp.u(x.key || ':rt'))::numeric, 4)::float8 END,
       CASE WHEN r.probed AND r.status IN (301, 302) THEN w.url || x.path || '/' END,
       CASE WHEN NOT r.probed THEN NULL
            WHEN pg_temp.u(x.key || ':same') < 0.7
              THEN pg_temp.sha(r.status || '|' || p.klass || '|' || (pg_temp.hn(w.host) % 7))
            ELSE pg_temp.sha(x.key) END,
       CASE WHEN pg_temp.u(x.key || ':tech') < 0.2 THEN w.tech ELSE '[]'::json END,
       p.klass,
       CASE WHEN ps.psid = 0 OR cardinality(ps.interests) = 0 THEN to_json(p.interests)
            WHEN cardinality(p.interests) = 0 THEN to_json(ps.interests)
            ELSE (SELECT to_json(array_agg(DISTINCT v ORDER BY v)) FROM unnest(p.interests || ps.interests) v) END,
       w.id, w.subdomain_id,
       CASE WHEN {lit(EndpointSource.ARCHIVE.value)} = ANY(m.srcs)
            THEN $7::timestamptz - make_interval(days => (pg_temp.hn(x.key || ':arch') % 900)::int) END,
       m.seen, m.seen, p.shape,
       pg_temp.sha(w.host || ':' || w.port || '|' || p.fshape || '|' || ps.fcsv)
  FROM (
    SELECT j,
           floor($8::int * power(pg_temp.u($4::text || ':eh:' || j), 3))::int AS wkey,
           1 + floor(pg_temp.u($4::text || ':ep:' || j) * {PATH_TEMPLATES})::int AS pid,
           CASE WHEN pg_temp.u($4::text || ':eq:' || j) < 0.3
                THEN 1 + floor(pg_temp.u($4::text || ':es:' || j) * {PARAM_SETS})::int ELSE 0 END AS psid
      FROM generate_series($9::int, $5::int) AS j
     WHERE (j::int8 * 7919 + $6::int8 * 104729) % {ENDPOINT_DROP_MOD} <> 0
  ) g
  JOIN web w ON w.wkey = g.wkey
  JOIN paths p ON p.pid = g.pid
  JOIN psets ps ON ps.psid = g.psid
  CROSS JOIN LATERAL (
    SELECT pg_temp.inst(p.path, g.j, $4::text) AS path, pg_temp.inst(p.dir, g.j, $4::text) AS dir,
           pg_temp.inst(p.file, g.j, $4::text) AS file, $4::text || ':e' || g.j AS key OFFSET 0
  ) x
  CROSS JOIN LATERAL (
    SELECT pg_temp.p_esource(pg_temp.u(x.key || ':s1')) AS s1,
           CASE WHEN pg_temp.u(x.key || ':s2') < 0.2 THEN pg_temp.p_esource(pg_temp.u(x.key || ':s3')) END AS s2,
           $7::timestamptz + interval '2 hours' + make_interval(secs => g.j % 7200) AS seen OFFSET 0
  ) m0
  CROSS JOIN LATERAL (
    SELECT CASE WHEN m0.s2 IS NULL OR m0.s2 = m0.s1 THEN ARRAY[m0.s1]
                ELSE ARRAY[least(m0.s1, m0.s2), greatest(m0.s1, m0.s2)] END AS srcs,
           m0.s1 AS first, m0.seen,
           CASE WHEN m0.s2 IS NULL OR m0.s2 = m0.s1
                THEN json_build_object(m0.s1, json_build_object('at', m0.seen))
                ELSE json_build_object(m0.s1, json_build_object('at', m0.seen),
                                       m0.s2, json_build_object('at', m0.seen)) END AS discovery OFFSET 0
  ) m
  CROSS JOIN LATERAL (
    SELECT pg_temp.u(x.key || ':probe') < 0.65 AS probed,
           CASE WHEN pg_temp.u(x.key || ':probe') < 0.65 OR pg_temp.u(x.key || ':katana') < 0.1
                THEN pg_temp.p_estatus(pg_temp.u(x.key || ':status')) END AS status OFFSET 0
  ) r
ON CONFLICT (scan_id, signature) DO NOTHING
"""

ENDPOINT_RESPONSES_SQL = """
INSERT INTO endpoint_responses (endpoint_id, scan_id, raw_response_header, response_body, created_at)
SELECT e.id, e.scan_id,
       'HTTP/1.1 ' || e.status_code || E'\\r\\n' || 'Content-Type: ' || coalesce(e.content_type, '') || E'\\r\\n'
         || 'Cache-Control: no-store' || E'\\r\\n',
       repeat('<div class="card"><h3>' || md5(e.signature) || '</h3><p>' || e.host || e.path
              || ' Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor '
              || 'incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud '
              || 'exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute '
              || 'irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla '
              || 'pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia '
              || 'deserunt mollit anim id est laborum.</p><a href="/next">next</a></div>',
              1 + (pg_temp.hn(e.signature) % 30)::int),
       e.discovered_at
  FROM endpoints e
 WHERE e.scan_id = $1::uuid AND e.content_hash IS NOT NULL AND pg_temp.u(e.signature) < 0.1
"""

VULNS_SQL = f"""
INSERT INTO vulnerabilities (
  id, scan_id, target_id, project_id, fingerprint, scanner, template_id, template_name,
  template_path, template_url, severity, protocol, matcher_name, extracted_results,
  description, remediation, "references", tags, authors, cve_ids, cwe_ids, cvss_score,
  epss_score, epss_percentile, is_kev, extra, matched_at, host, ip, port, scheme, url, path,
  subdomain_id, http_asset_id, request, response, curl_command, interaction, observed_at,
  discovered_at, created_at, exploit_score, intel_kinds, kev_ransomware, kev_due_date,
  template_available, evidence)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid,
       pg_temp.sha(t.template_id || '|' || m.matched), {lit(Scanner.NUCLEI.value)},
       t.template_id, t.name, t.path, 'https://cloud.projectdiscovery.io/public/' || t.template_id,
       t.severity, t.protocol,
       CASE WHEN pg_temp.u(g.key || ':mn') < 0.3 THEN 'version' END,
       CASE WHEN pg_temp.u(g.key || ':ex') < 0.25 THEN json_build_array('7.' || (g.v % 5) || '.' || (g.v % 30)) ELSE '[]'::json END,
       t.description, t.remediation, t.refs, t.tags, t.authors,
       CASE WHEN t.has_cve THEN json_build_array(t.cve) ELSE '[]'::json END,
       t.cwe_ids, t.cvss_score, t.epss, t.pct, t.kev, '{{}}'::json,
       m.matched, w.host, w.ip,
       CASE WHEN t.protocol = {lit(Protocol.DNS.value)} THEN NULL
            WHEN t.protocol = {lit(Protocol.SSL.value)} THEN 443 ELSE w.port END,
       CASE WHEN t.protocol = {lit(Protocol.HTTP.value)} THEN w.scheme END,
       CASE WHEN t.protocol = {lit(Protocol.HTTP.value)} THEN m.matched END,
       CASE WHEN t.protocol = {lit(Protocol.HTTP.value)} THEN nullif(m.vpath, '') END,
       w.subdomain_id, w.id,
       CASE WHEN m.heavy THEN 'GET ' || coalesce(nullif(m.vpath, ''), '/') || ' HTTP/1.1' || E'\\r\\n'
              || 'Host: ' || w.host || E'\\r\\n' || 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64)' || E'\\r\\n'
              || repeat('Cookie: pref=' || md5(g.key) || E'\\r\\n', 4 + (pg_temp.hn(g.key || ':rq') % 40)::int)
              || 'Connection: close' || E'\\r\\n\\r\\n' END,
       CASE WHEN m.heavy THEN 'HTTP/1.1 200 OK' || E'\\r\\n' || 'Content-Type: text/html' || E'\\r\\n\\r\\n'
              || repeat('<tr><td>' || md5(g.key || 'r') || '</td><td>config value</td><td>enabled</td></tr>',
                        30 + (pg_temp.hn(g.key || ':rs') % 270)::int) END,
       CASE WHEN m.heavy THEN 'curl -X ''GET'' -H ''Host: ' || w.host || ''' ''' || m.matched || '''' END,
       '{{}}'::json, m.seen, m.seen, m.seen,
       CASE WHEN t.kev THEN 90 WHEN coalesce(t.epss, 0) > 0.5 THEN 50 ELSE floor(coalesce(t.epss, 0) * 40)::int END,
       CASE WHEN t.kev THEN json_build_array({lit(ExploitSignal.KEV.value)}) ELSE '[]'::json END,
       t.ransom, t.due, true, {lit(Evidence.OBSERVED.value)}
  FROM (
    SELECT v, $4::text || ':v' || v AS key,
           CASE WHEN x < 0.05 THEN {lit(Severity.CRITICAL.value)} WHEN x < 0.17 THEN {lit(Severity.HIGH.value)}
                WHEN x < 0.37 THEN {lit(Severity.MEDIUM.value)} WHEN x < 0.52 THEN {lit(Severity.LOW.value)}
                ELSE {lit(Severity.INFO.value)} END AS sev,
           pg_temp.u($4::text || ':vc:' || v) < 0.2 AS cve,
           floor($8::int * power(pg_temp.u($4::text || ':vh:' || v), 2.5))::int AS wkey,
           pg_temp.u($4::text || ':vt:' || v) AS ut
      FROM (SELECT v, pg_temp.u($4::text || ':vs:' || v) AS x FROM generate_series($9::int, $5::int) v) q
     WHERE (v::int8 * 7919 + $6::int8 * 104729) % {ENDPOINT_DROP_MOD} <> 0
  ) g
  JOIN tpl_counts c ON c.severity = g.sev AND c.has_cve = g.cve
  JOIN tpl t ON t.severity = g.sev AND t.has_cve = g.cve AND t.rn = 1 + floor(power(g.ut, 2) * c.n)::int
  JOIN web w ON w.wkey = g.wkey
  CROSS JOIN LATERAL (
    SELECT pg_temp.p_vpath(pg_temp.u(g.key || ':vp')) AS vpath,
           pg_temp.u(g.key || ':heavy') < 0.3 AS heavy,
           $7::timestamptz + interval '4 hours' + make_interval(secs => g.v % 3600) AS seen OFFSET 0
  ) m0
  CROSS JOIN LATERAL (
    SELECT m0.vpath, m0.heavy, m0.seen,
           CASE WHEN t.protocol = {lit(Protocol.DNS.value)} THEN w.host
                WHEN t.protocol = {lit(Protocol.SSL.value)} THEN w.host || ':443'
                WHEN t.protocol = {lit(Protocol.NETWORK.value)} THEN w.host || ':' || w.port
                ELSE w.url || m0.vpath END AS matched OFFSET 0
  ) m
ON CONFLICT (scan_id, fingerprint) DO NOTHING
"""

SOFTWARE_CVES_SQL = f"""
INSERT INTO software_cves (
  id, scan_id, target_id, project_id, fingerprint, cve, name, version, vendor, product, cpe,
  version_source, severity, cvss_score, epss_score, epss_percentile, is_kev, kev_ransomware,
  kev_due_date, exploit_score, intel_kinds, confidence, caveats, host, ip, port, url,
  http_asset_id, discovered_at, created_at, evidence)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid,
       md5(c.cve || '|' || a.host || '|' || a.port || '|' || c.name || '|' || c.version),
       c.cve, left(c.name, 120), left(c.version, 64), c.vendor, c.product,
       'cpe:2.3:a:' || c.vendor || ':' || c.product || ':' || c.version || ':*:*:*:*:*:*:*',
       a.src,
       CASE WHEN c.severity IN ({lit(Severity.CRITICAL.value)}, {lit(Severity.HIGH.value)}, {lit(Severity.MEDIUM.value)},
                                {lit(Severity.LOW.value)}, {lit(Severity.INFO.value)}) THEN c.severity
            ELSE {lit(Severity.UNKNOWN.value)} END,
       c.cvss_score, c.epss, c.pct, c.kev, c.ransom, c.due,
       CASE WHEN c.kev THEN 90 ELSE floor(coalesce(c.epss, 0) * 40)::int END,
       CASE WHEN c.kev THEN json_build_array({lit(ExploitSignal.KEV.value)}) ELSE '[]'::json END,
       CASE WHEN a.src = {lit(VersionSource.BANNER.value)} THEN {lit(Confidence.HIGH.value)}
            WHEN pg_temp.u(a.host || c.cve) < 0.5 THEN {lit(Confidence.MEDIUM.value)}
            ELSE {lit(Confidence.LOW.value)} END,
       CASE WHEN a.src = {lit(VersionSource.BANNER.value)} THEN '[]'::json
            WHEN pg_temp.u(a.host || c.cve) < 0.5 THEN json_build_array({lit(Caveat.FINGERPRINT.value)})
            ELSE json_build_array({lit(Caveat.FINGERPRINT.value)}, {lit(Caveat.CONDITIONAL.value)}) END,
       a.host, a.ip, a.port, a.url, a.id, $5::timestamptz, $5::timestamptz,
       CASE WHEN pg_temp.u(a.host || c.cve || ':x') < 0.05 THEN {lit(Evidence.CROSS_CHECKED.value)}
            ELSE {lit(Evidence.INFERRED.value)} END
  FROM (
    SELECT w.*, sw ->> 'name' AS nm, sw ->> 'version' AS ver, sw ->> 'source' AS src
      FROM web w CROSS JOIN LATERAL json_array_elements(w.software) sw
  ) a
  JOIN swc c ON c.name = a.nm AND c.version = a.ver
             AND c.rn <= 1 + (pg_temp.hn(a.host || a.port) % 8)::int
 ORDER BY a.wkey, c.rn
 LIMIT $4::int
ON CONFLICT (scan_id, fingerprint) DO NOTHING
"""

SECRETS_SQL = f"""
INSERT INTO secrets (
  id, scan_id, target_id, project_id, fingerprint, kind, "group", vendor, state, is_secret,
  value, subject, meta, host, url, http_asset_id, source, context, sightings, hosts,
  discovered_at, created_at)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid,
       pg_temp.sha(d.key || ':' || x.value), d.key, d.grp, coalesce(d.vendor, ''),
       CASE WHEN d.public THEN {lit(SecretState.PUBLIC.value)}
            WHEN pg_temp.u(g.key || ':exp') < 0.1 THEN {lit(SecretState.EXPIRED.value)}
            ELSE {lit(SecretState.EXPOSED.value)} END,
       NOT d.public, x.value,
       CASE WHEN d.key = 'email' THEN split_part(x.value, '@', 2) END,
       CASE WHEN d.key = 'email' THEN json_build_object('domain', split_part(x.value, '@', 2)) ELSE '{{}}'::json END,
       w.host, w.url || (ARRAY['/static/js/app.js', '/', '/config.js', '/api/settings'])[1 + (pg_temp.hn(g.key) % 4)::int],
       w.id,
       (ARRAY[{lit(SecretSource.BODY.value)}, {lit(SecretSource.BODY.value)}, {lit(SecretSource.ENDPOINT_BODY.value)},
              {lit(SecretSource.HEADER.value)}, {lit(SecretSource.FINDING.value)}])[1 + (pg_temp.hn(g.key || ':src') % 5)::int],
       left('var config = {{ key: "' || x.value || '", region: "eu-west-1" }};', 1200),
       1 + (pg_temp.hn(g.key || ':sg') % 5)::int, 1 + (pg_temp.hn(g.key || ':hs') % 3)::int,
       $7::timestamptz + interval '5 hours', $7::timestamptz + interval '5 hours'
  FROM (
    SELECT n, $4::text || ':s' || n AS key,
           1 + floor(power(pg_temp.u($4::text || ':sd:' || n), 1.5) * $9::int)::int AS rn,
           floor($8::int * power(pg_temp.u($4::text || ':sh:' || n), 2))::int AS wkey
      FROM generate_series(1, $5::int) n
     WHERE (n::int8 * 7919 + $6::int8 * 104729) % {ENDPOINT_DROP_MOD} <> 0
  ) g
  JOIN det d ON d.rn = g.rn
  JOIN web w ON w.wkey = g.wkey
  CROSS JOIN LATERAL (
    SELECT CASE WHEN d.key = 'email' THEN 'staff' || (g.n % 400) || '@' || $10::text
                ELSE d.prefix || substr(upper(md5(g.key)) || md5(g.key || 'b'), 1, 36) END AS value OFFSET 0
  ) x
ON CONFLICT (scan_id, fingerprint) DO NOTHING
"""

POSTURE_SQL = f"""
INSERT INTO domain_posture (
  id, scan_id, target_id, project_id, zone, hosts, spf, spf_all, spf_lookups, dmarc,
  dmarc_policy, dmarc_subdomain_policy, dmarc_pct, dmarc_rua, dkim_selectors, dkim_key_bits, mx,
  null_mx, mta_sts, mta_sts_mode, tls_rpt, dnssec, caa, posture_issues, posture_checked,
  evidence, discovered_at, created_at, parent, dmarc_inherited)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, z.zone, z.hosts,
       CASE WHEN NOT (i ? {lit(PostureCheck.SPF_MISSING.value)}) THEN 'v=spf1 include:_spf.google.com '
              || CASE WHEN i ? {lit(PostureCheck.SPF_ANY_SENDER.value)} THEN '+all' WHEN i ? {lit(PostureCheck.SPF_SOFT_ALL.value)} THEN '~all' ELSE '-all' END END,
       CASE WHEN i ? {lit(PostureCheck.SPF_MISSING.value)} THEN {lit(SpfAll.ABSENT.value)} WHEN i ? {lit(PostureCheck.SPF_ANY_SENDER.value)} THEN {lit(SpfAll.PASS.value)}
            WHEN i ? {lit(PostureCheck.SPF_SOFT_ALL.value)} THEN {lit(SpfAll.SOFTFAIL.value)} ELSE {lit(SpfAll.FAIL.value)} END,
       CASE WHEN NOT (i ? {lit(PostureCheck.SPF_MISSING.value)}) THEN CASE WHEN i ? {lit(PostureCheck.SPF_LOOKUP_LIMIT.value)} THEN 12 ELSE 3 END END,
       CASE WHEN NOT (i ? {lit(PostureCheck.DMARC_MISSING.value)}) THEN 'v=DMARC1; p=' || CASE WHEN i ? {lit(PostureCheck.DMARC_NONE.value)} THEN 'none' ELSE 'reject' END END,
       CASE WHEN NOT (i ? {lit(PostureCheck.DMARC_MISSING.value)}) THEN CASE WHEN i ? {lit(PostureCheck.DMARC_NONE.value)} THEN 'none' ELSE 'reject' END END,
       CASE WHEN i ? {lit(PostureCheck.DMARC_SUBDOMAINS_OPEN.value)} THEN 'none' END,
       CASE WHEN i ? {lit(PostureCheck.DMARC_PARTIAL.value)} THEN 50 END,
       CASE WHEN NOT (i ? {lit(PostureCheck.DMARC_MISSING.value)}) THEN NOT (i ? {lit(PostureCheck.DMARC_NO_REPORTING.value)}) END,
       '[]'::json, NULL, json_build_array('mx1.' || z.zone, 'aspmx.l.google.com'), false,
       CASE WHEN NOT (i ? {lit(PostureCheck.MTA_STS_MISSING.value)}) THEN 'v=STSv1; id=20260101' END,
       CASE WHEN NOT (i ? {lit(PostureCheck.MTA_STS_MISSING.value)}) THEN CASE WHEN i ? {lit(PostureCheck.MTA_STS_NOT_ENFORCED.value)} THEN {lit(MtaStsMode.TESTING.value)} ELSE {lit(MtaStsMode.ENFORCE.value)} END END,
       CASE WHEN NOT (i ? {lit(PostureCheck.TLS_RPT_MISSING.value)}) THEN 'v=TLSRPTv1; rua=mailto:tls@' || z.zone END,
       CASE WHEN i ? {lit(PostureCheck.DNSSEC_BROKEN.value)} THEN {lit(DnssecState.BROKEN.value)}
            WHEN i ? {lit(PostureCheck.DNSSEC_MISSING.value)} THEN {lit(DnssecState.UNSIGNED.value)}
            ELSE {lit(DnssecState.SIGNED.value)} END,
       CASE WHEN i ? {lit(PostureCheck.CAA_MISSING.value)} THEN '[]'::json ELSE '["0 issue \\"letsencrypt.org\\""]'::json END,
       z.issues, z.checked, '{{}}'::json, $4::timestamptz, $4::timestamptz, NULL, false
  FROM (SELECT k.zone, k.hosts, pv.issues, pv.checked
          FROM zone_all k JOIN posture_var pv ON pv.v = pg_temp.hn(k.zone) % {VARIANTS}
         WHERE k.scan_id = $1::uuid) z
  CROSS JOIN LATERAL (SELECT z.issues::jsonb AS i OFFSET 0
  ) j
 ORDER BY z.zone
"""

SURFACE_SQL = f"""
WITH roots AS (
  SELECT h.id AS asset_id, h.url, h.host, h.port, h.scheme, w.subdomain_id,
         gen_random_uuid() AS item_id,
         count(*) OVER (PARTITION BY h.content_hash, h.status_code, h.title, h.port) AS size,
         row_number() OVER (PARTITION BY h.content_hash, h.status_code, h.title, h.port ORDER BY h.host) AS pos,
         md5(h.scan_id::text || h.content_hash || h.status_code || coalesce(h.title, '') || h.port)::uuid AS cluster_key
    FROM http_assets h LEFT JOIN web w ON w.id = h.id
   WHERE h.scan_id = $1::uuid
), ranked AS (
  SELECT r.*, first_value(r.item_id) OVER (PARTITION BY r.cluster_key ORDER BY r.pos) AS rep_id,
         pg_temp.u(r.url || ':state') AS x
    FROM roots r
)
INSERT INTO scan_surface_items (
  id, scan_id, target_id, project_id, class, value, host, port, scheme, http_asset_id,
  subdomain_id, cluster_id, representative_id, cluster_signals, members, drop_reason, rank,
  batch, guarded, tags, unmapped_tech, tiers_planned, tiers_done, state, created_at)
SELECT r.item_id, $1::uuid, $2::uuid, $3::uuid, {lit(SurfaceClass.ROOT.value)}, r.url, r.host,
       r.port, r.scheme, r.asset_id, r.subdomain_id,
       CASE WHEN r.size > 1 THEN r.cluster_key END,
       CASE WHEN r.pos > 1 THEN r.rep_id END,
       CASE WHEN r.size > 1 THEN json_build_array({lit(ClusterSignal.BODY.value)}, {lit(ClusterSignal.STATUS.value)}, {lit(ClusterSignal.TITLE.value)})
            ELSE '[]'::json END,
       CASE WHEN r.pos = 1 THEN r.size ELSE 1 END,
       CASE WHEN r.pos > 1 THEN {lit(DropReason.COVERED_BY_ORIGIN.value)}
            WHEN r.x >= 0.97 THEN {lit(DropReason.BUDGET.value)} END,
       round((1 - r.x)::numeric, 4)::float8, CASE WHEN r.pos = 1 THEN 1 + (pg_temp.hn(r.url) % 40)::int END,
       false, '[]'::json, '[]'::json,
       CASE WHEN r.pos > 1 THEN json_build_array({lit(Tier.ONE_REQUEST.value)})
            ELSE json_build_array({lit(Tier.ONE_REQUEST.value)}, {lit(Tier.UNIVERSAL.value)},
                                  {lit(Tier.MATCHED.value)}, {lit(Tier.BLIND.value)}) END,
       CASE WHEN r.pos > 1 THEN json_build_object({lit(Tier.ONE_REQUEST.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text)
            WHEN r.x < 0.90 THEN json_build_object(
                   {lit(Tier.ONE_REQUEST.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text,
                   {lit(Tier.UNIVERSAL.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text,
                   {lit(Tier.MATCHED.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text,
                   {lit(Tier.BLIND.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text)
            WHEN r.x < 0.97 THEN json_build_object(
                   {lit(Tier.ONE_REQUEST.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text,
                   {lit(Tier.UNIVERSAL.value)}, 'budget@' || $4::text)
            ELSE '{{}}'::json END,
       CASE WHEN r.pos > 1 THEN {lit(SurfaceState.COVERED.value)}
            WHEN r.x < 0.90 THEN {lit(SurfaceState.SCANNED.value)}
            WHEN r.x < 0.97 THEN {lit(SurfaceState.PARTIAL.value)}
            ELSE {lit(SurfaceState.NOT_SCANNED.value)} END,
       $5::timestamptz
  FROM ranked r
"""

SURFACE_NAMES_SQL = f"""
INSERT INTO scan_surface_items (
  id, scan_id, target_id, project_id, class, value, host, subdomain_id, cluster_signals,
  members, rank, guarded, tags, unmapped_tech, tiers_planned, tiers_done, state, created_at)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, {lit(SurfaceClass.NAME.value)}, s.name,
       s.name, s.id, '[]'::json, 1, 0, false, '[]'::json, '[]'::json,
       json_build_array({lit(Tier.NAMES.value)}),
       json_build_object({lit(Tier.NAMES.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text),
       {lit(SurfaceState.SCANNED.value)}, $5::timestamptz
  FROM subdomains s WHERE s.scan_id = $1::uuid AND s.is_active AND s.http_status IS NULL
"""

SURFACE_SERVICES_SQL = f"""
INSERT INTO scan_surface_items (
  id, scan_id, target_id, project_id, class, value, host, port, port_id, cluster_signals,
  members, rank, guarded, tags, unmapped_tech, tiers_planned, tiers_done, state, created_at)
SELECT gen_random_uuid(), $1::uuid, $2::uuid, $3::uuid, {lit(SurfaceClass.SERVICE.value)},
       p.ip || ':' || p.number, p.ip, p.number, p.id, '[]'::json, 1, 0, false, '[]'::json, '[]'::json,
       json_build_array({lit(Tier.SERVICES.value)}),
       json_build_object({lit(Tier.SERVICES.value)}, {lit(CoverageStatus.COMPLETED.value)} || '@' || $4::text),
       {lit(SurfaceState.SCANNED.value)}, $5::timestamptz
  FROM ports p WHERE p.scan_id = $1::uuid AND NOT p.is_http
"""

COUNTERS_SQL = """
UPDATE scans s SET
  subdomains_found = (SELECT count(*) FROM subdomains x WHERE x.scan_id = s.id),
  ips_found = (SELECT count(*) FROM ip_addresses x WHERE x.scan_id = s.id),
  open_ports_found = (SELECT count(*) FROM ports x WHERE x.scan_id = s.id),
  vulnerabilities_found = (SELECT count(*) FROM vulnerabilities x WHERE x.scan_id = s.id),
  endpoints_found = (SELECT count(*) FROM endpoints x WHERE x.scan_id = s.id),
  http_assets_found = (SELECT count(*) FROM http_assets x WHERE x.scan_id = s.id),
  secrets_found = (SELECT count(*) FROM secrets x WHERE x.scan_id = s.id)
 WHERE s.project_id = $1::uuid
"""


# ---------- seeding ----------


def dsn() -> str:
    return base_settings().database_url_async.replace(
        "postgresql+asyncpg://", "postgresql://"
    )


async def project_id_of(conn: asyncpg.Connection, name: str) -> uuid.UUID | None:
    return await conn.fetchval("SELECT id FROM projects WHERE name = $1", name)


async def prepare_session(conn: asyncpg.Connection) -> None:
    await conn.execute(session_sql())
    await conn.executemany(
        "INSERT INTO paths VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
        path_templates(),
    )
    await conn.executemany(
        "INSERT INTO psets VALUES ($1, $2, $3, $4, $5, $6, $7)", param_sets()
    )
    await conn.executemany(
        "INSERT INTO port_catalog VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        port_catalog(),
    )
    await conn.executemany(
        "INSERT INTO det VALUES ($1, $2, $3, $4, $5, $6)",
        [
            (rn, d.key, d.vendor, d.group, d.public, SECRET_PREFIXES.get(d.key, ""))
            for rn, d in enumerate(DETECTORS, start=1)
        ],
    )
    await conn.executemany(
        "INSERT INTO swp VALUES ($1, $2, $3, $4)", software_products()
    )
    await conn.execute(TEMPLATES_SQL)
    await conn.execute(SOFTWARE_SQL)
    await conn.execute(
        "ANALYZE paths; ANALYZE psets; ANALYZE tpl; ANALYZE swc; ANALYZE det"
    )


async def insert_header(
    conn: asyncpg.Connection,
    name: str,
    creator: uuid.UUID,
    targets: list[TargetPlan],
    scans: list[ScanPlan],
    now: datetime,
) -> uuid.UUID:
    from shared.utils.crypto import encrypt_secret  # noqa: PLC0415

    project = uuid.uuid4()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "stress"
    if await conn.fetchval("SELECT 1 FROM projects WHERE slug = $1", slug):
        slug = f"{slug}-{project.hex[:6]}"
    await conn.execute(
        "INSERT INTO projects (id, name, slug, is_active, created_at, created_by, description) "
        "VALUES ($1, $2, $3, true, $4, $5, $6)",
        project,
        name,
        slug,
        now - timedelta(days=90),
        creator,
        "Synthetic estate for query profiling",
    )
    engine = uuid.uuid4()
    stages = {stage: {"enabled": True} for stage in SCANNED_STAGES}
    await conn.execute(
        "INSERT INTO scan_engines (id, project_id, created_by, name, intensity, global_headers, "
        "created_at, updated_at, tool_options, stages, builtin, transport_overrides) "
        "VALUES ($1, $2, $3, 'Stress census', $4, $5, $6, $6, $7, $8::json, false, '{}'::json)",
        engine,
        project,
        creator,
        Intensity.NORMAL.value,
        encrypt_secret(json.dumps([])),
        now - timedelta(days=90),
        encrypt_secret(json.dumps({})),
        json.dumps(stages),
    )
    skipped = TaskStatus.SKIPPED.name
    configs: dict[str, dict] = {}
    for plan in targets:
        if plan.kind not in configs:
            configs[plan.kind] = execution_config(plan)
        plan.config = {**configs[plan.kind], "target_value": plan.value}
        whois = TaskStatus.NOT_APPLICABLE.name if plan.network else skipped
        await conn.execute(
            "INSERT INTO targets (id, target_value, display_name, target_type, project_id, "
            "created_at, updated_at, created_by, whois_status, bgp_status, dns_status, "
            "infostealer_status, seed_scans, new_checks) "
            "VALUES ($1, $2, $3, $4::targettype, $5, $6, $6, $7, $8::taskstatus, $9::taskstatus, "
            "$9::taskstatus, $9::taskstatus, true, false)",
            plan.id,
            plan.value,
            plan.brand.title() if plan.kind == TargetType.DOMAIN.value else None,
            TargetType(plan.kind).name,
            project,
            now - timedelta(days=89),
            creator,
            whois,
            skipped,
        )
    for scan in scans:
        await insert_scan(conn, project, engine, creator, scan)
        await insert_activities(conn, project, scan)
    return project


async def insert_scan(
    conn: asyncpg.Connection,
    project: uuid.UUID,
    engine: uuid.UUID,
    creator: uuid.UUID,
    scan: ScanPlan,
) -> None:
    await conn.execute(
        "INSERT INTO scans (id, project_id, target_id, engine_id, engine_name, "
        "execution_config, status, subdomains_found, ips_found, open_ports_found, "
        "vulnerabilities_found, endpoints_found, created_by, created_at, started_at, "
        "completed_at, celery_task_ids, scope, run_epoch, paused_seconds) "
        "VALUES ($1, $2, $3, $4, 'Stress census', $5::json, $6, 0, 0, 0, 0, 0, $7, $8, $8, "
        "$9, '[]'::json, $10, 0, 0)",
        scan.id,
        project,
        scan.target.id,
        engine,
        json.dumps(scan.target.config),
        scan.status,
        creator,
        scan.started,
        scan.completed,
        ScanScope.FULL.value,
    )


async def insert_activities(
    conn: asyncpg.Connection, project: uuid.UUID, scan: ScanPlan
) -> None:
    from stages.registry import stages as stage_specs  # noqa: PLC0415

    titles = {spec.name: spec.title for spec in stage_specs()}
    rows = []
    if scan.census:
        names = stage_list(scan.target)
        span = (scan.completed - scan.started) / (len(names) + 1)
        for index, name in enumerate(names):
            begin = scan.started + span * index
            rows.append(
                (
                    name,
                    ScanActivityStatus.SUCCESS.value,
                    begin,
                    begin + span,
                    begin,
                    str(uuid.uuid4()),
                )
            )
    else:
        for index, name in enumerate(RUNNING_DONE):
            begin = scan.started + timedelta(minutes=5 * index)
            rows.append(
                (
                    name,
                    ScanActivityStatus.SUCCESS.value,
                    begin,
                    begin + timedelta(minutes=4),
                    begin,
                    str(uuid.uuid4()),
                )
            )
        begin = scan.started + timedelta(minutes=30)
        rows.append(
            (
                RUNNING_NOW,
                ScanActivityStatus.RUNNING.value,
                begin,
                None,
                begin,
                str(uuid.uuid4()),
            )
        )
        guard = datetime.now(UTC) + timedelta(days=STALL_GUARD_DAYS)
        rows.append(
            (RUNNING_QUEUED, ScanActivityStatus.PENDING.value, None, None, guard, None)
        )
    await conn.executemany(
        "INSERT INTO scan_activities (id, scan_id, project_id, name, title, status, "
        "celery_task_id, result, started_at, completed_at, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, '{}'::json, $8, $9, $10)",
        [
            (
                uuid.uuid4(),
                scan.id,
                project,
                name,
                titles.get(name, name),
                status,
                task,
                a,
                b,
                c,
            )
            for name, status, a, b, c, task in rows
        ],
    )


def count_of(status: str) -> int:
    parts = status.split()
    return int(parts[-1]) if parts and parts[-1].isdigit() else 0


TIMINGS: dict[str, float] = {}
SQL_NAMES: dict[str, str] = {}


async def chunked(ex, sql: str, args: tuple, total: int, lo_first: bool = False) -> int:
    rows = 0
    for lo in range(0, total, CHUNK):
        hi = min(total, lo + CHUNK)
        bounds = (lo + 1, hi) if lo_first else (lo, hi)
        if lo_first:
            status = await ex(sql, *args[:4], hi, *args[5:], bounds[0])
        else:
            status = await ex(sql, *args, *bounds)
        rows += count_of(status)
    return rows


def executor(conn: asyncpg.Connection):
    async def ex(sql: str, *args) -> str:
        tick = time.monotonic()
        status = await conn.execute(sql, *args)
        label = SQL_NAMES.get(sql, sql.split()[0])
        TIMINGS[label] = TIMINGS.get(label, 0.0) + time.monotonic() - tick
        return status

    return ex


async def seed_primary(
    conn: asyncpg.Connection, project: uuid.UUID, scan: ScanPlan, stats: dict[str, int]
) -> int:
    plan = scan.target
    base = (scan.id, plan.id, project)
    started = scan.started
    probe = scan.census
    ex = executor(conn)

    def add(table: str, count: int) -> None:
        stats[table] = stats.get(table, 0) + count

    await ex("TRUNCATE sub_k; TRUNCATE web")
    if plan.network:
        live = max(1, round(plan.addresses * scan.fraction))
        add(
            "ip_addresses",
            count_of(
                await ex(IP_FROM_RANGE_SQL, *base, live, plan.octet, scan.run, started)
            ),
        )
        add("ports", count_of(await ex(PORTS_FROM_CATALOG_SQL, *base)))
        add("http_assets", count_of(await ex(HTTP_FROM_PORTS_SQL, *base)))
        await ex(WEB_FROM_ASSETS_SQL, scan.id)
        width = await conn.fetchval("SELECT count(*) FROM web")
    else:
        names = max(1, round(plan.names * scan.fraction))
        await ex(
            SUB_K_SQL,
            str(scan.id),
            plan.seed,
            names,
            scan.run,
            started,
            plan.zones,
            plan.apex,
            plan.brand,
            plan.apex
            if plan.kind == TargetType.DOMAIN.value
            else plan.apex.split(".", 1)[1],
            plan.number,
            probe,
            plan.pool,
        )
        await ex(SUB_K_BANDS_SQL)
        await ex("ANALYZE sub_k")
        add("subdomains", await chunked(ex, SUBDOMAINS_SQL, base, names))
        add("ip_addresses", count_of(await ex(IP_FROM_NAMES_SQL, *base)))
        if not probe:
            return 0
        add(
            "http_assets",
            await chunked(
                ex,
                HTTP_ASSETS_SQL,
                (*base, plan.brand, AI_SERVICE.category, AI_SERVICE.key),
                names,
            ),
        )
        add("ports", count_of(await ex(PORTS_FROM_WEB_SQL, *base)))
        add("ports", count_of(await ex(PORTS_FROM_CATALOG_SQL, *base)))
        await ex(WEB_FROM_NAMES_SQL)
        width = plan.web_names
    await ex("ANALYZE web")
    if not width:
        return 0
    endpoints = max(1, round(plan.endpoints * scan.fraction))
    add(
        "endpoints",
        await chunked(
            ex,
            ENDPOINTS_SQL,
            (*base, plan.seed, endpoints, scan.run, started, width),
            endpoints,
            True,
        ),
    )
    findings = max(1, round(plan.findings * scan.fraction))
    add(
        "vulnerabilities",
        await chunked(
            ex,
            VULNS_SQL,
            (*base, plan.seed, findings, scan.run, started, width),
            findings,
            True,
        ),
    )
    return width


async def seed_secondary(
    conn: asyncpg.Connection, project: uuid.UUID, scan: ScanPlan, stats: dict[str, int]
) -> None:
    plan = scan.target
    base = (scan.id, plan.id, project)
    started = scan.started
    ex = executor(conn)

    def add(table: str, status: str) -> None:
        stats[table] = stats.get(table, 0) + count_of(status)

    if not scan.census:
        return
    await ex("TRUNCATE web; TRUNCATE zone_all")
    await ex(WEB_FROM_DB_SQL, scan.id)
    await ex("ANALYZE web")
    width = await conn.fetchval("SELECT count(*) FROM web")
    if not width:
        return
    if not plan.network:
        zone = (
            plan.apex
            if plan.kind == TargetType.DOMAIN.value
            else plan.apex.split(".", 1)[1]
        )
        await ex(ZONES_SQL, scan.id, zone)
    add("endpoint_responses", await ex(ENDPOINT_RESPONSES_SQL, scan.id))
    secrets = max(1, round(plan.secrets * scan.fraction))
    add(
        "secrets",
        await ex(
            SECRETS_SQL,
            *base,
            plan.seed,
            secrets,
            scan.run,
            started,
            width,
            len(DETECTORS),
            plan.apex or f"{plan.brand}-stress.example",
        ),
    )
    software = max(1, round(plan.software * scan.fraction))
    add(
        "software_cves",
        await ex(
            SOFTWARE_CVES_SQL, *base, software, scan.completed - timedelta(minutes=5)
        ),
    )
    if not plan.network:
        add(
            "domain_posture",
            await ex(POSTURE_SQL, *base, started + timedelta(minutes=50)),
        )
    if scan.run == CENSUS_RUNS:
        stamp = scan.completed.isoformat()
        created = scan.started + timedelta(hours=1)
        for sql in (SURFACE_SQL, SURFACE_NAMES_SQL, SURFACE_SERVICES_SQL):
            add("scan_surface_items", await ex(sql, *base, stamp, created))


def progress(index: int, total: int, scan: ScanPlan, tick: float, clock: float) -> None:
    print(
        f"[{index}/{total}] {scan.target.value} run {scan.run} "
        f"{time.monotonic() - tick:.1f}s (total {time.monotonic() - clock:.0f}s)",
        flush=True,
    )


async def seed(conn: asyncpg.Connection, name: str, scale: float) -> uuid.UUID:
    if await project_id_of(conn, name):
        msg = f"Project {name!r} exists. Run with --wipe first."
        raise SystemExit(msg)
    creator = await conn.fetchval(
        "SELECT id FROM users WHERE is_active ORDER BY is_superuser DESC, created_at LIMIT 1"
    )
    if creator is None:
        msg = "No user exists. Complete onboarding first."
        raise SystemExit(msg)
    now = datetime.now(UTC)
    targets = build_targets(scale)
    scans = build_scans(targets, now)
    clock = time.monotonic()
    SQL_NAMES.update(
        {
            v: k
            for k, v in globals().items()
            if k.endswith("_SQL") and isinstance(v, str)
        }
    )
    await prepare_session(conn)
    print(f"session prepared in {time.monotonic() - clock:.0f}s", flush=True)
    async with conn.transaction():
        project = await insert_header(conn, name, creator, targets, scans, now)
    print(
        f"project {project} with {len(targets)} targets and {len(scans)} scans",
        flush=True,
    )
    stats: dict[str, int] = {}
    for index, scan in enumerate(scans, start=1):
        tick = time.monotonic()
        await seed_primary(conn, project, scan, stats)
        progress(index, len(scans), scan, tick, clock)
    for table in PRIMARY_TABLES:
        await conn.execute(f"ANALYZE {table}")
    print(
        f"primary tables loaded in {time.monotonic() - clock:.0f}s {stats}", flush=True
    )
    for index, scan in enumerate(scans, start=1):
        tick = time.monotonic()
        await seed_secondary(conn, project, scan, stats)
        progress(index, len(scans), scan, tick, clock)
    print(f"rows {stats}", flush=True)
    await finish(conn, project, clock)
    return project


async def finish(conn: asyncpg.Connection, project: uuid.UUID, clock: float) -> None:
    await conn.execute(COUNTERS_SQL, project)
    for table in RESULT_TABLES:
        await conn.execute(f"ANALYZE {table}")
    await conn.execute("ANALYZE scans; ANALYZE targets")
    await conn.execute("SELECT pg_stat_statements_reset()")
    print(f"seeded in {time.monotonic() - clock:.0f}s", flush=True)
    for label, spent in sorted(TIMINGS.items(), key=lambda item: -item[1]):
        print(f"  {label}: {spent:.0f}s", flush=True)


async def resume(conn: asyncpg.Connection, name: str, scale: float) -> None:
    project = await project_id_of(conn, name)
    if project is None:
        msg = f"No project named {name!r}."
        raise SystemExit(msg)
    clock = time.monotonic()
    SQL_NAMES.update(
        {
            v: k
            for k, v in globals().items()
            if k.endswith("_SQL") and isinstance(v, str)
        }
    )
    await prepare_session(conn)
    plans = {plan.value: plan for plan in build_targets(scale)}
    for row in await conn.fetch(
        "SELECT id, target_value FROM targets WHERE project_id = $1", project
    ):
        plans[row["target_value"]].id = row["id"]
    rows = await conn.fetch(
        "SELECT s.id, s.status, s.started_at, s.completed_at, t.target_value FROM scans s "
        "JOIN targets t ON t.id = s.target_id WHERE s.project_id = $1 "
        "ORDER BY t.target_value, s.started_at",
        project,
    )
    scans: list[ScanPlan] = []
    runs: dict[str, int] = {}
    for row in rows:
        plan = plans[row["target_value"]]
        if row["status"] != ScanStatus.COMPLETED.value:
            continue
        run = runs[plan.value] = runs.get(plan.value, 0) + 1
        scans.append(
            ScanPlan(
                target=plan,
                run=run,
                fraction=RUN_FRACTIONS[run - 1],
                started=row["started_at"],
                completed=row["completed_at"],
                status=row["status"],
                id=row["id"],
            )
        )
    stats: dict[str, int] = {}
    running = build_scans(list(plans.values()), datetime.now(UTC))[-1]
    if not any(r["status"] == ScanStatus.RUNNING.value for r in rows):
        engine = await conn.fetchval(
            "SELECT id FROM scan_engines WHERE project_id = $1 LIMIT 1", project
        )
        creator = await conn.fetchval(
            "SELECT created_by FROM projects WHERE id = $1", project
        )
        running.target.config = execution_config(running.target)
        async with conn.transaction():
            await insert_scan(conn, project, engine, creator, running)
            await insert_activities(conn, project, running)
        await seed_primary(conn, project, running, stats)
        print(f"running scan {running.id} added", flush=True)
    done = {
        r["scan_id"]
        for r in await conn.fetch(
            "SELECT DISTINCT scan_id FROM secrets WHERE project_id = $1", project
        )
    }
    pending = [scan for scan in scans if scan.id not in done]
    for index, scan in enumerate(pending, start=1):
        tick = time.monotonic()
        await seed_secondary(conn, project, scan, stats)
        progress(index, len(pending), scan, tick, clock)
    print(f"rows {stats}", flush=True)
    await finish(conn, project, clock)


# ---------- wipe ----------

WIPE_ATTEMPTS = 5
WIPE_FIRST = (
    "endpoint_responses",
    "scan_surface_items",
    "endpoints",
    "vulnerabilities",
    "software_cves",
    "secrets",
    "http_assets",
    "ports",
    "ip_addresses",
    "subdomains",
    "domain_posture",
    "scan_activities",
)


async def retrying(conn: asyncpg.Connection, sql: str, *args) -> str:
    for attempt in range(WIPE_ATTEMPTS):
        try:
            return await conn.execute(sql, *args)
        except asyncpg.DeadlockDetectedError:
            if attempt == WIPE_ATTEMPTS - 1:
                raise
            await asyncio.sleep(2)
    return ""


async def wipe(conn: asyncpg.Connection, name: str) -> None:
    project = await project_id_of(conn, name)
    if project is None:
        print(f"no project named {name!r}")
        return
    clock = time.monotonic()
    for table in WIPE_FIRST:
        if table == "endpoint_responses":
            sql = (
                "DELETE FROM endpoint_responses WHERE scan_id IN "
                "(SELECT id FROM scans WHERE project_id = $1)"
            )
        else:
            sql = f"DELETE FROM {table} WHERE project_id = $1"
        status = await retrying(conn, sql, project)
        print(f"{table}: {count_of(status)} rows removed", flush=True)
    children = await conn.fetch(
        """
        SELECT c.conrelid::regclass::text AS tbl, a.attname AS col
          FROM pg_constraint c
          JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
         WHERE c.contype = 'f' AND c.confrelid = 'projects'::regclass
        """
    )
    pending = [(row["tbl"], row["col"]) for row in children]
    while pending:
        left = []
        for table, column in pending:
            try:
                async with conn.transaction():
                    await conn.execute(
                        f'DELETE FROM {table} WHERE "{column}" = $1', project
                    )
            except asyncpg.ForeignKeyViolationError:
                left.append((table, column))
        if len(left) == len(pending):
            msg = f"Could not remove rows from {', '.join(t for t, _ in left)}."
            raise SystemExit(msg)
        pending = left
    await conn.execute("DELETE FROM projects WHERE id = $1", project)
    print(f"project {project} removed in {time.monotonic() - clock:.0f}s", flush=True)


# ---------- verify ----------


async def verify(conn: asyncpg.Connection, name: str) -> None:
    project = await project_id_of(conn, name)
    if project is None:
        print(f"no project named {name!r}")
        return
    print(f"project {project}")
    for table in RESULT_TABLES:
        if table in {"endpoint_responses", "scan_revisions"}:
            sql = f"SELECT count(*) FROM {table} WHERE scan_id IN (SELECT id FROM scans WHERE project_id = $1)"
        else:
            sql = f"SELECT count(*) FROM {table} WHERE project_id = $1"
        print(f"  {table}: {await conn.fetchval(sql, project):,}")
    newest = await conn.fetchrow(
        "SELECT s.id, s.target_id FROM scans s JOIN targets t ON t.id = s.target_id "
        "WHERE s.project_id = $1 AND s.status = $2 ORDER BY s.subdomains_found DESC, "
        "s.started_at DESC LIMIT 1",
        project,
        ScanStatus.COMPLETED.value,
    )
    expected = await conn.fetchval(
        """
        SELECT count(*) FROM subdomains s
         WHERE s.scan_id = $1 AND NOT EXISTS (
           SELECT 1 FROM subdomains e JOIN scans p ON p.id = e.scan_id
            WHERE e.target_id = s.target_id AND e.name = s.name AND e.scan_id <> s.scan_id
              AND p.started_at < (SELECT started_at FROM scans WHERE id = $1))
        """,
        newest["id"],
    )
    compiled = await grammar_count(newest["id"], project)
    print(f"  is:new on scan {newest['id']}: grammar {compiled:,}, direct {expected:,}")
    print(f"  health: {await asyncio.to_thread(health)}")


def health() -> str:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=10) as response:  # noqa: S310
            return f"{response.status} {response.read()[:120].decode()}"
    except OSError as exc:
        return str(exc)


async def grammar_count(scan_id: uuid.UUID, project: uuid.UUID) -> int:
    from sqlalchemy import func, select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import create_async_engine  # noqa: PLC0415

    from shared.models.subdomain import Subdomain  # noqa: PLC0415
    from shared.services.asset_query import (  # noqa: PLC0415
        QueryContext,
        QueryScope,
        compile_query,
        parse_query,
    )

    scope = QueryScope((scan_id,), project)
    predicate = compile_query(
        parse_query("is:new"), QueryContext(scope=scope, now=datetime.now(UTC))
    )
    engine = create_async_engine(base_settings().database_url_async)
    try:
        async with engine.connect() as db:
            stmt = (
                select(func.count())
                .select_from(Subdomain)
                .where(scope.match(Subdomain.scan_id), predicate)
            )
            return int((await db.execute(stmt)).scalar_one())
    finally:
        await engine.dispose()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--wipe", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--project-name", default="Stress")
    args = parser.parse_args()
    conn = await asyncpg.connect(dsn())
    try:
        await conn.execute("SET statement_timeout = 0")
        if args.wipe:
            await wipe(conn, args.project_name)
        elif args.resume:
            await resume(conn, args.project_name, args.scale)
            await verify(conn, args.project_name)
        elif args.verify:
            await verify(conn, args.project_name)
        else:
            await seed(conn, args.project_name, args.scale)
            await verify(conn, args.project_name)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
