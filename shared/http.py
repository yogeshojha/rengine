import os

import httpx

# TODO: dummy user agents

DEFAULT_TIMEOUT = 30
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; reNgine/3.0; +https://github.com/yogeshojha/rengine)"
)
MAX_RETRIES = 3


def _get_proxy_url() -> str | None:
    return os.environ.get("RENGINE_PROXY_URL")


def _get_timeout() -> float:
    try:
        return float(os.environ.get("RENGINE_HTTP_TIMEOUT", DEFAULT_TIMEOUT))
    except (ValueError, TypeError):
        return DEFAULT_TIMEOUT


def _get_user_agent() -> str:
    return os.environ.get("RENGINE_USER_AGENT", DEFAULT_USER_AGENT)


def _base_kwargs() -> dict:
    kwargs: dict = {
        "timeout": httpx.Timeout(_get_timeout()),
        "headers": {"User-Agent": _get_user_agent()},
        "follow_redirects": True,
    }
    proxy = _get_proxy_url()
    if proxy:
        kwargs["proxy"] = proxy
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
