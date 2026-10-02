"""AI services identified on web assets: model servers, gateways, agent platforms and MCP."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

AI_FIELD = "ai"
AI_MODEL_FIELD = "ai.model"

MAX_MODELS = 100
MAX_MODEL_LENGTH = 200
MAX_SERVICE_LENGTH = 64
MAX_ENDPOINT_LENGTH = 500

# measured on julius v1.4.19: 54 distinct requests plus one model listing
REQUESTS_PER_ASSET = 55
MCP_PATHS: tuple[str, ...] = ("/mcp", "/api/mcp")


class AiCategory(StrEnum):
    SELF_HOSTED = "self_hosted"
    GATEWAY = "gateway"
    MCP = "mcp"
    APPLICATION = "application"
    CLOUD = "cloud"
    GENERIC = "generic"


CATEGORY_LABELS: dict[str, str] = {
    AiCategory.SELF_HOSTED.value: "Model server",
    AiCategory.GATEWAY.value: "AI gateway",
    AiCategory.MCP.value: "MCP server",
    AiCategory.APPLICATION.value: "AI application",
    AiCategory.CLOUD.value: "Cloud AI endpoint",
    AiCategory.GENERIC.value: "OpenAI-compatible API",
}

CATEGORY_ORDER: tuple[str, ...] = tuple(CATEGORY_LABELS)

JULIUS_CATEGORIES: dict[str, str] = {
    "self-hosted": AiCategory.SELF_HOSTED.value,
    "gateway": AiCategory.GATEWAY.value,
    "mcp": AiCategory.MCP.value,
    "rag-orchestration": AiCategory.APPLICATION.value,
    "cloud-managed": AiCategory.CLOUD.value,
    "generic": AiCategory.GENERIC.value,
}

GENERIC_SERVICE = "openai-compatible"
MCP_SERVICE = "mcp-server"


@dataclass(frozen=True)
class ServiceSpec:
    key: str
    label: str
    category: str


def _s(key: str, label: str, category: AiCategory) -> ServiceSpec:
    return ServiceSpec(key, label, category.value)


_SELF = AiCategory.SELF_HOSTED
_GATE = AiCategory.GATEWAY
_APP = AiCategory.APPLICATION
_CLOUD = AiCategory.CLOUD

SERVICES: tuple[ServiceSpec, ...] = (
    _s("ollama", "Ollama", _SELF),
    _s("vllm", "vLLM", _SELF),
    _s("sglang", "SGLang", _SELF),
    _s("localai", "LocalAI", _SELF),
    _s("llama-cpp", "llama.cpp", _SELF),
    _s("huggingface-tgi", "Hugging Face TGI", _SELF),
    _s("nvidia-nim", "NVIDIA NIM", _SELF),
    _s("tensorrt-llm", "TensorRT-LLM", _SELF),
    _s("triton-inference-server", "Triton Inference Server", _SELF),
    _s("bentoml", "BentoML", _SELF),
    _s("ray-serve", "Ray Serve", _SELF),
    _s("aphrodite-engine", "Aphrodite Engine", _SELF),
    _s("baseten-truss", "Baseten Truss", _SELF),
    _s("deepspeed-mii", "DeepSpeed-MII", _SELF),
    _s("fastchat-controller", "FastChat", _SELF),
    _s("gpt4all", "GPT4All", _SELF),
    _s("gradio", "Gradio", _SELF),
    _s("jan", "Jan", _SELF),
    _s("koboldcpp", "KoboldCpp", _SELF),
    _s("lm-studio", "LM Studio", _SELF),
    _s("mlc-llm", "MLC LLM", _SELF),
    _s("petals", "Petals", _SELF),
    _s("powerinfer", "PowerInfer", _SELF),
    _s("tabbyapi", "TabbyAPI", _SELF),
    _s("text-generation-webui", "Text Generation WebUI", _SELF),
    _s("litellm", "LiteLLM", _GATE),
    _s("bifrost", "Bifrost", _GATE),
    _s("envoy-ai-gateway", "Envoy AI Gateway", _GATE),
    _s("helicone", "Helicone", _GATE),
    _s("kong-proxy", "Kong AI Gateway", _GATE),
    _s("omniroute", "OmniRoute", _GATE),
    _s("portkey-ai-gateway", "Portkey AI Gateway", _GATE),
    _s("tensorzero", "TensorZero", _GATE),
    _s(MCP_SERVICE, "MCP server", AiCategory.MCP),
    _s("anythingllm", "AnythingLLM", _APP),
    _s("astrbot", "AstrBot", _APP),
    _s("betterchatgpt", "BetterChatGPT", _APP),
    _s("dify", "Dify", _APP),
    _s("flowise", "Flowise", _APP),
    _s("h2ogpt", "h2oGPT", _APP),
    _s("huggingface-chat-ui", "Hugging Face Chat UI", _APP),
    _s("langflow", "Langflow", _APP),
    _s("librechat", "LibreChat", _APP),
    _s("lobehub", "LobeHub", _APP),
    _s("nextchat", "NextChat", _APP),
    _s("onyx", "Onyx", _APP),
    _s("openclaw", "OpenClaw", _APP),
    _s("open-webui", "Open WebUI", _APP),
    _s("privategpt", "PrivateGPT", _APP),
    _s("quivr", "Quivr", _APP),
    _s("ragflow", "RAGFlow", _APP),
    _s("sillytavern", "SillyTavern", _APP),
    _s("aws-bedrock", "AWS Bedrock", _CLOUD),
    _s("azure-openai", "Azure OpenAI", _CLOUD),
    _s("cloudflare-ai-gateway", "Cloudflare AI Gateway", _CLOUD),
    _s("databricks-model-serving", "Databricks Model Serving", _CLOUD),
    _s("fireworks-ai", "Fireworks AI", _CLOUD),
    _s("vertex-ai", "Google Vertex AI", _CLOUD),
    _s("groq", "Groq", _CLOUD),
    _s("modal", "Modal", _CLOUD),
    _s("replicate", "Replicate", _CLOUD),
    _s("salesforce-einstein", "Salesforce Einstein", _CLOUD),
    _s("together-ai", "Together AI", _CLOUD),
    _s(GENERIC_SERVICE, "OpenAI-compatible API", AiCategory.GENERIC),
)

SERVICE_BY_KEY: dict[str, ServiceSpec] = {s.key: s for s in SERVICES}

# default ports of the services above that no web port list carries
AI_PORTS: tuple[int, ...] = (
    1234, 1337, 2242, 3080, 3210, 4000, 4891, 5050, 6185, 7860, 8265, 8585,
    8787, 11434, 18789, 20128, 21001, 28080, 30000,
)  # fmt: skip


AI_YES = "yes"
AI_NO = "no"
AI_QUERY_VALUES: tuple[str, ...] = (
    AI_YES,
    AI_NO,
    *CATEGORY_ORDER,
    *(s.key for s in SERVICES),
)


def service_label(key: str) -> str:
    spec = SERVICE_BY_KEY.get(key)
    return spec.label if spec else key


def normalise_category(raw: str | None, service: str) -> str:
    """The category of a julius result, the catalog's when the service is known."""
    spec = SERVICE_BY_KEY.get(service)
    if spec is not None:
        return spec.category
    return JULIUS_CATEGORIES.get((raw or "").strip().lower(), AiCategory.GENERIC.value)


_MODEL_NEEDS_QUOTE = re.compile(r'[\s:,"\\\[\]()]')


def ai_query(service: str) -> str:
    return f"{AI_FIELD}:{service}"


def model_query(model: str) -> str:
    if _MODEL_NEEDS_QUOTE.search(model):
        model = '"' + model.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return f"{AI_MODEL_FIELD}:{model}"


__all__ = [
    "AI_FIELD",
    "AI_MODEL_FIELD",
    "AI_NO",
    "AI_PORTS",
    "AI_QUERY_VALUES",
    "AI_YES",
    "CATEGORY_LABELS",
    "CATEGORY_ORDER",
    "GENERIC_SERVICE",
    "JULIUS_CATEGORIES",
    "MAX_ENDPOINT_LENGTH",
    "MAX_MODELS",
    "MAX_MODEL_LENGTH",
    "MAX_SERVICE_LENGTH",
    "MCP_PATHS",
    "MCP_SERVICE",
    "REQUESTS_PER_ASSET",
    "SERVICES",
    "SERVICE_BY_KEY",
    "AiCategory",
    "ServiceSpec",
    "ai_query",
    "model_query",
    "normalise_category",
    "service_label",
]
