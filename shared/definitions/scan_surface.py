"""What a vulnerability scanner is handed: input classes, origin clusters, tiers and their labels."""

from __future__ import annotations

import re
from enum import StrEnum

from shared.definitions.correlation import MIN_BODY_BYTES


class SurfaceClass(StrEnum):
    ROOT = "root"
    NAME = "name"
    SERVICE = "service"
    BASE = "base"
    REQUEST = "request"


SURFACE_CLASS_LABELS: dict[str, str] = {
    SurfaceClass.ROOT.value: "Site root",
    SurfaceClass.NAME.value: "Hostname",
    SurfaceClass.SERVICE.value: "Network service",
    SurfaceClass.BASE.value: "Directory",
    SurfaceClass.REQUEST.value: "Request",
}

SURFACE_CLASS_HELP: dict[str, str] = {
    SurfaceClass.ROOT.value: "One per web asset, any status. HTTP checks run here.",
    SurfaceClass.NAME.value: "One per resolved name. DNS checks run here.",
    SurfaceClass.SERVICE.value: "One per open port. TLS and network checks run here.",
    SurfaceClass.BASE.value: "One per directory. Exposure checks run here.",
    SurfaceClass.REQUEST.value: "One per parameter set. Fuzzing runs here.",
}


class DropReason(StrEnum):
    OUT_OF_SCOPE = "out_of_scope"
    DUPLICATE_SPELLING = "duplicate_spelling"
    COVERED_BY_ORIGIN = "covered_by_origin"
    NO_ANSWER = "no_answer"
    CANARY_MATCH = "canary_match"
    BUDGET = "budget"
    OVER_CAP = "over_cap"


DROP_REASON_LABELS: dict[str, str] = {
    DropReason.OUT_OF_SCOPE.value: "Excluded by the scan context",
    DropReason.DUPLICATE_SPELLING.value: "Same target, another spelling",
    DropReason.COVERED_BY_ORIGIN.value: "Covered by an equivalent web asset",
    DropReason.NO_ANSWER.value: "Did not answer",
    DropReason.CANARY_MATCH.value: "Answers like a missing page",
    DropReason.BUDGET.value: "Not reached within the time budget",
    DropReason.OVER_CAP.value: "Over the target budget",
}


class ClusterSignal(StrEnum):
    ADDRESS = "address"
    CERTIFICATE = "certificate"
    BODY = "body"
    SHAPE = "shape"
    STATUS = "status"
    TITLE = "title"
    CANARY = "canary"
    FAVICON = "favicon"


CLUSTER_SIGNAL_LABELS: dict[str, str] = {
    ClusterSignal.ADDRESS.value: "Same address",
    ClusterSignal.CERTIFICATE.value: "Same certificate",
    ClusterSignal.BODY.value: "Same body",
    ClusterSignal.SHAPE.value: "Same response shape",
    ClusterSignal.STATUS.value: "Same status",
    ClusterSignal.TITLE.value: "Same title",
    ClusterSignal.CANARY.value: "Same missing-page answer",
    ClusterSignal.FAVICON.value: "Same favicon",
}


class Tier(StrEnum):
    ONE_REQUEST = "one_request"
    UNIVERSAL = "universal"
    MATCHED = "matched"
    BLIND = "blind"
    SERVICES = "services"
    NAMES = "names"
    REPLAY = "replay"
    DAST = "dast"
    BASES = "bases"


TIER_ORDER: tuple[str, ...] = (
    Tier.ONE_REQUEST.value,
    Tier.UNIVERSAL.value,
    Tier.SERVICES.value,
    Tier.NAMES.value,
    Tier.MATCHED.value,
    Tier.BLIND.value,
    Tier.REPLAY.value,
    Tier.DAST.value,
    Tier.BASES.value,
)

TIER_LABELS: dict[str, str] = {
    Tier.ONE_REQUEST.value: "One-request checks",
    Tier.UNIVERSAL.value: "Universal checks",
    Tier.MATCHED.value: "Checks for detected software",
    Tier.BLIND.value: "Remaining checks",
    Tier.SERVICES.value: "TLS and network checks",
    Tier.NAMES.value: "DNS checks",
    Tier.REPLAY.value: "Confirmation on equivalent web assets",
    Tier.DAST.value: "Fuzzing",
    Tier.BASES.value: "Directory exposure checks",
}

