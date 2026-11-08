"""API key providers grouped by what each adds."""

from __future__ import annotations

import re
from dataclasses import dataclass

from shared.enums.api_key import APIProvider, ProviderGroup


@dataclass(frozen=True)
class AccountField:
    """A second credential value stored in `key_meta[field]` beside the key."""

    field: str
    label: str
    required: bool = True
    default: str | None = None
    pattern: str | None = None
    invalid: str | None = None


@dataclass(frozen=True)
class SubfinderSource:
    name: str
    account_first: bool = False


_UUID = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

API_PROVIDER_META: dict[APIProvider, dict] = {
    APIProvider.GITHUB: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "GitHub",
        "description": "Subdomains found in public code, and subfinder's GitHub source",
        "docs_url": "https://github.com/settings/tokens",
        "icon": "github",
        "subfinder": SubfinderSource("github"),
        "setup": True,
    },
    APIProvider.CHAOS: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "Chaos",
        "description": "ProjectDiscovery Chaos subdomain dataset",
        "docs_url": "https://cloud.projectdiscovery.io",
        "icon": "radar",
        "subfinder": SubfinderSource("chaos"),
        "setup": True,
    },
    APIProvider.SECURITYTRAILS: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "SecurityTrails",
        "description": "Subdomains from SecurityTrails DNS history",
        "docs_url": "https://securitytrails.com",
        "icon": "route",
        "subfinder": SubfinderSource("securitytrails"),
        "setup": True,
    },
    APIProvider.VIRUSTOTAL: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "VirusTotal",
        "description": "Subdomains from VirusTotal passive DNS",
        "docs_url": "https://www.virustotal.com/gui/my-apikey",
        "icon": "shield",
        "subfinder": SubfinderSource("virustotal"),
        "setup": True,
    },
    APIProvider.ALIENVAULT: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "AlienVault OTX",
        "description": "Subdomains from OTX passive DNS",
        "docs_url": "https://otx.alienvault.com/api",
        "icon": "database",
        "subfinder": SubfinderSource("alienvault"),
        "setup": True,
    },
    APIProvider.URLSCAN: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "urlscan.io",
        "description": "Subdomains from pages urlscan.io has scanned",
        "docs_url": "https://urlscan.io/user/profile/",
        "icon": "scan-search",
        "subfinder": SubfinderSource("urlscan"),
    },
    APIProvider.CERTSPOTTER: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "Cert Spotter",
        "description": "Subdomains named on certificates in Certificate Transparency logs",
        "docs_url": "https://sslmate.com/account/api_credentials",
        "icon": "badge-check",
        "subfinder": SubfinderSource("certspotter"),
    },
    APIProvider.FULLHUNT: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "FullHunt",
        "description": "Subdomains from the FullHunt attack surface database",
        "docs_url": "https://fullhunt.io/user/settings/",
        "icon": "search",
        "subfinder": SubfinderSource("fullhunt"),
    },
    APIProvider.BEVIGIL: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "BeVigil",
        "description": "Subdomains referenced inside mobile applications",
        "docs_url": "https://bevigil.com/osint-api",
        "icon": "search",
        "subfinder": SubfinderSource("bevigil"),
    },
    APIProvider.INTELX: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "Intelligence X",
        "description": "Subdomains from the Intelligence X phonebook",
        "docs_url": "https://intelx.io/account?tab=developer",
        "icon": "search",
        "account": AccountField(
            "host",
            "API host",
            required=False,
            default="free.intelx.io",
            pattern=r"^([a-z0-9-]+\.)*intelx\.io$",
            invalid="The API host must be an intelx.io host, such as free.intelx.io.",
        ),
        "subfinder": SubfinderSource("intelx", account_first=True),
    },
    APIProvider.WHOISXMLAPI: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "WhoisXML API",
        "description": "Subdomains from the WhoisXML API subdomain lookup",
        "docs_url": "https://user.whoisxmlapi.com/products",
        "icon": "database",
        "subfinder": SubfinderSource("whoisxmlapi"),
    },
    APIProvider.SHODAN: {
        "group": ProviderGroup.INTERNET_SCANS.value,
        "name": "Shodan",
        "description": "Subdomains, and the services Shodan indexed on each address",
        "docs_url": "https://account.shodan.io",
        "icon": "radar",
        "subfinder": SubfinderSource("shodan"),
    },
    APIProvider.CENSYS: {
        "group": ProviderGroup.INTERNET_SCANS.value,
        "name": "Censys",
        "description": "Subdomains named on certificates Censys has indexed",
        "docs_url": "https://docs.censys.com/reference/get-started",
        "icon": "globe",
        "account": AccountField(
            "organization_id",
            "Organization ID",
            required=False,
            pattern=_UUID,
            invalid="The organization ID must be a UUID.",
        ),
        "subfinder": SubfinderSource("censys"),
        "setup": True,
    },
    APIProvider.NETLAS: {
        "group": ProviderGroup.INTERNET_SCANS.value,
        "name": "Netlas",
        "description": "Subdomains from the Netlas internet scan index",
        "docs_url": "https://netlas.io",
        "icon": "globe",
        "setup": True,
    },
    APIProvider.FOFA: {
        "group": ProviderGroup.INTERNET_SCANS.value,
        "name": "FOFA",
        "description": "Subdomains from the FOFA internet scan index",
        "docs_url": "https://en.fofa.info/userInfo",
        "icon": "globe",
        "account": AccountField(
            "email",
            "Account email",
            pattern=r"^[^@\s:]+@[^@\s:]+\.[^@\s:]+$",
            invalid="The account email is not an email address.",
        ),
        "subfinder": SubfinderSource("fofa", account_first=True),
    },
    APIProvider.ZOOMEYE: {
        "group": ProviderGroup.INTERNET_SCANS.value,
        "name": "ZoomEye",
        "description": "Subdomains from the ZoomEye internet scan index",
        "docs_url": "https://www.zoomeye.ai/profile",
        "icon": "globe",
        "account": AccountField(
            "host",
            "API host",
            required=False,
            default="zoomeye.ai",
            pattern=r"^zoomeye\.(ai|hk)$",
            invalid="The API host must be zoomeye.ai or zoomeye.hk.",
        ),
        "subfinder": SubfinderSource("zoomeyeapi", account_first=True),
    },
    APIProvider.LEAKIX: {
        "group": ProviderGroup.INTERNET_SCANS.value,
        "name": "LeakIX",
        "description": "Subdomains from the LeakIX service index",
        "docs_url": "https://leakix.net/settings/api",
        "icon": "search",
        "subfinder": SubfinderSource("leakix"),
    },
    APIProvider.VIEWDNS: {
        "group": ProviderGroup.LOOKUPS.value,
        "name": "ViewDNS.info",
        "description": "DNS intelligence, reverse lookups and DNS history",
        "docs_url": "https://viewdns.info/api/?src=reNgine",
        "icon": "scan-search",
        "setup": True,
    },
    APIProvider.HACKERONE: {
        "group": ProviderGroup.BOUNTY_PLATFORMS.value,
        "name": "HackerOne",
        "description": "Program scope and reports from HackerOne",
        "docs_url": "https://api.hackerone.com",
        "icon": "shield",
        "account": AccountField("username", "Username"),
    },
    APIProvider.INTIGRITI: {
        "group": ProviderGroup.BOUNTY_PLATFORMS.value,
        "name": "Intigriti",
        "description": "Program scope from Intigriti, including invite-only programs",
        "docs_url": "https://app.intigriti.com/researcher/personal-access-tokens",
        "icon": "shield",
    },
    APIProvider.VULNX: {
        "group": ProviderGroup.EXPLOIT_INTEL.value,
        "name": "vulnx",
        "description": "ProjectDiscovery vulnerability intelligence: exploits, coverage and exposure",
        "docs_url": "https://cloud.projectdiscovery.io",
        "icon": "biohazard",
        "setup": True,
    },
    APIProvider.INTERACTSH: {
        "group": ProviderGroup.OAST.value,
        "name": "Interactsh",
        "description": "Auth token for a self-hosted out-of-band callback server",
        "docs_url": "https://github.com/projectdiscovery/interactsh",
        "icon": "satellite-dish",
    },
    APIProvider.TELEGRAM: {
        "group": ProviderGroup.CHAT.value,
        "name": "Telegram",
        "description": "Bot token for remote control and notifications",
        "docs_url": "https://core.telegram.org/bots#how-do-i-create-a-bot",
        "icon": "send",
    },
}

