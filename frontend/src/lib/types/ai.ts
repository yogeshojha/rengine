export interface AiFeatureUsage {
	feature: string;
	label: string;
	calls: number;
	cached: number;
	failed: number;
	input_tokens: number;
	output_tokens: number;
	cache_read_tokens: number;
	cache_write_tokens: number;
	cost_usd: number | null;
	unpriced: number;
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
	cache_read_tokens: number;
	cache_write_tokens: number;
	cost_usd: number | null;
	cost_source: string | null;
	input_per_mtok: number | null;
	output_per_mtok: number | null;
	latency_ms: number;
	error: string | null;
}

export interface AiCallPage {
	items: AiCall[];
	has_more: boolean;
}

export interface AiUsage {
	calls: number;
	cost_usd: number | null;
	unpriced: number;
	failed: number;
	since: string | null;
	by_feature: AiFeatureUsage[];
}

export interface AiStatus {
	enabled: boolean;
	configured: boolean;
	connection_id: string | null;
	provider: string | null;
	model: string | null;
	workspace_id: string | null;
	base_url: string | null;
	key_masked: string | null;
	features: Record<string, boolean>;
	usage: AiUsage;
	cached_narratives: number;
}

export interface AiConnection {
	id: string;
	name: string;
	provider: string;
	model: string;
	base_url: string | null;
	workspace_id: string | null;
	key_masked: string | null;
	in_use: boolean;
	last_test_at: string | null;
	last_test_ok: boolean | null;
	last_test_message: string | null;
}

export interface AiConnectionCreate {
	name?: string;
	provider: string;
	api_key?: string;
	base_url?: string;
	model?: string;
	workspace_id?: string;
	use?: boolean;
}

export type AiConnectionUpdate = Partial<Omit<AiConnectionCreate, 'use'>>;

export interface AiModelsRequest {
	connection_id?: string;
	provider?: string;
	api_key?: string;
	base_url?: string;
	workspace_id?: string;
}

export interface AiModelOption {
	id: string;
	label: string;
	input_per_mtok: number | null;
	output_per_mtok: number | null;
	cache_read_per_mtok: number | null;
	cache_write_per_mtok: number | null;
	recommended: boolean;
}

export interface AiModelList {
	models: AiModelOption[];
	error: string | null;
}

export interface AiModel {
	id: string;
	label: string;
	note: string;
	input_per_mtok: number | null;
	output_per_mtok: number | null;
	cache_read_per_mtok: number | null;
	cache_write_per_mtok: number | null;
	context: number;
	recommended: boolean;
}

export interface AiProvider {
	key: string;
	label: string;
	key_hint: string;
	help: string;
	key_optional: boolean;
	needs_base_url: boolean;
	base_url_hint: string;
	workspace: boolean;
	default_model: string;
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
	features?: Record<string, boolean>;
}

export interface AiTestRequest {
	connection_id?: string;
	provider?: string;
	model?: string;
	api_key?: string;
	workspace_id?: string;
	base_url?: string;
}

export interface AiTestResult {
	success: boolean;
	message: string;
	model: string | null;
	latency_ms: number | null;
}

export interface AiOnboarding {
	enabled: boolean;
	provider?: string;
	api_key?: string;
	base_url?: string;
	workspace_id?: string;
	model?: string;
	features?: Record<string, boolean>;
}

export interface AiOnboardingRead {
	enabled: boolean;
	connection: AiConnection | null;
	features: Record<string, boolean>;
}
