import BrainCircuit from '@lucide/svelte/icons/brain-circuit';
import type { IconComponent } from './icons';

// mirrors shared/definitions/ai_services.py
export const AI_FIELD = 'ai';
export const AI_MODEL_FIELD = 'ai.model';
export const AI_YES = 'yes';
export const AI_ICON: IconComponent = BrainCircuit;

export const AiCategory = {
	SELF_HOSTED: 'self_hosted',
	GATEWAY: 'gateway',
	MCP: 'mcp',
	APPLICATION: 'application',
	CLOUD: 'cloud',
	GENERIC: 'generic'
} as const;
export type AiCategory = (typeof AiCategory)[keyof typeof AiCategory];

export const CATEGORY_LABELS: Record<AiCategory, string> = {
	self_hosted: 'Model server',
	gateway: 'AI gateway',
	mcp: 'MCP server',
	application: 'AI application',
	cloud: 'Cloud AI endpoint',
	generic: 'OpenAI-compatible API'
};

const SELF = AiCategory.SELF_HOSTED;
const GATE = AiCategory.GATEWAY;
const APP = AiCategory.APPLICATION;
const CLOUD = AiCategory.CLOUD;

export const SERVICES: Record<string, { label: string; category: AiCategory }> = {
	ollama: { label: 'Ollama', category: SELF },
	vllm: { label: 'vLLM', category: SELF },
	sglang: { label: 'SGLang', category: SELF },
	localai: { label: 'LocalAI', category: SELF },
	'llama-cpp': { label: 'llama.cpp', category: SELF },
	'huggingface-tgi': { label: 'Hugging Face TGI', category: SELF },
	'nvidia-nim': { label: 'NVIDIA NIM', category: SELF },
	'tensorrt-llm': { label: 'TensorRT-LLM', category: SELF },
	'triton-inference-server': { label: 'Triton Inference Server', category: SELF },
	bentoml: { label: 'BentoML', category: SELF },
	'ray-serve': { label: 'Ray Serve', category: SELF },
	'aphrodite-engine': { label: 'Aphrodite Engine', category: SELF },
	'baseten-truss': { label: 'Baseten Truss', category: SELF },
	'deepspeed-mii': { label: 'DeepSpeed-MII', category: SELF },
	'fastchat-controller': { label: 'FastChat', category: SELF },
	gpt4all: { label: 'GPT4All', category: SELF },
	gradio: { label: 'Gradio', category: SELF },
	jan: { label: 'Jan', category: SELF },
	koboldcpp: { label: 'KoboldCpp', category: SELF },
	'lm-studio': { label: 'LM Studio', category: SELF },
	'mlc-llm': { label: 'MLC LLM', category: SELF },
	petals: { label: 'Petals', category: SELF },
	powerinfer: { label: 'PowerInfer', category: SELF },
	tabbyapi: { label: 'TabbyAPI', category: SELF },
	'text-generation-webui': { label: 'Text Generation WebUI', category: SELF },
	litellm: { label: 'LiteLLM', category: GATE },
	bifrost: { label: 'Bifrost', category: GATE },
	'envoy-ai-gateway': { label: 'Envoy AI Gateway', category: GATE },
	helicone: { label: 'Helicone', category: GATE },
	'kong-proxy': { label: 'Kong AI Gateway', category: GATE },
	omniroute: { label: 'OmniRoute', category: GATE },
	'portkey-ai-gateway': { label: 'Portkey AI Gateway', category: GATE },
	tensorzero: { label: 'TensorZero', category: GATE },
	'mcp-server': { label: 'MCP server', category: AiCategory.MCP },
	anythingllm: { label: 'AnythingLLM', category: APP },
	astrbot: { label: 'AstrBot', category: APP },
	betterchatgpt: { label: 'BetterChatGPT', category: APP },
	dify: { label: 'Dify', category: APP },
	flowise: { label: 'Flowise', category: APP },
	h2ogpt: { label: 'h2oGPT', category: APP },
	'huggingface-chat-ui': { label: 'Hugging Face Chat UI', category: APP },
	langflow: { label: 'Langflow', category: APP },
	librechat: { label: 'LibreChat', category: APP },
	lobehub: { label: 'LobeHub', category: APP },
	nextchat: { label: 'NextChat', category: APP },
	onyx: { label: 'Onyx', category: APP },
	openclaw: { label: 'OpenClaw', category: APP },
	'open-webui': { label: 'Open WebUI', category: APP },
	privategpt: { label: 'PrivateGPT', category: APP },
	quivr: { label: 'Quivr', category: APP },
	ragflow: { label: 'RAGFlow', category: APP },
	sillytavern: { label: 'SillyTavern', category: APP },
	'aws-bedrock': { label: 'AWS Bedrock', category: CLOUD },
	'azure-openai': { label: 'Azure OpenAI', category: CLOUD },
	'cloudflare-ai-gateway': { label: 'Cloudflare AI Gateway', category: CLOUD },
	'databricks-model-serving': { label: 'Databricks Model Serving', category: CLOUD },
	'fireworks-ai': { label: 'Fireworks AI', category: CLOUD },
	'vertex-ai': { label: 'Google Vertex AI', category: CLOUD },
	groq: { label: 'Groq', category: CLOUD },
	modal: { label: 'Modal', category: CLOUD },
	replicate: { label: 'Replicate', category: CLOUD },
	'salesforce-einstein': { label: 'Salesforce Einstein', category: CLOUD },
	'together-ai': { label: 'Together AI', category: CLOUD },
	'openai-compatible': { label: 'OpenAI-compatible API', category: AiCategory.GENERIC }
};

export function aiServiceLabel(key: string): string {
	return SERVICES[key]?.label ?? key;
}

export function aiCategoryLabel(category: string | null | undefined): string {
	return CATEGORY_LABELS[(category ?? '') as AiCategory] ?? CATEGORY_LABELS.generic;
}

export function aiQuery(value: string): string {
	return `${AI_FIELD}:${value}`;
}

export function aiModelQuery(model: string): string {
	const value = /[\s:,"\\[\]()]/.test(model) ? `"${model.replace(/["\\]/g, '\\$&')}"` : model;
	return `${AI_MODEL_FIELD}:${value}`;
}