PROVIDER_GROUP_LABELS: dict[str, str] = {
    ProviderGroup.SUBDOMAINS.value: "Subdomain sources",
    ProviderGroup.INTERNET_SCANS.value: "Internet scan data",
    ProviderGroup.LOOKUPS.value: "Lookups",
    ProviderGroup.EXPLOIT_INTEL.value: "Exploit intelligence",
    ProviderGroup.BOUNTY_PLATFORMS.value: "Bug bounty platforms",
    ProviderGroup.OAST.value: "Out-of-band testing",
    ProviderGroup.CHAT.value: "Chat",
}

# the groups the setup key step shows
RECON_GROUPS: tuple[str, ...] = (
    ProviderGroup.SUBDOMAINS.value,
    ProviderGroup.INTERNET_SCANS.value,
    ProviderGroup.LOOKUPS.value,
    ProviderGroup.EXPLOIT_INTEL.value,
)

SUBFINDER_SOURCES: dict[APIProvider, SubfinderSource] = {
    provider: meta["subfinder"]
    for provider, meta in API_PROVIDER_META.items()
    if "subfinder" in meta
}

MAX_KEY_LENGTH = 600

# subfinder splits a multi-part key on its colons
_KEY_SEPARATOR = ":"


def provider_name(provider: APIProvider | str) -> str:
    meta = API_PROVIDER_META.get(APIProvider(provider))
    return meta["name"] if meta else str(provider)


