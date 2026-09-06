import type { ScanStatus } from './scan';
import type { SeverityCount } from '$lib/utilities/vulns';

export const DASHBOARD_WINDOWS = [
	{ key: '24h', label: '24h', text: 'last 24 hours' },
	{ key: '7d', label: '7d', text: 'last 7 days' },
	{ key: '30d', label: '30d', text: 'last 30 days' }
] as const;
export type DashboardWindow = (typeof DASHBOARD_WINDOWS)[number]['key'];
export const DEFAULT_DASHBOARD_WINDOW: DashboardWindow = '7d';
export const windowText = (w: DashboardWindow) =>
	DASHBOARD_WINDOWS.find((x) => x.key === w)?.text ?? '';

export interface TakeoverCandidate {
	name: string;
	target_id: string;
	cname: string;
	provider: string;
	last_seen: string;
}

export interface TakeoverSignal {
	count: number;
	items: TakeoverCandidate[];
}

export interface SpoofableDomain {
	target_id: string;
	target_value: string;
	reason: string;
}

export interface SpoofableSignal {
	count: number;
	items: SpoofableDomain[];
}

export interface StaleTarget {
	target_id: string;
	target_value: string;
	target_type: string;
	last_scanned_at: string | null;
}

export interface StaleSignal {
	never_scanned: number;
	stale: number;
	items: StaleTarget[];
}

export interface DashboardSignals {
	takeover: TakeoverSignal;
	spoofable: SpoofableSignal;
	stale: StaleSignal;
}

export interface DashboardTargetCount {
	target_id: string;
	target_value: string;
	scan_id: string;
	count: number;
}

export interface ExpiringTarget {
	target_id: string;
	target_value: string;
	expires_at: string;
}

export interface FailedRun {
	target_id: string;
	target_value: string;
	scan_id: string;
	engine_name: string;
	error: string | null;
	at: string;
}

export interface DashboardSurfaceMetric {
	key: string;
	label: string;
	value: number;
	targets_covered: number;
	new_in_window: number;
}

export interface DashboardFinding {
	id: string;
	scan_id: string;
	target_id: string;
	target_value: string;
	template_id: string;
	name: string;
	severity: string;
	host: string | null;
	matched_at: string;
	host_count: number;
	is_kev: boolean;
	is_new: boolean;
	cve_ids: string[];
	epss_score: number | null;
	cvss_score: number | null;
	discovered_at: string;
}

export interface DashboardRisk {
	total: number;
	actionable: number;
	kev: number;
	new_in_window: number;
	suppressed: number;
	targets_affected: number;
	targets_scanned: number;
	by_severity: SeverityCount[];
	queue: DashboardFinding[];
}

export interface DashboardGeo {
	code: string;
	count: number;
	targets: DashboardTargetCount[];
}

export interface DashboardExposureBand {
	key: string;
	label: string;
	count: number;
	targets: number;
	query: string;
}

export interface DashboardExposedService {
	key: string;
	label: string;
	service_class: string;
	sensitive: boolean;
	count: number;
	query: string;
	targets: DashboardTargetCount[];
}

export interface DashboardExposure {
	services: number;
	addresses: number;
	targets: number;
	sensitive: number;
	sensitive_targets: number;
	non_web: number;
	bands: DashboardExposureBand[];
	top: DashboardExposedService[];
}

export interface DashboardCertSignal {
	count: number;
	query: string;
	targets: DashboardTargetCount[];
}

export interface DashboardCerts {
	expired: DashboardCertSignal;
	expiring: DashboardCertSignal;
}

export interface DashboardChangeRow {
	target_id: string;
	target_value: string;
	target_type: string;
	runs: number;
	last_scan_id: string;
	last_status: ScanStatus;
	last_at: string;
	new: Record<string, number>;
	new_scan: Record<string, string | null>;
	first: string[];
	gone_web_assets: number;
}

export interface DashboardDay {
	date: string;
	runs: number;
	failed: number;
	new: Record<string, number>;
}

export interface DashboardTargetSurface {
	key: string;
	covered: boolean;
	value: number | null;
	previous: number | null;
	delta: number | null;
	scan_id: string | null;
	scan_status: ScanStatus | null;
	observed_at: string | null;
}

export interface DashboardTargetRow {
	id: string;
	value: string;
	type: string;
	scans_total: number;
	last_scan_id: string | null;
	last_scan_status: ScanStatus | null;
	last_scan_at: string | null;
	surface: DashboardTargetSurface[];
	findings: number;
	actionable: number;
	kev: number;
	worst_severity: string | null;
	risk_scan_id: string | null;
	sensitive_services: number;
	services_scan_id: string | null;
	monitored: boolean;
}

export interface DashboardReadiness {
	worker_online: boolean;
	worker_concurrency: number | null;
	checks_ready: boolean;
	checks_total: number;
}

export interface DashboardOverview {
	generated_at: string;
	window: DashboardWindow;
	first_run: boolean;
	targets_total: number;
	targets_scanned: number;
	targets_never_scanned: number;
	targets_stale: number;
	targets_monitored: number;
	targets_by_type: Record<string, number>;
	runs_total: number;
	runs_in_window: number;
	failed_in_window: number;
	last_completed_at: string | null;
	surface: DashboardSurfaceMetric[];
	risk: DashboardRisk;
	signals: DashboardSignals;
	never_scanned: StaleTarget[];
	stale: StaleTarget[];
	sensitive: DashboardTargetCount[];
	expiring: ExpiringTarget[];
	failed_runs: FailedRun[];
	exposure: DashboardExposure;
	certs: DashboardCerts;
	geography: DashboardGeo[];
	geo_total: number;
	changes: DashboardChangeRow[];
	daily: DashboardDay[];
	targets: DashboardTargetRow[];
}

export interface DashboardDiscoverySource {
	target_id: string;
	target_value: string;
	scan_id: string;
	seen_on: string;
	hostname_count: number;
}

export interface DashboardDiscoveredDomain {
	domain: string;
	hostname_count: number;
	hostnames: string[];
	sources: DashboardDiscoverySource[];
}

export interface DashboardDiscovery {
	targets_examined: number;
	domains: DashboardDiscoveredDomain[];
}
