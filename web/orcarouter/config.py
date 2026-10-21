"""Static configuration for the OrcaRouter provider.

OrcaRouter is an OpenAI-compatible AI gateway. Inference and model discovery
share one public origin (``https://api.orcarouter.ai/v1``); authentication and
authorization live on a separate origin (``https://www.orcarouter.ai``). The
two origins are deliberately independent: never derive one from the other by
string replacement, and never append ``/v1`` to the authentication origin.

Deployments can point the provider at a self-hosted gateway with
``ORCA_BASE_URL`` (shared fallback) or with the explicit
``ORCA_API_BASE_URL`` / ``ORCA_AUTH_BASE_URL`` overrides, which take
precedence.
"""

import os
from urllib.parse import urlsplit

###############################################################################
# Origins
###############################################################################

OFFICIAL_AUTH_ORIGIN = 'https://www.orcarouter.ai'
OFFICIAL_API_ORIGIN = 'https://api.orcarouter.ai'
OFFICIAL_API_BASE_URL = f'{OFFICIAL_API_ORIGIN}/v1'

LOOPBACK_HOSTS = frozenset({'localhost', '127.0.0.1', '::1', '[::1]'})


def _clean(value):
    return (value or '').strip().rstrip('/')


def _shared_base_url():
    return _clean(os.environ.get('ORCA_BASE_URL'))


def api_base_url():
    """Return the inference/model-discovery base URL (always ends in ``/v1``)."""
    explicit = _clean(os.environ.get('ORCA_API_BASE_URL'))
    if explicit:
        return explicit
    shared = _shared_base_url()
    if shared:
        return shared if shared.endswith('/v1') else f'{shared}/v1'
    return OFFICIAL_API_BASE_URL


def auth_base_url():
    """Return the authentication origin used by browser/PKCE flows."""
    explicit = _clean(os.environ.get('ORCA_AUTH_BASE_URL'))
    if explicit:
        return explicit
    shared = _shared_base_url()
    if shared.endswith('/v1'):
        shared = shared[:-len('/v1')]
    return shared or OFFICIAL_AUTH_ORIGIN


def validate_origin(url):
    """Reject non-HTTPS remote origins.

    HTTP is only accepted for loopback hosts, which keeps local development
    possible without allowing credentials to travel in clear text.
    """
    parts = urlsplit(url or '')
    if parts.scheme == 'https':
        return url
    if parts.scheme == 'http' and (parts.hostname or '') in LOOPBACK_HOSTS:
        return url
    raise ValueError('OrcaRouter origins must use https:// (http is allowed for loopback only).')


ORCAROUTER_API_BASE_URL = api_base_url()
ORCAROUTER_AUTH_BASE_URL = auth_base_url()

ORCAROUTER_MODELS_PATH = '/models'
ORCAROUTER_CHAT_COMPLETIONS_PATH = '/chat/completions'
ORCAROUTER_AUTH_KEYS_PATH = '/api/v1/auth/keys'
ORCAROUTER_AUTHORIZE_URL = f'{ORCAROUTER_AUTH_BASE_URL}/auth'
ORCAROUTER_CONSOLE_KEYS_URL = f'{ORCAROUTER_AUTH_BASE_URL}/console/api-keys'
ORCAROUTER_HOME_URL = 'https://www.orcarouter.ai'
ORCAROUTER_LOGO_URL = 'https://www.orcarouter.ai/orca-logo-classic.png'
ORCAROUTER_KEY_PREFIX = 'sk-orca-'

###############################################################################
# Bounds
###############################################################################

# A catalog response must never be able to exhaust the server: bound the
# request, the payload size and the number of accepted entries.
CATALOG_TIMEOUT = 10
CATALOG_MAX_BYTES = 1000000
CATALOG_MAX_MODELS = 200
CHAT_TIMEOUT = 120
MAX_MODEL_ID_LENGTH = 200
MAX_ERROR_LENGTH = 400

###############################################################################
# Capabilities
###############################################################################

