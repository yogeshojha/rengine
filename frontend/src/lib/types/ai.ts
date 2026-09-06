export interface AiUsage {
	calls: number;
	cached: number;
	input_tokens: number;
	output_tokens: number;
	cost_usd: number | null;
	reports: number;
	since: string | null;
}

export interface AiStatus {
	enabled: boolean;
	configured: boolean;
	provider: string | null;
	model: string | null;
	fast_model: string | null;
	workspace_id: string | null;
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
	api_key?: string;
	features?: Record<string, boolean>;
}

export interface AiTestResult {
	success: boolean;
	message: string;
	model: string | null;
	latency_ms: number | null;
}
