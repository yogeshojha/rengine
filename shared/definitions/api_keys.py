"""API key providers grouped by what each adds."""

from shared.enums.api_key import APIProvider, ProviderGroup

API_PROVIDER_META: dict[str, dict] = {
    APIProvider.VIEWDNS: {
        "group": ProviderGroup.LOOKUPS.value,
        "name": "ViewDNS.info",
        "description": "DNS intelligence, reverse lookups and DNS history",
        "docs_url": "https://viewdns.info/api/?src=reNgine",
        "requires_username": False,
        "icon": "scan-search",
    },
    APIProvider.GITHUB: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "GitHub",
        "description": "Subdomains found in public code, and subfinder's GitHub source",
        "docs_url": "https://github.com/settings/tokens",
        "requires_username": False,
        "icon": "github",
    },
    APIProvider.CHAOS: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "Chaos",
        "description": "ProjectDiscovery Chaos subdomain dataset",
        "docs_url": "https://cloud.projectdiscovery.io",
        "requires_username": False,
        "icon": "radar",
    },
    APIProvider.NETLAS: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "Netlas",
        "description": "Internet-wide asset and attack-surface intelligence",
        "docs_url": "https://netlas.io",
        "requires_username": False,
        "icon": "globe",
    },
    APIProvider.SECURITYTRAILS: {
        "group": ProviderGroup.SUBDOMAINS.value,
        "name": "SecurityTrails",
        "description": "DNS, domain and subdomain history intelligence",
        "docs_url": "https://securitytrails.com",
        "requires_username": False,
        "icon": "route",
    },
    APIProvider.HACKERONE: {
        "group": ProviderGroup.BOUNTY_PLATFORMS.value,
        "name": "HackerOne",
        "description": "Program scope and reports from HackerOne",
        "docs_url": "https://api.hackerone.com",
        "requires_username": True,
        "icon": "shield",
    },
    APIProvider.INTIGRITI: {
        "group": ProviderGroup.BOUNTY_PLATFORMS.value,
        "name": "Intigriti",
        "description": "Program scope from Intigriti, including invite-only programs",
        "docs_url": "https://app.intigriti.com/researcher/personal-access-tokens",
        "requires_username": False,
        "icon": "shield",
    },
    APIProvider.VULNX: {
        "group": ProviderGroup.EXPLOIT_INTEL.value,
        "name": "vulnx",
        "description": "ProjectDiscovery vulnerability intelligence: exploits, coverage and exposure",
        "docs_url": "https://cloud.projectdiscovery.io",
        "requires_username": False,
        "icon": "biohazard",
    },
    APIProvider.INTERACTSH: {
        "group": ProviderGroup.OAST.value,
        "name": "Interactsh",
        "description": "Auth token for a self-hosted out-of-band callback server",
        "docs_url": "https://github.com/projectdiscovery/interactsh",
        "requires_username": False,
        "icon": "satellite-dish",
    },
    APIProvider.TELEGRAM: {
        "group": ProviderGroup.CHAT.value,
        "name": "Telegram",
        "description": "Bot token for remote control and notifications",
        "docs_url": "https://core.telegram.org/bots#how-do-i-create-a-bot",
        "requires_username": False,
        "icon": "send",
    },
}

PROVIDER_GROUP_LABELS: dict[str, str] = {
    ProviderGroup.SUBDOMAINS.value: "Subdomain sources",
    ProviderGroup.LOOKUPS.value: "Lookups",
    ProviderGroup.EXPLOIT_INTEL.value: "Exploit intelligence",
    ProviderGroup.BOUNTY_PLATFORMS.value: "Bug bounty platforms",
    ProviderGroup.OAST.value: "Out-of-band testing",
    ProviderGroup.CHAT.value: "Chat",
}

# the groups the setup key step shows
RECON_GROUPS: tuple[str, ...] = (
    ProviderGroup.SUBDOMAINS.value,
    ProviderGroup.LOOKUPS.value,
    ProviderGroup.EXPLOIT_INTEL.value,
)
