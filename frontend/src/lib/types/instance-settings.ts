export interface InstanceSettings {
	id: string;
	singleton_key: string;
	instance_name: string;
	timezone: string;
	mode: string;
	onboarding_completed: boolean;
	onboarding_completed_at: string | null;
	onboarding_completed_by: string | null;
	onboarding_step: number;
	onboarding_state: Record<string, unknown>;
	scan_history_retention_days: number;
	screenshot_retention_days: number;
	ai_enabled: boolean;
	ai_provider: string | null;
	ai_model: string | null;
	ai_api_key_masked: string | null;
	ai_configured: boolean;
	ai_features: Record<string, boolean>;
	capabilities: string[];
	created_at: string;
	updated_at: string;
}

export interface InstanceSettingsUpdate {
	instance_name?: string;
	timezone?: string;
	mode?: string;
	scan_history_retention_days?: number;
	screenshot_retention_days?: number;
	ai_enabled?: boolean;
	ai_provider?: string | null;
	ai_model?: string | null;
	ai_api_key?: string | null;
	ai_features?: Record<string, boolean>;
}