TIER_HELP: dict[str, str] = {
    Tier.ONE_REQUEST.value: "Root-page checks on every web asset. At most ten requests each.",
    Tier.UNIVERSAL.value: "Checks for any web server. One web asset per origin.",
    Tier.MATCHED.value: "Checks for the software the web asset was seen running.",
    Tier.BLIND.value: "Checks for software not detected on the web asset. Runs last.",
    Tier.SERVICES.value: "Certificate and protocol checks on open ports.",
    Tier.NAMES.value: "Record-level checks on resolved names.",
    Tier.REPLAY.value: "A finding re-run against each web asset the origin stands for.",
    Tier.DAST.value: "Parameter fuzzing on discovered requests.",
    Tier.BASES.value: "Exposure checks under each discovered directory.",
}

# tiers a root web asset can be planned for
ROOT_TIERS: tuple[str, ...] = (
    Tier.ONE_REQUEST.value,
    Tier.UNIVERSAL.value,
    Tier.MATCHED.value,
    Tier.BLIND.value,
)


class SurfaceState(StrEnum):
    PLANNED = "planned"
    SCANNED = "scanned"
    PARTIAL = "partial"
    COVERED = "covered"
    NOT_SCANNED = "not_scanned"


SURFACE_STATE_LABELS: dict[str, str] = {
    SurfaceState.PLANNED.value: "Planned",
    SurfaceState.SCANNED.value: "Scanned",
    SurfaceState.PARTIAL.value: "Partly scanned",
    SurfaceState.COVERED.value: "Covered by an equivalent web asset",
    SurfaceState.NOT_SCANNED.value: "Not scanned",
}

# ---------- thresholds ----------

# one batch is one scanner invocation; the time cut lands between batches
BATCH_SECONDS = 600
BATCH_MIN_HOSTS = 3
BATCH_MAX_HOSTS = 250
# a batch may run this much longer than planned before it is cut
BATCH_OVERRUN = 1.5
# tier 0 is the top paths of the library, one request each
ONE_REQUEST_PATHS = 10
# tech groups share one invocation; the rest fold into one mixed group
MAX_TECH_GROUPS = 12
# a request item is one per parameter set, capped per origin and per scan
MAX_REQUESTS_PER_ORIGIN = 50
MAX_REQUESTS = 1500
MAX_BASES_PER_ORIGIN = 10
BASE_MAX_DEPTH = 1
# replay is bounded by findings times members
MAX_REPLAY_TARGETS = 2000
BODY_IDENTITY_BYTES = MIN_BODY_BYTES

# ---------- template tiers ----------

# tags that name a class of check rather than a product
GENERIC_TAGS: frozenset[str] = frozenset(
    {
        "cve",
        "kev",
        "exposure",
        "exposures",
        "misconfig",
        "misconfiguration",
        "panel",
        "login",
        "default-login",
        "takeover",
        "config",
        "backup",
        "backups",
        "file",
        "files",
        "disclosure",
        "token",
        "tokens",
        "tech",
        "detect",
        "fingerprint",
        "unauth",
        "auth-bypass",
        "xss",
        "sqli",
        "rce",
        "lfi",
        "rfi",
        "ssrf",
        "ssti",
        "xxe",
        "csrf",
        "idor",
        "injection",
        "traversal",
        "redirect",
        "deserialization",
        "upload",
        "intrusive",
        "osint",
        "cloud",
        "network",
        "dns",
        "ssl",
        "tls",
        "headless",
        "dast",
        "fuzz",
        "fuzzing",
        "iot",
        "router",
        "camera",
        "oast",
        "top-10",
        "generic",
        "medium",
        "high",
        "critical",
        "low",
        "info",
        "vuln",
        "vulnerability",
        "enum",
        "bruteforce",
        "dos",
        "local",
        "creds-stuffing",
        "token-spray",
        "js",
        "javascript",
        "tcp",
        "smb",
        "ftp",
        "ssh",
        "smtp",
        "rdp",
        "mail",
        "api",
        "graphql",
        "swagger",
        "jwt",
        "cache",
        "crlf",
        "header",
        "headers",
        "cors",
        "waf",
        "ddos",
        "spring",
        "wp-plugin",
        "wp-theme",
        "wordpress",
        "wpscan",
        "cms",
        "ecommerce",
        "devops",
        "docker",
        "kubernetes",
        "k8s",
        "aws",
        "azure",
        "gcp",
        "s3",
        "bucket",
        "storage",
        "miscellaneous",
        "misc",
        "default",
        "hackerone",
        "edb",
        "packetstorm",
        "seclists",
        "cisa",
        "vulhub",
        "cnvd",
        "xray",
        "sast",
        "web",
        "http",
    }
)

