import type { ScanStatus } from './scan';
import type { SeverityCount } from '$lib/utilities/vulns';
import type { ActivityKind, FunnelStep, QueueTier } from '$lib/config/dashboard';

export const DASHBOARD_WINDOWS = [
	{ key: '7d', label: '7d', text: 'last 7 days', days: 7 },
	{ key: '14d', label: '14d', text: 'last 14 days', days: 14 },
	{ key: '30d', label: '30d', text: 'last 30 days', days: 30 }
] as const;
export type DashboardWindow = (typeof DASHBOARD_WINDOWS)[number]['key'];
export const DEFAULT_DASHBOARD_WINDOW: DashboardWindow = '7d';
export const windowDays = (w: DashboardWindow) =>
	DASHBOARD_WINDOWS.find((x) => x.key === w)?.days ?? 7;
export const DASHBOARD_SLICES = [
	'tech',
	'ipFacets',
	'intel',
	'changes',
	'hosting',
	'exposures',
	'software',
	'hygiene',
	'posture',
	'shared',
	'activity',
	'programs',
	'discovery',
	'surfaceRisk'
] as const;
export type DashboardSlice = (typeof DASHBOARD_SLICES)[number];

export const DASHBOARD_SLICE_LABELS: Record<DashboardSlice, string> = {
	tech: 'Technology',
	ipFacets: 'Geography and networks',
	intel: 'Exploitation',
	changes: 'Exploitation changes',
	hosting: 'Hosting',
	exposures: 'Exposures',
	software: 'Software CVEs',
	hygiene: 'Web hygiene',
	posture: 'Domain posture',
	shared: 'Shared across targets',
	activity: 'Activity',
	programs: 'Programs',
	discovery: 'Untracked domains',
	surfaceRisk: 'Surface against risk'
};

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
	zone: string;
	reason: string;
	check: string;
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

export interface DashboardEvidenceCell {
	severity: string;
	evidence: string;
	count: number;
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
	evidence: string | null;
	tier: QueueTier;
	replays: number;
}

export interface DashboardRisk {
	total: number;
	actionable: number;
	kev: number;
	ransomware: number;
	overdue: number;
	newly_exploited: number;
	new_in_window: number;
	suppressed: number;
	targets_affected: number;
	targets_scanned: number;
	by_severity: SeverityCount[];
	evidence: DashboardEvidenceCell[];
	tiers: Record<QueueTier, number>;
	queue: DashboardFinding[];
}

export interface DashboardFunnelStep {
	key: FunnelStep;
	label: string;
	count: number;
	new_in_window: number | null;
	query: string | null;
	tab: string | null;
}

export interface DashboardFunnel {
	steps: DashboardFunnelStep[];
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

export interface DashboardCertBucket {
	key: string;
	label: string;
	count: number;
	query: string;
}

export interface DashboardCerts {
	expired: DashboardCertSignal;
	expiring: DashboardCertSignal;
	buckets: DashboardCertBucket[];
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
	outcomes: Record<string, number>;
	new: Record<string, number>;
	retired: Record<string, number>;
	total: Record<string, number>;
	findings: Record<string, number>;
}

export interface DashboardTargetRow {
	id: string;
	value: string;
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
	funnel: DashboardFunnel;
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

export interface SurfaceRiskTarget {
	target_id: string;
	target_value: string;
	target_type: string;
	names: number;
	live: number;
	findings: number;
	actionable: number;
	act: number;
	kev: number;
	by_severity: Record<string, number>;
	scan_id: string | null;
	scan_status: ScanStatus | null;
	last_at: string | null;
	organizations: string[];
	tags: string[];
}

export interface DashboardSurfaceRisk {
	targets_total: number;
	scanned: number;
	live: number;
	findings: number;
	actionable: number;
	act: number;
	rows: SurfaceRiskTarget[];
}

export interface SurfaceRiskFilters {
	organizationId?: string | null;
	tagId?: string | null;
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

// fronting split of resolving web assets
export const HOSTING_QUERIES = {
	resolved: 'is:resolved',
	edge: 'is:cdn',
	cloud: 'is:cloud',
	direct: 'is:resolved and not is:cdn and not is:cloud'
} as const;

export interface HostingSplit {
	resolved: number;
	edge: number;
	cloud: number;
	direct: number;
	capped: Record<string, boolean>;
}

export interface DashboardEvent {
	at: string;
	kind: ActivityKind;
	label: string;
	title: string;
	detail: string | null;
	tone: 'neutral' | 'hot' | 'new';
	scan_id: string | null;
	target_id: string | null;
	watch_id: string | null;
	platform: string | null;
	handle: string | null;
	connector_id: string | null;
}

export interface DashboardActivity {
	window: DashboardWindow;
	events: DashboardEvent[];
}

export interface DashboardDayKinds {
	date: string;
	kinds: Record<string, number>;
}

export interface DashboardWatchAlert {
	watch_id: string;
	name: string;
	program_name: string;
	at: string;
}

export interface DashboardLadderStep {
	state: string;
	label: string;
	count: number;
}

export interface DashboardWatches {
	total: number;
	active: number;
	daily: DashboardDayKinds[];
	ladder: DashboardLadderStep[];
	latest_alert: DashboardWatchAlert | null;
	stream_running: boolean;
	stream_certificates: number;
	last_certificate_at: string | null;
}

export interface DashboardBrowsing {
	connectors: number;
	live: number;
	requests_seen: number;
	browsed: number;
	unseen: number;
	new_params: number;
	flagged: number;
	last_seen_at: string | null;
	daily: DashboardDayKinds[];
}

export interface DashboardPrograms {
	window: DashboardWindow;
	programs_total: number;
	by_platform: Record<string, number>;
	watched: number;
	events_in_window: Record<string, number>;
	events_daily: DashboardDayKinds[];
	watches: DashboardWatches;
	browsing: DashboardBrowsing;
}
