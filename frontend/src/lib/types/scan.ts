import type { HttpProtocol } from './scan-context';

export const SCAN_STATUSES = [
	'pending',
	'running',
	'completed',
	'failed',
	'cancelled'
] as const;
export type ScanStatus = (typeof SCAN_STATUSES)[number];

export interface ResolvedScanConfig {
	target_value: string;
	target_type: string;
	headers: Record<string, string>;
	per_tool_rate_limits: Record<string, number>;
	global_rate_limit_ceiling: number | null;
	global_threads: number;
	resolved_threads: Record<string, number>;
	resolved_timeouts: Record<string, number>;
	thread_multiplier: number;
	timeout_multiplier: number;
	phases: Record<string, Record<string, unknown>>;
	excluded_subdomains: string[];
	excluded_paths: string[];
	excluded_ips: string[];
	included_subdomains: string[];
	follow_redirects: boolean | null;
	http_protocol: HttpProtocol;
	global_http_crawl: boolean;
	intensity: string;
}

export interface ScanRead {
	id: string;
	project_id: string;
	target_id: string;
	engine_id: string;
	engine_name: string;
	context_id: string | null;
	context_name: string | null;
	execution_config: ResolvedScanConfig;
	auth_summary: string;
	status: ScanStatus;
	subdomains_found: number;
	ips_found: number;
	open_ports_found: number;
	vulnerabilities_found: number;
	endpoints_found: number;
	error: string | null;
	created_by: string;
	created_at: string;
	started_at: string | null;
	completed_at: string | null;
}

export interface ScanCreate {
	engine_id: string;
	context_id?: string | null;
	target_id: string;
}

export const PREVIEW_TOOL_STATUSES = [
	'will_run',
	'skipped_disabled',
	'skipped_needs_key'
] as const;
export type PreviewToolStatus = (typeof PREVIEW_TOOL_STATUSES)[number];

export interface PreviewTool {
	capability: string;
	label: string;
	status: PreviewToolStatus;
	reason?: string | null;
	rate?: number | null;
	threads?: number | null;
	timeout?: number | null;
}

export interface PreviewPhase {
	phase: string;
	label: string;
	tools: PreviewTool[];
}

export interface PreviewSummary {
	auth_summary: string;
	custom_header_names: string[];
	rate_summary: string;
	thread_multiplier: number;
	timeout_multiplier: number;
	http_protocol: HttpProtocol;
	follow_redirects: boolean | null;
	excluded_subdomains_count: number;
	excluded_paths_count: number;
	excluded_ips_count: number;
	excluded_subdomains: string[];
	excluded_paths: string[];
	excluded_ips: string[];
	included_subdomains: string[];
	estimated_duration_seconds: number;
	estimated_duration_human: string;
}

export interface ScanPreview {
	target_id: string;
	target_value: string;
	target_type: string;
	engine_id: string;
	engine_name: string;
	context_id: string | null;
	context_name: string | null;
	phases: PreviewPhase[];
	summary: PreviewSummary;
	warnings: string[];
}
