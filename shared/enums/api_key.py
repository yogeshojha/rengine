from enum import Enum, StrEnum


class APIProvider(Enum):
    VIEWDNS = "viewdns"
    CHAOS = "chaos"
    NETLAS = "netlas"
    SECURITYTRAILS = "securitytrails"
    HACKERONE = "hackerone"
    INTIGRITI = "intigriti"
    VULNX = "vulnx"
    INTERACTSH = "interactsh"
    GITHUB = "github"
    TELEGRAM = "telegram"


class ProviderGroup(StrEnum):
    SUBDOMAINS = "subdomains"
    LOOKUPS = "lookups"
    EXPLOIT_INTEL = "exploit_intel"
    BOUNTY_PLATFORMS = "bounty_platforms"
    OAST = "oast"
    CHAT = "chat"
