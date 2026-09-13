from enum import Enum


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
