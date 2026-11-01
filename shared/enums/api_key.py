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
    VIRUSTOTAL = "virustotal"
    CENSYS = "censys"
    SHODAN = "shodan"
    ALIENVAULT = "alienvault"
    URLSCAN = "urlscan"
    CERTSPOTTER = "certspotter"
    FULLHUNT = "fullhunt"
    LEAKIX = "leakix"
    BEVIGIL = "bevigil"
    INTELX = "intelx"
    WHOISXMLAPI = "whoisxmlapi"
    FOFA = "fofa"
    ZOOMEYE = "zoomeye"


class ProviderGroup(StrEnum):
    SUBDOMAINS = "subdomains"
    INTERNET_SCANS = "internet_scans"
    LOOKUPS = "lookups"
    EXPLOIT_INTEL = "exploit_intel"
    BOUNTY_PLATFORMS = "bounty_platforms"
    OAST = "oast"
    CHAT = "chat"
