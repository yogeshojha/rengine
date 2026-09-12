import re
from collections.abc import Iterable

from shared.utils.privacy import registrant_key

_MIN_IDENTITY = 4

_SHARED_NS_TOKENS = frozenset(
    {
        "cloudflare",
        "awsdns",
        "azure-dns",
        "googledomains",
        "ultradns",
        "dnsmadeeasy",
        "akamai",
        "domaincontrol",
        "registrar-servers",
        "worldnic",
        "name-services",
        "cloudns",
        "vercel-dns",
        "wpengine",
        "wixdns",
        "squarespacedns",
        "dnsimple",
        "nsone",
        "foundationdns",
        "googlehosted",
        "incapdns",
        "sucuridns",
        "constellix",
        "dnspod",
        "hichina",
        "alidns",
        "markmonitor",
        "stabletransit",
        "gcorelabs",
        "cdnetworks",
        "dnsowl",
    }
)

_SHARED_NS_DOMAINS = frozenset(
    {
        "he.net",
        "gandi.net",
        "ovh.net",
        "akam.net",
        "name.com",
        "digitalocean.com",
        "linode.com",
    }
)


def is_shared_nameserver(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip().lower().rstrip(".")
    if not normalized:
        return False
    if any(token in normalized for token in _SHARED_NS_TOKENS):
        return True
    return any(
        normalized == domain or normalized.endswith(f".{domain}")
        for domain in _SHARED_NS_DOMAINS
    )


# CNAME targets every tenant of the platform shares
SHARED_EDGE_HOSTS: dict[str, str] = {
    "sni.global.fastly.net": "Fastly",
    "global.prod.fastly.net": "Fastly",
    "global-nossl.fastly.net": "Fastly",
    "nonssl.global.fastly.net": "Fastly",
    "freetls.fastly.net": "Fastly",
    "sni.cloudflaressl.com": "Cloudflare",
    "shops.myshopify.com": "Shopify",
    "cdn.shopify.com": "Shopify",
    "ghs.google.com": "Google",
    "ghs.googlehosted.com": "Google",
    "cname.vercel-dns.com": "Vercel",
    "apex-loadbalancer.netlify.com": "Netlify",
    "ext-cust.squarespace.com": "Squarespace",
    "ext-sq.squarespace.com": "Squarespace",
    "proxy-ssl.webflow.com": "Webflow",
    "balancer.wixdns.net": "Wix",
    "stats.statuspage.io": "Statuspage",
    "custom.intercom.help": "Intercom",
    "sites.hubspot.net": "HubSpot",
    "pi.pardot.com": "Pardot",
    "unbouncepages.com": "Unbounce",
    "sendgrid.net": "SendGrid",
    "mailgun.org": "Mailgun",
    "mandrillapp.com": "Mandrill",
    "hostedemail.com": "Hosted Email",
    "domains.tumblr.com": "Tumblr",
    "parkingpage.namecheap.com": "Namecheap",
    "registrar-servers.com": "Namecheap",
}

# public certificate authorities
PUBLIC_CA_NAMES: dict[str, str] = {
    "let's encrypt": "Let's Encrypt",
    "digicert": "DigiCert",
    "sectigo": "Sectigo",
    "comodo": "Comodo",
    "godaddy": "GoDaddy",
    "starfield": "Starfield",
    "globalsign": "GlobalSign",
    "entrust": "Entrust",
    "amazon": "Amazon",
    "google trust services": "Google Trust Services",
    "cloudflare inc": "Cloudflare",
    "zerossl": "ZeroSSL",
    "buypass": "Buypass",
    "rapidssl": "RapidSSL",
    "thawte": "Thawte",
    "geotrust": "GeoTrust",
    "identrust": "IdenTrust",
    "actalis": "Actalis",
    "ssl.com": "SSL.com",
    "certum": "Certum",
    "microsoft": "Microsoft",
}


def shared_edge(host: str | None) -> str | None:
    """The platform a shared CNAME target belongs to."""
    if not host:
        return None
    normalized = host.strip().lower().rstrip(".")
    for suffix, name in SHARED_EDGE_HOSTS.items():
        if normalized == suffix or normalized.endswith(f".{suffix}"):
            return name
    return None


def public_ca(issuer: str | None) -> str | None:
    """The certificate authority a public issuer belongs to."""
    if not issuer:
        return None
    normalized = issuer.strip().lower()
    for token, name in PUBLIC_CA_NAMES.items():
        if token in normalized:
            return name
    return None


_SHARED_MAIL_DOMAINS = frozenset(
    {
        "google.com",
        "googlemail.com",
        "outlook.com",
        "microsoft.com",
        "office365.com",
        "pphosted.com",
        "mimecast.com",
        "proofpoint.com",
        "barracudanetworks.com",
        "messagelabs.com",
        "zoho.com",
        "zohomail.com",
        "protonmail.ch",
        "fastmail.com",
        "mailgun.org",
        "sendgrid.net",
        "amazonses.com",
        "amazonaws.com",
        "mandrillapp.com",
        "sparkpostmail.com",
        "mail.ru",
        "yandex.net",
        "secureserver.net",
        "emailsrvr.com",
        "improvmx.com",
        "migadu.com",
        "qq.com",
        "cloudflare.com",
        "amazon.com",
    }
)


def is_shared_host(host: str | None) -> bool:
    """Whether a nameserver, mail host or mail domain belongs to a provider."""
    if not host:
        return False
    normalized = host.strip().lower().rstrip(".")
    if is_shared_nameserver(normalized) or shared_edge(normalized):
        return True
    labels = normalized.split(".")
    return any(
        ".".join(labels[i:]) in _SHARED_MAIL_DOMAINS for i in range(len(labels) - 1)
    )


def owns_network(as_name: str | None, identities: set[str]) -> bool:
    """Whether the network's holder is one of these parties, not a landlord."""
    holder = registrant_key(as_name)
    if not holder:
        return False
    for identity in identities:
        if len(identity) < _MIN_IDENTITY:
            continue
        if (
            holder == identity
            or holder.startswith(identity)
            or identity.startswith(holder)
        ):
            return True
    return False


# pages a server or an edge writes, keyed by the platform they come from
GENERIC_TITLE_PHRASES: dict[str, str] = {
    "just a moment": "Cloudflare",
    "attention required": "Cloudflare",
    "sorry, you have been blocked": "Cloudflare",
    "access denied": "an edge",
    "403 forbidden": "the server",
    "404 not found": "the server",
    "page not found": "the server",
    "not found": "the server",
    "site not found": "the server",
    "no such app": "the server",
    "under construction": "the server",
    "welcome to nginx": "nginx",
    "apache2 ubuntu default page": "Apache",
    "apache2 debian default page": "Apache",
    "it works": "Apache",
    "iis windows server": "IIS",
    "default web site page": "the server",
    "domain default page": "the server",
    "bad gateway": "the server",
    "service unavailable": "the server",
    "gateway timeout": "the server",
    "are you a robot": "an edge",
    "request rejected": "an edge",
}

_MIN_TITLE_LENGTH = 4
_STATUS_CODE = re.compile(r"\b([1-5]\d{2})\b")


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", title.strip().lower())


def generic_page(title: str | None, statuses: Iterable[int | None] = ()) -> str | None:
    """Who wrote the page, when the title is not the application's own."""
    if not title or not title.strip():
        return "the server"
    normalized = " ".join(_normalize_title(title).split())
    if len(normalized) < _MIN_TITLE_LENGTH or normalized.isdigit():
        return "the server"
    for phrase, source in GENERIC_TITLE_PHRASES.items():
        if " ".join(_normalize_title(phrase).split()) in normalized:
            return source
    codes = {int(m.group(1)) for m in _STATUS_CODE.finditer(normalized)}
    answered = {code for code in statuses if code is not None}
    if codes and answered and codes <= answered:
        return "the server"
    return None
