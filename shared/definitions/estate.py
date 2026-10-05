"""What ties a target to another domain, a provider or another target."""

from __future__ import annotations

import re
from enum import StrEnum
from functools import lru_cache

from shared.definitions.constants import PURE_CACHE
from shared.definitions.domains import (
    VENDOR_DOMAINS,
    registrable_domain,
    takeover_provider,
)
from shared.definitions.relations import RELATION_LABELS
from shared.utils.infra import is_shared_nameserver, shared_edge


class EstateReason(StrEnum):
    REDIRECT = "redirect"
    CNAME = "cname"
    CERT_SUBJECT = "cert_subject"
    CERT_SAN = "cert_san"
    ADDRESS = "address"
    EMPLOYEE_LOGINS = "employee_logins"
    NAME = "name"


class EstateStrength(StrEnum):
    DIRECT = "direct"
    SHARED = "shared"


class ProviderKind(StrEnum):
    EDGE = "edge"
    HOSTING = "hosting"
    DNS = "dns"
    MAIL = "mail"


class EstateTriageState(StrEnum):
    OPEN = "open"
    DISMISSED = "dismissed"


ESTATE_REASON_LABELS: dict[str, str] = {
    EstateReason.REDIRECT.value: "Redirects to",
    EstateReason.CNAME.value: "Delegates to",
    EstateReason.CERT_SUBJECT.value: "Serves a certificate for",
    EstateReason.CERT_SAN.value: "Named on a certificate",
    EstateReason.ADDRESS.value: "Same address",
    EstateReason.EMPLOYEE_LOGINS.value: "Employee logins",
    EstateReason.NAME.value: "Name contains",
    **RELATION_LABELS,
}

# strongest first
ESTATE_REASON_ORDER: tuple[str, ...] = (
    EstateReason.REDIRECT.value,
    EstateReason.CNAME.value,
    EstateReason.CERT_SUBJECT.value,
    EstateReason.CERT_SAN.value,
    *RELATION_LABELS.keys(),
    EstateReason.ADDRESS.value,
    EstateReason.EMPLOYEE_LOGINS.value,
    EstateReason.NAME.value,
)

# a certificate naming more registrable domains than this is a platform's
NEIGHBOUR_MAX_NAMES = 5
MAX_ESTATE_DOMAINS = 60
MAX_ESTATE_HOSTS = 6
MAX_PROJECT_ESTATE = 60
MAX_ESTATE_DOMAIN_LENGTH = 253

# candidate dossier
DOSSIER_TTL_DAYS = 7
MAX_ENRICH_PER_TICK = 40
MAX_DOSSIER_PORTS = 8
MAX_REGISTRAR_LENGTH = 200

# suffix -> provider name
PROVIDER_SUFFIXES: dict[str, str] = {
    "azurefd.net": "Azure Front Door",
    "azureedge.net": "Azure CDN",
    "azurewebsites.net": "Azure App Service",
    "azure-mobile.net": "Azure",
    "cloudapp.net": "Azure",
    "cloudapp.azure.com": "Azure",
    "trafficmanager.net": "Azure Traffic Manager",
    "windows.net": "Azure",
    "amazonaws.com": "AWS",
    "cloudfront.net": "CloudFront",
    "elasticbeanstalk.com": "AWS",
    "awsglobalaccelerator.com": "AWS",
    "cloudflare.net": "Cloudflare",
    "cloudflare.com": "Cloudflare",
    "cdn.cloudflare.net": "Cloudflare",
    "akamai.net": "Akamai",
    "akamaiedge.net": "Akamai",
    "akamaihd.net": "Akamai",
    "edgekey.net": "Akamai",
    "edgesuite.net": "Akamai",
    "fastly.net": "Fastly",
    "fastlylb.net": "Fastly",
    "incapdns.net": "Imperva",
    "impervadns.net": "Imperva",
    "sucuri.net": "Sucuri",
    "netlify.app": "Netlify",
    "netlify.com": "Netlify",
    "vercel.app": "Vercel",
    "vercel-dns.com": "Vercel",
    "github.io": "GitHub Pages",
    "herokuapp.com": "Heroku",
    "herokudns.com": "Heroku",
    "wixdns.net": "Wix",
    "wixsite.com": "Wix",
    "squarespace.com": "Squarespace",
    "myshopify.com": "Shopify",
    "shopify.com": "Shopify",
    "wpengine.com": "WP Engine",
    "wpenginepowered.com": "WP Engine",
    "pressable.com": "Pressable",
    "automattic.com": "Automattic",
    "pantheonsite.io": "Pantheon",
    "kinsta.cloud": "Kinsta",
    "siteground.biz": "SiteGround",
    "sgvps.net": "SiteGround",
    "hostinger.com": "Hostinger",
    "hstgr.io": "Hostinger",
    "aldryn.io": "Aldryn",
    "manageengine.eu": "ManageEngine",
    "manageengine.com": "ManageEngine",
    "zendesk.com": "Zendesk",
    "freshdesk.com": "Freshdesk",
    "hubspot.com": "HubSpot",
    "hs-sites.com": "HubSpot",
    "salesforce.com": "Salesforce",
    "force.com": "Salesforce",
    "short.io": "short.io",
    "bit.ly": "Bitly",
    "smtp2go.net": "SMTP2GO",
    "sendgrid.net": "SendGrid",
    "mailgun.org": "Mailgun",
    "mailchimp.com": "Mailchimp",
    "outlook.com": "Microsoft 365",
    "office365.com": "Microsoft 365",
    "protection.outlook.com": "Microsoft 365",
    "google.com": "Google Workspace",
    "googlehosted.com": "Google Workspace",
    "pphosted.com": "Proofpoint",
    "mimecast.com": "Mimecast",
    "cloudns.net": "ClouDNS",
    "domaincontrol.com": "GoDaddy",
    "registrar-servers.com": "Namecheap",
    "dnsmadeeasy.com": "DNS Made Easy",
    "ultradns.com": "UltraDNS",
    "ultradns.net": "UltraDNS",
    "nsone.net": "NS1",
    "he.net": "Hurricane Electric",
    "gandi.net": "Gandi",
    "ovh.net": "OVH",
    "digitalocean.com": "DigitalOcean",
    "linode.com": "Linode",
    "hetzner.com": "Hetzner",
    "grnet.gr": "GRNET",
    "cpanel.net": "cPanel",
    "plesk.page": "Plesk",
}

EDGE_PROVIDERS = frozenset(
    {
        "Azure Front Door",
        "Azure CDN",
        "Azure Traffic Manager",
        "CloudFront",
        "Cloudflare",
        "Akamai",
        "Fastly",
        "Imperva",
        "Sucuri",
    }
)

_ROUTE53 = re.compile(r"awsdns-\d{2}\.(?:com|net|org|co\.uk)")


@lru_cache(maxsize=PURE_CACHE)
def provider_of(host: str) -> str | None:
    """The platform a host belongs to, or None when it is an estate's own."""
    name = (host or "").strip().lower().rstrip(".").removeprefix("*.")
    if "." not in name or " " in name:
        return None
    apex = registrable_domain(name)
    if _ROUTE53.fullmatch(apex):
        return "Route 53"
    labels = name.split(".")
    for i in range(len(labels) - 1):
        suffix = ".".join(labels[i:])
        if suffix in PROVIDER_SUFFIXES:
            return PROVIDER_SUFFIXES[suffix]
    edge = shared_edge(name)
    if edge:
        return edge
    if apex in VENDOR_DOMAINS or is_shared_nameserver(name):
        return apex
    return takeover_provider(name)
