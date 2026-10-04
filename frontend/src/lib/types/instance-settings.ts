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
	cert_recheck_enabled: boolean;
	infostealer_lookups: boolean;
	concurrent_scans: number;
	concurrent_scans_auto: number | null;
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
	cert_recheck_enabled?: boolean;
	infostealer_lookups?: boolean;
	concurrent_scans?: number;
}