_YEAR_TAG = re.compile(r"^(cve|cnvd|cwe)-?\d{4}$")

# universal checks apply to any web server
UNIVERSAL_TAGS: frozenset[str] = frozenset(
    {
        "exposure",
        "exposures",
        "misconfig",
        "misconfiguration",
        "default-login",
        "panel",
        "login",
        "takeover",
        "config",
        "backup",
        "backups",
        "file",
        "files",
        "disclosure",
        "token",
        "tokens",
        "tech",
        "detect",
        "fingerprint",
        "unauth",
        "auth-bypass",
        "cors",
        "crlf",
        "cache",
        "headers",
        "redirect",
    }
)

# product tags that stay product-specific even though they are in GENERIC_TAGS
PRODUCT_FAMILIES: frozenset[str] = frozenset(
    {"wordpress", "wp-plugin", "wp-theme", "spring", "docker", "kubernetes", "k8s"}
)


def is_generic_tag(tag: str) -> bool:
    value = tag.strip().lower()
    if value in PRODUCT_FAMILIES:
        return False
    return value in GENERIC_TAGS or bool(_YEAR_TAG.match(value))


def product_tags(tags) -> frozenset[str]:
    """The tags on a check that name a product."""
    return frozenset(
        t.strip().lower() for t in tags or () if t and not is_generic_tag(t)
    )


def is_universal(tags) -> bool:
    lowered = {t.strip().lower() for t in tags or () if t}
    return bool(lowered & UNIVERSAL_TAGS) and not product_tags(lowered)


# ---------- what a web asset was seen running, as template tags ----------

