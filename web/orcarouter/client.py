"""OpenAI-compatible client and credential helpers for OrcaRouter.

The provider is a first-class named provider: it keeps its own origins, its own
credential and its own model catalog, and it is not a generic "any base URL"
passthrough.

Secrets rules enforced here:

- the API key is only ever placed in the ``Authorization`` header;
- error messages are truncated and never include the key;
- :func:`mask_key` is the only representation allowed to reach a template.
"""

import logging
import os
import re

import requests

from . import config

logger = logging.getLogger(__name__)

_KEY_PATTERN = re.compile(r'sk-orca-[A-Za-z0-9_\-]+')


class OrcaRouterError(Exception):
    """A provider error whose message is safe to show to a user."""


def mask_key(key):
    """Return a display-safe representation of an OrcaRouter API key."""
    if not key:
        return ''
    key = str(key).strip()
    if len(key) <= 12:
        return f'{key[:2]}…'
    return f'{key[:11]}…{key[-4:]}'


def redact(text):
    """Remove anything that looks like an OrcaRouter key from ``text``."""
    if not text:
        return ''
    return _KEY_PATTERN.sub('sk-orca-…', str(text))[:config.MAX_ERROR_LENGTH]


def resolve_api_key(key=None):
    """Resolve the OrcaRouter key from an explicit value or the environment.

    Stored keys win; ``ORCAROUTER_API_KEY`` lets operators configure the
    deployment without writing the secret to the database.
    """
    if key and str(key).strip():
        return str(key).strip()
    env_key = os.environ.get('ORCAROUTER_API_KEY', '').strip()
    return env_key or ''


def _error_message(response):
    """Extract a short, provider-supplied error message without secrets."""
    try:
        payload = response.json()
    except Exception:
        payload = None
    message = ''
    if isinstance(payload, dict):
        error = payload.get('error')
        if isinstance(error, dict):
            message = error.get('message') or ''
        elif isinstance(error, str):
            message = error
        if not message:
            message = payload.get('message') or ''
    if not message:
        message = getattr(response, 'reason', '') or ''
    return redact(message)


def chat_completion(api_key, model, messages, session=None, timeout=None):
    """Send one chat completion through OrcaRouter.

    Returns the assistant message content. Raises :class:`OrcaRouterError`
    with a redacted, user-facing message on failure.
    """
    api_key = resolve_api_key(api_key)
    if not api_key:
        raise OrcaRouterError('OrcaRouter API key is not set. Add it in the API Vault.')
    if not model:
        raise OrcaRouterError('No OrcaRouter model is selected.')
    if not isinstance(messages, list) or not messages:
        raise OrcaRouterError('OrcaRouter request requires at least one message.')

    session = session or requests
    url = f'{config.ORCAROUTER_API_BASE_URL}{config.ORCAROUTER_CHAT_COMPLETIONS_PATH}'
    try:
        response = session.post(
            url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json={'model': model, 'messages': messages},
            timeout=timeout or config.CHAT_TIMEOUT,
        )
    except Exception as exc:
        logger.warning('OrcaRouter request failed: %s', redact(exc))
        raise OrcaRouterError('Unable to reach OrcaRouter. Check the network and try again.')

    status = getattr(response, 'status_code', None)
    if status == 401:
        raise OrcaRouterError(
            'OrcaRouter rejected the API key. Update the key in the API Vault.')
    if status == 403:
        raise OrcaRouterError(
            'OrcaRouter refused this request for the current key. Confirm the key is '
            'valid and that the selected model is available to your workspace.')
    if status == 429:
        raise OrcaRouterError('OrcaRouter rate limit reached. Try again shortly.')
    if status != 200:
        detail = _error_message(response)
        suffix = f' {detail}' if detail else ''
        raise OrcaRouterError(f'OrcaRouter returned HTTP {status}.{suffix}')

    try:
        payload = response.json()
        content = payload['choices'][0]['message']['content']
    except Exception:
        raise OrcaRouterError('OrcaRouter returned an unexpected response.')
    if not isinstance(content, str) or not content.strip():
        raise OrcaRouterError('OrcaRouter returned an empty response.')
    return content
