"""Detection of shared / managed DNS infrastructure.

Large numbers of unrelated domains are served by the same managed-DNS or CDN
nameservers (Cloudflare, AWS Route 53, Google Cloud DNS, Azure DNS, GoDaddy ...).
Correlating targets purely because they share such a nameserver yields large,
low-signal clusters that drown out genuine ownership relationships.

This module centralizes recognition of those shared nameservers so the
correlation layer can exclude them. Matching uses two strategies:

* distinctive *tokens* that only ever appear in managed-DNS hostnames
  (e.g. ``awsdns`` in ``ns-1234.awsdns-56.org``), matched as substrings;
* registrable *domains* that host shared nameservers, matched as an exact
  host or a dotted suffix to avoid accidental substring collisions.
"""

# Distinctive substrings unique to managed-DNS / CDN providers. Safe to match
# anywhere in the hostname because no legitimate private nameserver contains
# them.
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

# Registrable domains that host shared nameservers. Matched as an exact host or
# a dotted suffix (``ns1.gandi.net`` -> ``gandi.net``) so short names like
# ``name.com`` do not collide with unrelated hosts (``myname.com``).
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
    """Return ``True`` if a nameserver belongs to shared/managed infrastructure.

    Such nameservers are poor correlation keys: many unrelated targets point at
    the same Cloudflare/Route 53/etc. nameserver.
    """
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
