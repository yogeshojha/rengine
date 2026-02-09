"""Centralized HTTP client factory for reNgine.

All the http requests in reNgine should use these clients to ensure consistent configuration and behavior, this is because
some prefer to use proxy hence we need to ensure that all requests go through the same proxy if configured.

This module provides two main functions:
- Proxy support (HTTP and SOCKS5 via RENGINE_PROXY_URL env var) for now but will change to db based
- Configurable timeout and user-agent this is dummy for now will use user configured. TODO: dummy user agents
- Automatic retries on transient failures
"""

import os

import httpx

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
    """HTTP client for use in FastAPI routes and async services."""
    kwargs = _base_kwargs()
    kwargs["transport"] = httpx.AsyncHTTPTransport(retries=MAX_RETRIES)
    kwargs.update(overrides)
    return httpx.AsyncClient(**kwargs)


def get_sync_client(**overrides) -> httpx.Client:
    """HTTP client for use in Celery workers and sync services."""
    kwargs = _base_kwargs()
    kwargs["transport"] = httpx.HTTPTransport(retries=MAX_RETRIES)
    kwargs.update(overrides)
    return httpx.Client(**kwargs)