CAPABILITY_CHAT = 'chat'
CAPABILITY_EMBEDDING = 'embedding'
CAPABILITY_IMAGE = 'image'
CAPABILITY_VIDEO = 'video'
CAPABILITY_RERANK = 'rerank'

# Endpoint types the OrcaRouter client can speak for chat completions.
CHAT_ENDPOINT_TYPES = frozenset({'openai', 'openai-response', 'anthropic', 'gemini'})
# Endpoint types that are dedicated to a different capability and must never
# be offered in a text chat dropdown on their own.
NON_CHAT_ENDPOINT_TYPES = frozenset({
    'image-generation',
    'openai-video',
    'jina-rerank',
    'embeddings',
})

CAPABILITY_ENDPOINT_TYPES = {
    CAPABILITY_EMBEDDING: frozenset({'embeddings'}),
    CAPABILITY_IMAGE: frozenset({'image-generation'}),
    CAPABILITY_VIDEO: frozenset({'openai-video'}),
    CAPABILITY_RERANK: frozenset({'jina-rerank'}),
}

###############################################################################
# Models
###############################################################################

# OrcaCyber Zero is the recommended default for authorized security work.
# Access to it requires business verification; when the live catalog for the
# configured key does not advertise it, the UI falls back to a model that is
# actually callable instead of pretending the model exists.
ORCAROUTER_DEFAULT_MODEL = 'orcacyber-zero'
ORCAROUTER_FALLBACK_MODEL = 'orcarouter/fusion'

# Small, verified cold-start/outage seed. Live discovery is authoritative when
# it succeeds; this seed keeps a fresh installation usable when the catalog is
# slow or unreachable. Metadata is preserved exactly as verified.
ORCAROUTER_SEED_MODELS = [
    {
        'id': 'openai/gpt-5.5',
        'name': 'openai/gpt-5.5',
        'owned_by': 'openai',
        'context_length': 400000,
        'max_completion_tokens': 128000,
        'input_modalities': ['text', 'image'],
        'supported_endpoint_types': ['openai', 'openai-response'],
        'reasoning_efforts': ['low', 'medium', 'high', 'xhigh'],
        'pricing': {},
    },
    {
        'id': 'anthropic/claude-opus-4.8',
        'name': 'anthropic/claude-opus-4.8',
        'owned_by': 'anthropic',
        'context_length': 200000,
        'max_completion_tokens': 64000,
        'input_modalities': ['text', 'image'],
        'supported_endpoint_types': ['anthropic', 'openai'],
        'reasoning_efforts': [],
        'pricing': {},
    },
    {
        'id': 'google/gemini-3.5-flash',
        'name': 'google/gemini-3.5-flash',
        'owned_by': 'google',
        'context_length': 1000000,
        'max_completion_tokens': 65536,
        'input_modalities': ['text', 'image'],
        'supported_endpoint_types': ['gemini', 'openai'],
        'reasoning_efforts': [],
        'pricing': {},
    },
    {
        'id': 'deepseek/deepseek-v4-pro',
        'name': 'deepseek/deepseek-v4-pro',
        'owned_by': 'deepseek',
        'context_length': 1048576,
        'max_completion_tokens': 65536,
        'input_modalities': ['text'],
        'supported_endpoint_types': ['openai', 'openai-response'],
        'reasoning_efforts': [],
        'pricing': {},
    },
    {
        'id': 'orcarouter/auto',
        'name': 'orcarouter/auto',
        'owned_by': 'orcarouter',
        'context_length': 200000,
        'max_completion_tokens': 32768,
        'input_modalities': ['text'],
        'supported_endpoint_types': ['openai', 'openai-response'],
        'reasoning_efforts': [],
        'pricing': {},
    },
    {
        'id': 'orcarouter/fusion',
        'name': 'orcarouter/fusion',
        'owned_by': 'orcarouter',
        'context_length': 1000000,
        'max_completion_tokens': 65536,
        'input_modalities': ['text'],
        'supported_endpoint_types': ['openai', 'openai-response', 'anthropic', 'gemini'],
        'reasoning_efforts': [],
        'pricing': {},
    },
]