def account_of(provider: APIProvider) -> AccountField | None:
    return API_PROVIDER_META[provider].get("account")


def account_value(provider: APIProvider, key_meta: dict | None) -> str | None:
    """The stored account value, or the field's default."""
    field = account_of(provider)
    if field is None:
        return None
    value = str((key_meta or {}).get(field.field) or "").strip()
    return value or field.default


def clean_meta(provider: APIProvider, key_meta: dict | None) -> dict | None:
    """The account value alone, trimmed, under its field name."""
    field = account_of(provider)
    if field is None:
        return None
    value = str((key_meta or {}).get(field.field) or "").strip()
    return {field.field: value} if value else None


def key_error(provider: APIProvider, key_value: str) -> str | None:
    """Why a key value cannot be stored for this provider, or None."""
    name = provider_name(provider)
    if not key_value:
        return f"The {name} key is empty."
    if len(key_value.encode()) > MAX_KEY_LENGTH:
        return f"The {name} key is longer than {MAX_KEY_LENGTH} characters."
    if any(ch.isspace() or not ch.isprintable() for ch in key_value):
        return f"The {name} key contains spaces or control characters."
    if (
        provider in SUBFINDER_SOURCES
        and account_of(provider) is not None
        and _KEY_SEPARATOR in key_value
    ):
        return f"The {name} key contains a colon. Enter the {account_of(provider).label.lower()} in its own field."
    return None


def account_error(provider: APIProvider, key_meta: dict | None) -> str | None:
    """Why the account value cannot be stored for this provider, or None."""
    field = account_of(provider)
    if field is None:
        return None
    name = provider_name(provider)
    value = str((key_meta or {}).get(field.field) or "").strip()
    if not value:
        return f"{name} requires the {field.label.lower()}." if field.required else None
    if any(ch.isspace() or not ch.isprintable() for ch in value):
        return (
            f"The {name} {field.label.lower()} contains spaces or control characters."
        )
    if field.pattern and not re.fullmatch(field.pattern, value):
        return field.invalid or f"The {name} {field.label.lower()} is not valid."
    return None


def subfinder_value(
    provider: APIProvider, key: str, key_meta: dict | None
) -> str | None:
    """The provider-config entry subfinder reads for this key, or None when incomplete."""
    spec = SUBFINDER_SOURCES.get(provider)
    if spec is None or not key:
        return None
    field = account_of(provider)
    account = account_value(provider, key_meta)
    if field is not None and field.required and not account:
        return None
    if not account:
        return key
    return (
        f"{account}{_KEY_SEPARATOR}{key}"
        if spec.account_first
        else f"{key}{_KEY_SEPARATOR}{account}"
    )
