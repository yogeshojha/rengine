import httpx

from shared.config import base_settings

MAX_RETRIES = 3


def _base_kwargs() -> dict:
    settings = base_settings()
    kwargs: dict = {
        "timeout": httpx.Timeout(settings.EGRESS_TIMEOUT),
        "headers": {"User-Agent": settings.EGRESS_USER_AGENT},
        "follow_redirects": True,
    }
    if settings.EGRESS_PROXY_URL:
        kwargs["proxy"] = settings.EGRESS_PROXY_URL
    return kwargs


def get_async_client(**overrides) -> httpx.AsyncClient:
    kwargs = _base_kwargs()
    kwargs["transport"] = httpx.AsyncHTTPTransport(retries=MAX_RETRIES)
    kwargs.update(overrides)
    return httpx.AsyncClient(**kwargs)


def get_sync_client(**overrides) -> httpx.Client:
    kwargs = _base_kwargs()
    kwargs["transport"] = httpx.HTTPTransport(retries=MAX_RETRIES)
    kwargs.update(overrides)
    return httpx.Client(**kwargs)
