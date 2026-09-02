import type { HttpProtocol } from './scan-context';
import type { StageConfig } from './scan-engine';

export const SCAN_STATUSES = ['pending', 'running', 'completed', 'failed', 'cancelled'] as const;
export type ScanStatus = (typeof SCAN_STATUSES)[number];

export const SCAN_ACTIVITY_STATUSES = [
	'pending',
	'running',
	'success',
	'failed',
	'skipped',
	'aborted'
] as const;
export type ScanActivityStatus = (typeof SCAN_ACTIVITY_STATUSES)[number];

export const ACTIVITY_TERMINAL_STATUSES: readonly ScanActivityStatus[] = [
	'success',
	'failed',
	'skipped',
	'aborted'
];

export const SCAN_COUNT_COLUMNS = {
	subdomains: 'subdomains_found',
	ips: 'ips_found',
	open_ports: 'open_ports_found',
	http_assets: 'http_assets_found',
	vulnerabilities: 'vulnerabilities_found',
	endpoints: 'endpoints_found'
} as const satisfies Record<string, keyof ScanRead>;

export interface ScanActivityRead {
	id: string;
	scan_id: string;
	name: string;
	title: string;
	status: ScanActivityStatus;
	error: string | null;
	result: Record<string, number | string>;
	command_count: number;
	started_at: string | null;
	completed_at: string | null;
	duration_seconds: number | null;
	created_at: string;
}

export interface ScanCommandRead {
	id: string;
	scan_id: string;
	activity_id: string | null;
	tool: string;
	command: string;
	status: ScanActivityStatus;
	return_code: number | null;
	error: string | null;
	duration_seconds: number | null;
	started_at: string;
	completed_at: string | null;
}

export interface ScanCommandDetail extends ScanCommandRead {
	output: string | null;
}

export const SCAN_SORT_KEYS = [
	'started',
	'duration',
	'status',
	'subdomains',
	'vulnerabilities'
] as const;
export type ScanSortKey = (typeof SCAN_SORT_KEYS)[number];

export type ScanSortDir = 'asc' | 'desc';

export const SCAN_TIME_RANGES = [
	{ key: 'all', label: 'All time' },
	{ key: '24h', label: 'Last 24 hours' },
	{ key: '7d', label: 'Last 7 days' },
	{ key: '30d', label: 'Last 30 days' }
] as const;
export type ScanTimeRange = (typeof SCAN_TIME_RANGES)[number]['key'];

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
	stages: Record<string, StageConfig>;
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
	schedule_id: string | null;
	schedule_type: string | null;
	execution_config: ResolvedScanConfig;
	auth_summary: string;
	status: ScanStatus;
	subdomains_found: number;
	ips_found: number;
	open_ports_found: number;
	http_assets_found: number;
	vulnerabilities_found: number;
	endpoints_found: number;
	error: string | null;
	created_by: string;
	created_at: string;
	started_at: string | null;
	completed_at: string | null;
	duration_seconds: number | null;
	new_subdomains: number | null;
	gone_subdomains: number | null;
	prev_subdomains_found: number | null;
	is_first_scan: boolean | null;
}

export interface ScanCreate {
	engine_id: string;
	context_id?: string | null;
	target_id: string;
}

export const MAX_SCAN_BATCH = 500;

export interface ScanBatchCreate {
	engine_id: string;
	context_id?: string | null;
	target_ids: string[];
}

export const PREVIEW_TOOL_STATUSES = ['will_run', 'skipped_disabled', 'skipped_needs_key'] as const;
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
	proxy_name: string | null;
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

export interface ScanStatusCounts {
	pending: number;
	running: number;
	completed: number;
	failed: number;
	cancelled: number;
}

export interface ScanDailyCount {
	date: string;
	count: number;
	completed: number;
	failed: number;
	cancelled: number;
	running: number;
	pending: number;
	new_subdomains: number;
}

export const SCAN_CHANGE_WINDOWS = [
	{ key: '6h', label: '6h' },
	{ key: '12h', label: '12h' },
	{ key: '24h', label: '24h' },
	{ key: '7d', label: '7d' },
	{ key: '30d', label: '30d' }
] as const;
export type ScanChangeWindow = (typeof SCAN_CHANGE_WINDOWS)[number]['key'];

export interface ScanChanges {
	window: ScanChangeWindow;
	new_subdomains: number;
	retired_subdomains: number;
	targets_changed: number;
	scans_run: number;
	failed_runs: number;
}

export interface ScanTargetGroup {
	target_id: string;
	target_value: string;
	target_type: string;
	scan_count: number;
	last_scan_at: string;
	last_status: ScanStatus;
	running: number;
	trend: number[];
}

export interface ScanFacet {
	name: string;
	count: number;
}

export interface ScanExportRow {
	target: string;
	status: string;
	engine: string;
	context: string | null;
	subdomains: number;
	ips: number;
	open_ports: number;
	vulnerabilities: number;
	endpoints: number;
	duration_seconds: number | null;
	started_at: string | null;
	completed_at: string | null;
	created_at: string;
}

export interface ScanStats {
	total: number;
	running: number;
	by_status: ScanStatusCounts;
	last_scan_at: string | null;
	avg_duration_seconds: number | null;
	success_rate: number | null;
	daily: ScanDailyCount[];
	engines: ScanFacet[];
	contexts: ScanFacet[];
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
