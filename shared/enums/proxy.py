from enum import Enum


class ProxyMode(Enum):
    SINGLE = "single"
    ROTATING = "rotating"


class ProxyProtocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
