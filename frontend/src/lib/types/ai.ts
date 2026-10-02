export interface AiFeatureUsage {
	feature: string;
	label: string;
	calls: number;
	cached: number;
	failed: number;
	input_tokens: number;
	output_tokens: number;
	cost_usd: number | null;
	last_at: string | null;
}

export interface AiCall {
	id: string;
	at: string;
	feature: string;
	provider: string;
	model: string;
	ok: boolean;
	cached: boolean;
	input_tokens: number;
	output_tokens: number;
	cost_usd: number | null;
	latency_ms: number;
	error: string | null;
}

export interface AiUsage {
	calls: number;
	cost_usd: number | null;
	failed: number;
	since: string | null;
	by_feature: AiFeatureUsage[];
}

export interface AiStatus {
	enabled: boolean;
	configured: boolean;
	provider: string | null;
	model: string | null;
	fast_model: string | null;
	workspace_id: string | null;
	base_url: string | null;
	key_masked: string | null;
	features: Record<string, boolean>;
	usage: AiUsage;
	cached_narratives: number;
}

export interface AiModel {
	id: string;
	label: string;
	note: string;
	input_per_mtok: number | null;
	output_per_mtok: number | null;
	context: number;
}

export interface AiProvider {
	key: string;
	label: string;
	key_hint: string;
	help: string;
	key_optional: boolean;
	needs_base_url: boolean;
	base_url_hint: string;
	models: AiModel[];
}

export interface AiFeature {
	key: string;
	label: string;
	help: string;
	default: boolean;
}

export interface AiCatalog {
	providers: AiProvider[];
	features: AiFeature[];
}

export interface AiSettingsUpdate {
	enabled?: boolean;
	provider?: string;
	model?: string;
	fast_model?: string;
	workspace_id?: string;
	base_url?: string;
	api_key?: string;
	features?: Record<string, boolean>;
}

export interface AiTestResult {
	success: boolean;
	message: string;
	model: string | null;
	latency_ms: number | null;
}