# httpx and Server-header names that do not normalise to their tag
TECH_ALIASES: dict[str, tuple[str, ...]] = {
    "apache": ("apache",),
    "apache http server": ("apache",),
    "apache httpd": ("apache",),
    "apache tomcat": ("tomcat",),
    "tomcat": ("tomcat",),
    "microsoft iis": ("iis",),
    "microsoft-iis": ("iis",),
    "microsoft iis httpd": ("iis",),
    "iis": ("iis",),
    "microsoft asp.net": ("aspnet", "asp", "dotnet"),
    "asp.net": ("aspnet", "asp", "dotnet"),
    "microsoft httpapi": (),
    "microsoft-httpapi": (),
    "microsoft sharepoint": ("sharepoint",),
    "microsoft exchange server": ("exchange", "owa"),
    "outlook web app": ("owa", "exchange"),
    "nodejs": ("nodejs", "node"),
    "ruby on rails": ("rails", "ruby"),
    "amazon web services": ("aws",),
    "amazon s3": ("s3", "aws"),
    "amazon cloudfront": ("cloudfront", "aws"),
    "atlassian jira": ("jira", "atlassian"),
    "atlassian confluence": ("confluence", "atlassian"),
    "atlassian bitbucket": ("bitbucket", "atlassian"),
    "f5 big-ip": ("bigip", "f5"),
    "big-ip": ("bigip", "f5"),
    "pulse secure": ("pulsesecure", "pulse"),
    "pulse connect secure": ("pulsesecure", "pulse"),
    "fortigate": ("fortinet", "fortigate", "fortios"),
    "fortinet": ("fortinet",),
    "fortios": ("fortinet", "fortios"),
    "citrix": ("citrix",),
    "citrix gateway": ("citrix",),
    "citrix adc": ("citrix",),
    "sonicwall": ("sonicwall",),
    "palo alto": ("paloalto", "panos"),
    "pan-os": ("paloalto", "panos"),
    "globalprotect": ("globalprotect", "paloalto"),
    "cisco": ("cisco",),
    "cisco asa": ("cisco", "asa"),
    "vmware": ("vmware",),
    "vmware vcenter": ("vcenter", "vmware"),
    "vmware horizon": ("horizon", "vmware"),
    "oracle weblogic server": ("weblogic", "oracle"),
    "weblogic": ("weblogic", "oracle"),
    "red hat jboss": ("jboss",),
    "jboss": ("jboss",),
    "wildfly": ("wildfly", "jboss"),
    "wordpress": ("wordpress", "wp-plugin", "wp-theme", "wp"),
    "woocommerce": ("wordpress", "wp-plugin", "woocommerce"),
    "elementor": ("wordpress", "wp-plugin", "elementor"),
    "yoast seo": ("wordpress", "wp-plugin", "yoast"),
    "spring": ("spring", "springboot"),
    "spring boot": ("spring", "springboot"),
    "elasticsearch": ("elasticsearch", "elastic"),
    "elastic": ("elastic", "elasticsearch"),
    "kibana": ("kibana", "elastic"),
    "phpmyadmin": ("phpmyadmin",),
    "cpanel": ("cpanel",),
    "plesk": ("plesk",),
    "webmin": ("webmin",),
    "concrete cms": ("concrete",),
    "craft cms": ("craftcms",),
    "rocketchat": ("rocketchat",),
    "swagger ui": ("swagger",),
    "grav": ("grav",),
    "typo3 cms": ("typo3",),
    "october cms": ("october", "octobercms"),
    "1c-bitrix": ("bitrix",),
    "bitrix24": ("bitrix",),
    "jfrog artifactory": ("artifactory", "jfrog"),
    "sonatype nexus": ("nexus", "sonatype"),
    "nexus repository manager": ("nexus", "sonatype"),
    "sonarqube": ("sonarqube",),
    "zabbix": ("zabbix",),
    "nagios": ("nagios",),
    "splunk": ("splunk",),
    "openresty": ("openresty", "nginx"),
    "tengine": ("tengine", "nginx"),
    "litespeed": ("litespeed",),
    "caddy": ("caddy",),
    "haproxy": ("haproxy",),
    "traefik": ("traefik",),
    "envoy": ("envoy",),
    "varnish": ("varnish",),
    "squid": ("squid",),
    "kong": ("kong",),
    "minio": ("minio",),
    "gitea": ("gitea",),
    "gogs": ("gogs",),
    "gitlab": ("gitlab",),
    "jenkins": ("jenkins",),
    "grafana": ("grafana",),
    "prometheus": ("prometheus",),
    "keycloak": ("keycloak",),
    "nextcloud": ("nextcloud",),
    "owncloud": ("owncloud",),
    "roundcube": ("roundcube",),
    "zimbra": ("zimbra",),
    "horde": ("horde",),
    "squirrelmail": ("squirrelmail",),
    "moodle": ("moodle",),
    "magento": ("magento",),
    "prestashop": ("prestashop",),
    "opencart": ("opencart",),
    "drupal": ("drupal",),
    "joomla": ("joomla",),
    "laravel": ("laravel",),
    "symfony": ("symfony",),
    "django": ("django",),
    "flask": ("flask",),
    "express": ("express",),
    "nextjs": ("nextjs",),
    "nuxtjs": ("nuxt", "nuxtjs"),
    "angular": ("angular",),
    "react": ("react",),
    "vuejs": ("vuejs", "vue"),
    "php": ("php",),
    "java": ("java",),
    "python": ("python",),
    "golang": ("golang", "go"),
    "openssl": ("openssl",),
    "jquery": ("jquery",),
    "mediawiki": ("mediawiki",),
    "dokuwiki": ("dokuwiki",),
    "phpbb": ("phpbb",),
    "mybb": ("mybb",),
    "vbulletin": ("vbulletin",),
    "xenforo": ("xenforo",),
    "discourse": ("discourse",),
    "ghost": ("ghost",),
    "strapi": ("strapi",),
    "directus": ("directus",),
    "odoo": ("odoo",),
    "sap": ("sap",),
    "sap netweaver": ("sap", "netweaver"),
    "liferay": ("liferay",),
    "sitecore": ("sitecore",),
    "umbraco": ("umbraco",),
    "kentico": ("kentico",),
    "dnn": ("dnn", "dotnetnuke"),
    "dotnetnuke": ("dnn", "dotnetnuke"),
    "silverstripe": ("silverstripe",),
    "modx": ("modx",),
    "expressionengine": ("expressionengine",),
    "osticket": ("osticket",),
    "sugarcrm": ("sugarcrm",),
    "suitecrm": ("suitecrm",),
    "vtiger": ("vtiger",),
    "dolibarr": ("dolibarr",),
    "metabase": ("metabase",),
    "apache superset": ("superset",),
    "apache airflow": ("airflow",),
    "apache solr": ("solr",),
    "apache kafka": ("kafka",),
    "apache zookeeper": ("zookeeper",),
    "apache struts": ("struts",),
    "apache activemq": ("activemq",),
    "apache couchdb": ("couchdb",),
    "apache druid": ("druid",),
    "jupyter": ("jupyter",),
    "rstudio": ("rstudio",),
    "adminer": ("adminer",),
    "awstats": ("awstats",),
    "matomo": ("matomo",),
    "portainer": ("portainer",),
    "rancher": ("rancher",),
    "harbor": ("harbor",),
    "geoserver": ("geoserver",),
    "mapserver": ("mapserver",),
    "openssh": ("openssh", "ssh"),
    "exim": ("exim",),
    "exim smtpd": ("exim",),
    "postfix": ("postfix",),
    "dovecot": ("dovecot",),
    "proftpd": ("proftpd",),
    "vsftpd": ("vsftpd",),
    "mysql": ("mysql",),
    "mariadb": ("mariadb", "mysql"),
    "postgresql": ("postgresql", "postgres"),
    "redis": ("redis",),
    "mongodb": ("mongodb", "mongo"),
    "memcached": ("memcached",),
    "rabbitmq": ("rabbitmq",),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "cloudflare": ("cloudflare",),
    "akamai": ("akamai",),
    "fastly": ("fastly",),
    "ubuntu": (),
    "debian": (),
    "centos": (),
    "windows server": ("windows",),
    "hsts": (),
    "http/3": (),
    "http/2": (),
    "bootstrap": (),
    "google analytics": (),
    "google tag manager": (),
    "google font api": (),
    "font awesome": (),
    "cdnjs": (),
    "jsdelivr": (),
    "unpkg": (),
    "youtube": (),
    "owl carousel": (),
    "slick": (),
    "swiper": (),
    "lodash": (),
    "moment.js": (),
    "core-js": (),
    "webpack": (),
    "recaptcha": (),
    "open graph": (),
    "priority hints": (),
    "module federation": (),
}

