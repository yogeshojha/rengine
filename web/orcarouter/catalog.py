"""Bounded model discovery and capability filtering for OrcaRouter.

The model dropdown must be driven by the real catalog at
``GET {ORCAROUTER_API_BASE_URL}/models`` and never by free text or a hand
written example list. Live discovery is authoritative when it succeeds. When
it fails, a small verified seed keeps the installation usable and the UI
reports the degraded state.

Only minimal metadata is kept: the browser never receives the API key and does
not need pricing internals to render a selectable model.
"""

import json
import logging

import requests

from . import config

logger = logging.getLogger(__name__)


class OrcaRouterCatalogError(Exception):
    """Raised when the catalog cannot be retrieved or parsed safely."""


class CatalogResult:
    """Outcome of a bounded catalog fetch.

    ``source`` is ``live`` when the remote catalog was accepted and ``seed``
    when the verified fallback was used. ``degraded`` tells the UI that a
    refresh is advisable; ``error`` carries a short, key-free diagnostic.
    """

    def __init__(self, models, source, capability, error=None):
        self.models = models
        self.source = source
        self.capability = capability
        self.error = error
        self.degraded = source != 'live'

    def as_dict(self):
        return {
            'models': self.models,
            'source': self.source,
            'capability': self.capability,
            'degraded': self.degraded,
            'error': self.error,
            'count': len(self.models),
        }

    def __repr__(self):
        return (
            f'<CatalogResult source={self.source!r} capability={self.capability!r} '
            f'models={len(self.models)} degraded={self.degraded}>'
        )


def _bounded_str(value, limit):
    if not isinstance(value, str):
        return ''
    return value.strip()[:limit]


def _normalise_endpoint_types(value):
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        endpoint = _bounded_str(item, 64).lower()
        if endpoint and endpoint not in out:
            out.append(endpoint)
    return out


def _normalise_modalities(value):
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        modality = _bounded_str(item, 32).lower()
        if modality and modality not in out:
            out.append(modality)
    return out


def _normalise_model(record):
    """Convert one catalog record into the minimal provider model shape.

    Returns ``None`` when the record does not carry a usable identifier. The
    vendor/model namespace in ``id`` is preserved verbatim.
    """
    if not isinstance(record, dict):
        return None
    raw_id = _bounded_str(record.get('id'), config.MAX_MODEL_ID_LENGTH)
    if not raw_id:
        return None
    architecture = record.get('architecture')
    if not isinstance(architecture, dict):
        architecture = {}
    modalities = _normalise_modalities(architecture.get('input_modalities'))
    owned_by = _bounded_str(record.get('owned_by'), 100) or (
        raw_id.split('/')[0] if '/' in raw_id else '')
    model = {
        'id': raw_id,
        'name': raw_id,
        'owned_by': owned_by,
        'supported_endpoint_types': _normalise_endpoint_types(
            record.get('supported_endpoint_types')),
        'input_modalities': modalities,
        'context_length': _positive_int(record.get('context_length')),
        'max_completion_tokens': _positive_int(record.get('max_completion_tokens')),
        'reasoning_efforts': _normalise_modalities(record.get('reasoning_efforts')),
    }
    pricing = record.get('pricing')
    if isinstance(pricing, dict):
        model['pricing'] = {
            _bounded_str(k, 64): v
            for k, v in list(pricing.items())[:8]
            if isinstance(v, (str, int, float))
        }
    return model


