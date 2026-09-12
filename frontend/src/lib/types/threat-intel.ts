export interface ThreatFeedRead {
	kind: string;
	label: string;
	tagline: string;
	description: string;
	source: string;
	source_url: string;
	url: string;
	license: string;
	rows_noun: string;
	status: string;
	status_label: string;
	rows: number;
	version: string | null;
	bytes: number;
	duration_ms: number;
	error: string | null;
	last_synced_at: string | null;
	age_hours: number | null;
}

export interface IntelCoverage {
	findings: number;
	with_cve: number;
	scored: number;
	kev: number;
	ransomware: number;
	overdue: number;
	weaponised: number;
	untestable: number;
	enriched: number;
	bands: Record<string, number>;
}

export interface IntelChange {
	vulnerability_id: string;
	scan_id: string;
	target_id: string;
	target_value: string | null;
	template_name: string;
	severity: string;
	cve: string;
	host: string | null;
	matched_at: string | null;
	change: string;
	epss_before: number | null;
	epss_after: number | null;
	changed_at: string | null;
}

export interface SignalFinding {
	vulnerability_id: string;
	scan_id: string;
	target_id: string;
	target_value: string | null;
	template_name: string;
	severity: string;
	host: string | null;
	matched_at: string | null;
	cve: string;
	epss_score: number | null;
	exploit_score: number;
	reason: string;
}

export interface ThreatIntelStatus {
	auto_sync: boolean;
	feeds: ThreatFeedRead[];
	coverage: IntelCoverage;
	ready: boolean;
	syncing: boolean;
	provider_enabled: boolean;
	provider_cached: number;
	last_applied_at: string | null;
	recent_changes: IntelChange[];
}

export interface SyncResult {
	queued: boolean;
	feeds: string[];
	detail: string | null;
}

export interface PocRef {
	url: string;
	source: string | null;
	added_at: string | null;
}

export interface KevDetail {
	vendor: string | null;
	product: string | null;
	name: string | null;
	short_description: string | null;
	required_action: string | null;
	notes: string | null;
	cwes: string[];
	known_ransomware: boolean;
	date_added: string | null;
	due_date: string | null;
	overdue_days: number | null;
}

export interface ExposureProduct {
	id: string;
	hosts: number;
}

export interface CveIntelRead {
	cve: string;
	epss_score: number | null;
	epss_percentile: number | null;
	band: string | null;
	band_label: string | null;
	is_kev: boolean;
	kev: KevDetail | null;
	enriched: boolean;
	description: string | null;
	remediation: string | null;
	weaknesses: { cwe_id: string; cwe_name: string }[];
	pocs: PocRef[];
	poc_count: number;
	poc_first_seen: string | null;
	template_available: boolean | null;
	is_remote: boolean | null;
	needs_auth: boolean | null;
	patch_available: boolean | null;
	vendor_kev: boolean;
	exposure_hosts: number | null;
	exposure_products: ExposureProduct[];
	hackerone_rank: number | null;
	hackerone_reports: number | null;
	published_at: string | null;
	fetched_at: string | null;
}

export interface SignalRead {
	kind: string;
	label: string;
	help: string;
	tone: string;
	weight: number;
	reason: string;
	evidence: Record<string, unknown>;
}

export interface FindingIntel {
	exploit_score: number;
	signals: SignalRead[];
	cves: CveIntelRead[];
	stale: boolean;
}