# names that carry no check of their own and are not reported as unmapped
TECH_IGNORED: frozenset[str] = frozenset(
    name for name, tags in TECH_ALIASES.items() if not tags
)

_VERSION = re.compile(r":.*$")
_STRIP = re.compile(r"[^a-z0-9 +-]")


def normalize_tech(name: str) -> str:
    """The lookup key for a name httpx, a Server header or a banner emits."""
    value = _VERSION.sub("", (name or "").strip().lower())
    value = value.split("/", 1)[0].strip()
    value = _STRIP.sub("", value.replace(".", ""))
    return " ".join(value.split())


def tags_for_tech(name: str) -> tuple[str, ...] | None:
    """The template tags a tech name maps to; None when the name is unknown."""
    key = normalize_tech(name)
    if not key:
        return ()
    if key in TECH_ALIASES:
        return TECH_ALIASES[key]
    return None


__all__ = [
    "BASE_MAX_DEPTH",
    "BATCH_MAX_HOSTS",
    "BATCH_MIN_HOSTS",
    "BATCH_OVERRUN",
    "BATCH_SECONDS",
    "BODY_IDENTITY_BYTES",
    "CLUSTER_SIGNAL_LABELS",
    "DROP_REASON_LABELS",
    "GENERIC_TAGS",
    "MAX_BASES_PER_ORIGIN",
    "MAX_REPLAY_TARGETS",
    "MAX_REQUESTS",
    "MAX_REQUESTS_PER_ORIGIN",
    "MAX_TECH_GROUPS",
    "ONE_REQUEST_PATHS",
    "ROOT_TIERS",
    "SURFACE_CLASS_HELP",
    "SURFACE_CLASS_LABELS",
    "SURFACE_STATE_LABELS",
    "TECH_ALIASES",
    "TECH_IGNORED",
    "TIER_HELP",
    "TIER_LABELS",
    "TIER_ORDER",
    "UNIVERSAL_TAGS",
    "ClusterSignal",
    "DropReason",
    "SurfaceClass",
    "SurfaceState",
    "Tier",
    "is_generic_tag",
    "is_universal",
    "normalize_tech",
    "product_tags",
    "tags_for_tech",
]
