from enum import Enum


class ProxyProtocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
