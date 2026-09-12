"""Software inference: named products and NVD match confidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MAX_COMPONENTS_PER_ASSET = 60
MAX_MATCHES_PER_SCAN = 200_000
MAX_PRODUCT = 200
MAX_VENDOR = 200


class VersionSource(StrEnum):
    BANNER = "banner"
    FINGERPRINT = "fingerprint"


VERSION_SOURCE_LABELS: dict[str, str] = {
    VersionSource.BANNER.value: "Server header",
    VersionSource.FINGERPRINT.value: "Fingerprint",
}

VERSION_SOURCE_HELP: dict[str, str] = {
    VersionSource.BANNER.value: "Version stated in a server response header.",
    VersionSource.FINGERPRINT.value: "Version read from the page body.",
}


class Caveat(StrEnum):
    BACKPORT = "backport"
    CONDITIONAL = "conditional"
    FINGERPRINT = "fingerprint"
    COARSE = "coarse"


CAVEAT_LABELS: dict[str, str] = {
    Caveat.BACKPORT.value: "Distribution build",
    Caveat.CONDITIONAL.value: "Conditional",
    Caveat.FINGERPRINT.value: "Fingerprinted version",
    Caveat.COARSE.value: "Major version only",
}

CAVEAT_HELP: dict[str, str] = {
    Caveat.BACKPORT.value: (
        "The banner names a distribution build. Fixes may land without a version change."
    ),
    Caveat.CONDITIONAL.value: (
        "NVD ties this CVE to a further component this scan did not identify."
    ),
    Caveat.FINGERPRINT.value: ("The version was read from the page body."),
    Caveat.COARSE.value: (
        "Only a major version was reported. The match covers every release in that series."
    ),
}

CAVEAT_ORDER: tuple[str, ...] = tuple(c.value for c in Caveat)


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


CONFIDENCE_LABELS: dict[str, str] = {
    Confidence.HIGH.value: "High",
    Confidence.MEDIUM.value: "Medium",
    Confidence.LOW.value: "Low",
}

CONFIDENCE_HELP: dict[str, str] = {
    Confidence.HIGH.value: "The server stated the version and NVD names no further condition.",
    Confidence.MEDIUM.value: "One part of the match is unverified.",
    Confidence.LOW.value: "Two or more parts of the match are unverified.",
}

CONFIDENCE_ORDER: tuple[str, ...] = tuple(c.value for c in Confidence)

MEDIUM_CAVEATS = 1
LOW_CAVEATS = 2


def confidence_of(caveats: list[str] | tuple[str, ...]) -> str:
    count = len({c for c in caveats if c in CAVEAT_LABELS})
    if count >= LOW_CAVEATS:
        return Confidence.LOW.value
    if count >= MEDIUM_CAVEATS:
        return Confidence.MEDIUM.value
    return Confidence.HIGH.value


@dataclass(frozen=True)
class SoftwareProduct:
    """One name a tool reports, and the NVD pair it is filed under."""

    key: str
    product: str
    vendor: str | None = None


# ---------- servers and runtimes ----------

_SERVERS: tuple[SoftwareProduct, ...] = (
    SoftwareProduct("nginx", "nginx"),
    SoftwareProduct("apache", "http_server", "apache"),
    SoftwareProduct("apache_http_server", "http_server", "apache"),
    SoftwareProduct("openresty", "openresty", "openresty"),
    SoftwareProduct("iis", "internet_information_services", "microsoft"),
    SoftwareProduct("microsoft_iis", "internet_information_services", "microsoft"),
    SoftwareProduct("litespeed", "litespeed_web_server", "litespeedtech"),
    SoftwareProduct("openlitespeed", "openlitespeed", "litespeedtech"),
    SoftwareProduct("tomcat", "tomcat", "apache"),
    SoftwareProduct("apache_tomcat", "tomcat", "apache"),
    SoftwareProduct("jetty", "jetty"),
    SoftwareProduct("varnish", "varnish"),
    SoftwareProduct("squid", "squid"),
    SoftwareProduct("haproxy", "haproxy", "haproxy"),
    SoftwareProduct("traefik", "traefik", "traefik"),
    SoftwareProduct("caddy", "caddy", "caddyserver"),
    SoftwareProduct("envoy", "envoy", "envoyproxy"),
    SoftwareProduct("apache_apisix", "apisix", "apache"),
    SoftwareProduct("apisix", "apisix", "apache"),
    SoftwareProduct("exim", "exim", "exim"),
    SoftwareProduct("postfix", "postfix", "postfix"),
    SoftwareProduct("dovecot", "dovecot", "dovecot"),
    SoftwareProduct("openssh", "openssh", "openbsd"),
    SoftwareProduct("proftpd", "proftpd", "proftpd"),
    SoftwareProduct("vsftpd", "vsftpd", "beasts"),
    SoftwareProduct("phusion_passenger", "phusion_passenger"),
    SoftwareProduct("twistedweb", "twistedweb", "twistedmatrix"),
)

# ---------- languages and libraries shipped with the server ----------

_RUNTIMES: tuple[SoftwareProduct, ...] = (
    SoftwareProduct("php", "php"),
    SoftwareProduct("perl", "perl"),
    SoftwareProduct("python", "python", "python"),
    SoftwareProduct("openssl", "openssl"),
    SoftwareProduct("microsoft_asp.net", "asp.net", "microsoft"),
    SoftwareProduct("asp.net", "asp.net", "microsoft"),
    SoftwareProduct("mod_perl", "mod_perl", "apache"),
    SoftwareProduct("mod_wsgi", "mod_wsgi", "modwsgi"),
    SoftwareProduct("node.js", "node.js", "nodejs"),
    SoftwareProduct("express", "express", "openjsf"),
)

# ---------- applications ----------

_APPS: tuple[SoftwareProduct, ...] = (
    SoftwareProduct("wordpress", "wordpress", "wordpress"),
    SoftwareProduct("drupal", "drupal", "drupal"),
    SoftwareProduct("joomla", "joomla\\!", "joomla"),
    SoftwareProduct("moodle", "moodle", "moodle"),
    SoftwareProduct("phpmyadmin", "phpmyadmin", "phpmyadmin"),
    SoftwareProduct("webmin", "webmin", "webmin"),
    SoftwareProduct("cpanel", "cpanel", "cpanel"),
    SoftwareProduct("plesk", "plesk", "plesk"),
    SoftwareProduct("typo3", "typo3", "typo3"),
    SoftwareProduct("magento", "magento", "adobe"),
    SoftwareProduct("jenkins", "jenkins", "jenkins"),
    SoftwareProduct("grafana", "grafana", "grafana"),
    SoftwareProduct("keycloak", "keycloak", "redhat"),
    SoftwareProduct("strapi", "strapi", "strapi"),
    SoftwareProduct("gitlab", "gitlab", "gitlab"),
    SoftwareProduct("confluence", "confluence", "atlassian"),
    SoftwareProduct("jira", "jira", "atlassian"),
    SoftwareProduct("zimbra", "zimbra_collaboration_suite", "zimbra"),
    SoftwareProduct("roundcube", "webmail", "roundcube"),
    SoftwareProduct("nextcloud", "nextcloud_server", "nextcloud"),
    SoftwareProduct("n8n", "n8n", "n8n"),
    SoftwareProduct("modoboa", "modoboa", "modoboa"),
    SoftwareProduct("jumpserver", "jumpserver", "fit2cloud"),
)

# ---------- wordpress plugins and themes ----------

_PLUGINS: tuple[SoftwareProduct, ...] = (
    SoftwareProduct("contact_form_7", "contact_form_7", "rocklobster"),
    SoftwareProduct("yoast_seo", "yoast_seo", "yoast"),
    SoftwareProduct("slider_revolution", "slider_revolution", "themepunch"),
    SoftwareProduct("wpml", "wpml", "wpml"),
    SoftwareProduct("all_in_one_seo", "all_in_one_seo", "aioseo"),
    SoftwareProduct("all_in_one_seo_pack", "all_in_one_seo_pack", "semperplugins"),
    SoftwareProduct("woocommerce", "woocommerce"),
    SoftwareProduct("elementor", "website_builder", "elementor"),
    SoftwareProduct("addtoany_share_buttons", "addtoany_share_buttons", "addtoany"),
    SoftwareProduct("monsterinsights", "monsterinsights", "monsterinsights"),
    SoftwareProduct("divi", "divi", "elegantthemes"),
    SoftwareProduct(
        "advanced_custom_fields", "advanced_custom_fields", "advancedcustomfields"
    ),
    SoftwareProduct("max_mega_menu", "max_mega_menu", "megamenu"),
    SoftwareProduct("download_monitor", "download_monitor"),
    SoftwareProduct("tablepress", "tablepress", "tablepress"),
    SoftwareProduct("layerslider", "layerslider", "kreaturamedia"),
)

# ---------- front-end libraries ----------

_LIBRARIES: tuple[SoftwareProduct, ...] = (
    SoftwareProduct("jquery", "jquery", "jquery"),
    SoftwareProduct("jquery_ui", "jquery_ui", "jqueryui"),
    SoftwareProduct("bootstrap", "bootstrap", "getbootstrap"),
    SoftwareProduct("chart.js", "chart.js", "chartjs"),
    SoftwareProduct("mathjax", "mathjax", "mathjax"),
    SoftwareProduct("lodash", "lodash", "lodash"),
    SoftwareProduct("moment.js", "moment", "momentjs"),
    SoftwareProduct("next.js", "next.js", "vercel"),
    SoftwareProduct("angular", "angular", "angular"),
    SoftwareProduct("axios", "axios", "axios"),
)

PRODUCTS: tuple[SoftwareProduct, ...] = (
    *_SERVERS,
    *_RUNTIMES,
    *_APPS,
    *_PLUGINS,
    *_LIBRARIES,
)

PRODUCTS_BY_KEY: dict[str, SoftwareProduct] = {p.key: p for p in PRODUCTS}
