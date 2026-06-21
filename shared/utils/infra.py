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
