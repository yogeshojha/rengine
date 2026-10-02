from enum import StrEnum


class AuthType(StrEnum):
    NONE = "none"
    HEADER = "header"
    BEARER = "bearer"
    BASIC = "basic"
    COOKIE = "cookie"
    API_KEY = "api_key"


class HttpProtocol(StrEnum):
    BOTH = "both"
    HTTP_ONLY = "http_only"
    HTTPS_ONLY = "https_only"