def _positive_int(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def parse_catalog_payload(payload, capability=config.CAPABILITY_CHAT):
    """Parse a ``/v1/models`` payload and keep only compatible records.

    Accepts both the OpenAI-style ``{"data": [...]}`` envelope and a bare
    list. Unsupported shapes raise :class:`OrcaRouterCatalogError` so callers
    can fall back to the seed instead of rendering garbage.
    """
    if isinstance(payload, dict):
        data = payload.get('data')
    elif isinstance(payload, list):
        data = payload
    else:
        raise OrcaRouterCatalogError('Unexpected catalog payload')

    if not isinstance(data, list):
        raise OrcaRouterCatalogError('Unexpected catalog payload')

    models = []
    seen = set()
    for record in data[:config.CATALOG_MAX_MODELS]:
        model = _normalise_model(record)
        if not model or model['id'] in seen:
            continue
        seen.add(model['id'])
        models.append(model)
    return filter_models(models, capability)


def filter_models(models, capability=config.CAPABILITY_CHAT, required_modalities=None):
    """Keep only models that can serve ``capability``.

    Filtering is driven solely by declared catalog metadata. A model that does
    not declare the required capability fails closed: it is never offered just
    because its name looks like a chat model.
    """
    if capability == config.CAPABILITY_CHAT:
        allowed = config.CHAT_ENDPOINT_TYPES
        required_modalities = _normalise_modalities(required_modalities)
        out = []
        for model in models:
            endpoints = set(model.get('supported_endpoint_types') or [])
            if not endpoints.intersection(allowed):
                continue
            if endpoints and endpoints.issubset(config.NON_CHAT_ENDPOINT_TYPES):
                continue
            if required_modalities:
                declared = set(model.get('input_modalities') or [])
                if not declared.issuperset(required_modalities):
                    continue
            out.append(model)
        return out

    required_endpoints = config.CAPABILITY_ENDPOINT_TYPES.get(capability, frozenset())
    if not required_endpoints:
        return []
    out = []
    for model in models:
        endpoints = set(model.get('supported_endpoint_types') or [])
        if endpoints.intersection(required_endpoints):
            out.append(model)
    return out


def seed_catalog(capability=config.CAPABILITY_CHAT):
    """Return a deep-ish copy of the verified seed filtered for ``capability``.

    The copy matters: callers annotate models with UI flags (``selected``) and
    must not mutate the module-level constants.
    """
    models = []
    for entry in config.ORCAROUTER_SEED_MODELS:
        model = dict(entry)
        model['supported_endpoint_types'] = list(entry['supported_endpoint_types'])
        model['input_modalities'] = list(entry['input_modalities'])
        model['reasoning_efforts'] = list(entry['reasoning_efforts'])
        model['pricing'] = dict(entry.get('pricing') or {})
        models.append(model)
    return filter_models(models, capability)


def _read_bounded(response, limit):
    chunks = []
    total = 0
    for chunk in response.iter_content(8192):
        total += len(chunk)
        if total > limit:
            raise OrcaRouterCatalogError('Catalog response too large')
        chunks.append(chunk)
    return b''.join(chunks)


def fetch_chat_catalog(api_key, capability=config.CAPABILITY_CHAT, session=None,
                       required_modalities=None):
    """Fetch the live catalog, falling back to the verified seed.

    The API key is only ever sent in the ``Authorization`` header. Errors are
    reduced to short, key-free messages before they reach logs or the UI.
    """
    session = session or requests
    url = f'{config.ORCAROUTER_API_BASE_URL}{config.ORCAROUTER_MODELS_PATH}'
    params = {'capability': capability}
    headers = {'Accept': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        response = session.get(
            url,
            params=params,
            headers=headers,
            timeout=config.CATALOG_TIMEOUT,
            stream=True,
        )
        status = getattr(response, 'status_code', None)
        if status == 401 or status == 403:
            return CatalogResult(
                seed_catalog(capability), 'seed', capability,
                error='OrcaRouter rejected the API key. Update it in the API Vault.')
        if status != 200:
            return CatalogResult(
                seed_catalog(capability), 'seed', capability,
                error=f'OrcaRouter catalog returned HTTP {status}.')
        body = _read_bounded(response, config.CATALOG_MAX_BYTES)
        payload = json.loads(body.decode('utf-8'))
        models = parse_catalog_payload(payload, capability)
        if capability == config.CAPABILITY_CHAT and required_modalities:
            models = filter_models(models, capability, required_modalities)
        if not models:
            return CatalogResult(
                seed_catalog(capability), 'seed', capability,
                error='OrcaRouter catalog returned no compatible models.')
        return CatalogResult(models, 'live', capability)
    except OrcaRouterCatalogError as exc:
        logger.warning('OrcaRouter catalog unavailable: %s', exc)
        return CatalogResult(seed_catalog(capability), 'seed', capability, error=str(exc))
    except Exception as exc:  # network, JSON, timeout
        message = str(exc)[:config.MAX_ERROR_LENGTH]
        logger.warning('OrcaRouter catalog request failed: %s', message)
        return CatalogResult(
            seed_catalog(capability), 'seed', capability,
            error='Unable to reach OrcaRouter. Showing the last verified model list.')


def model_ids(models):
    return [model['id'] for model in models]


def reconcile_selection(selected, models):
    """Validate a stored selection against the current dropdown options.

    Returns ``(selected_or_empty, cleared)``. A value that is no longer
    compatible must be cleared rather than silently kept.
    """
    selected = _bounded_str(selected, config.MAX_MODEL_ID_LENGTH)
    if selected and selected in model_ids(models):
        return selected, False
    return '', bool(selected)


def pick_default_orcarouter_model(models):
    """Choose a sensible default from the current catalog.

    OrcaCyber Zero is the recommended default for authorized security work,
    but it is only advertised to verified business workspaces. Prefer it when
    the live catalog offers it, then the configured fallback, then the first
    compatible model so the dropdown is never left on a non-existent id.
    """
    ids = model_ids(models)
    for candidate in (config.ORCAROUTER_DEFAULT_MODEL, config.ORCAROUTER_FALLBACK_MODEL):
        if candidate in ids:
            return candidate
    return ids[0] if ids else ''
