export interface CveLadderStep {
	evidence: string;
	label: string;
	help: string;
	count: number;
	software: number;
	findings: number;
}

export interface CveLocation {
	dimension: string;
	id: string;
	scan_id: string;
	target_id: string;
	target_value: string | null;
	host: string | null;
	ip: string | null;
	port: number | null;
	url: string | null;
	evidence: string;
	evidence_label: string;
	basis: string;
	detail: string | null;
	severity: string;
	state: string | null;
	confidence: string | null;
	caveats: string[];
	discovered_at: string;
}

export interface CveTargetRow {
	target_id: string;
	target_value: string;
	target_type: string;
	assets: number;
	software: number;
	findings: number;
	first_seen: string | null;
}

export interface CveExposure {
	cve: string;
	known: boolean;
	severity: string | null;
	cvss_score: number | null;
	cvss_vector: string | null;
	description: string | null;
	published_at: string | null;
	last_modified_at: string | null;
	epss_score: number | null;
	epss_percentile: number | null;
	band: string | null;
	is_kev: boolean;
	kev_ransomware: boolean;
	kev_date_added: string | null;
	kev_due_date: string | null;
	kev_required_action: string | null;
	exploit_score: number;
	intel_kinds: string[];
	assets: number;
	targets: number;
	software_rows: number;
	finding_rows: number;
	suppressed: number;
	ladder: CveLadderStep[];
	first_seen: string | null;
	software_scans: number;
	finding_scans: number;
	corpus_ready: boolean;
	by_target: CveTargetRow[];
	locations: CveLocation[];
	locations_total: number;
	generated_at: string;
}

export interface CveIndexRow {
	cve: string;
	severity: string | null;
	cvss_score: number | null;
	epss_score: number | null;
	is_kev: boolean;
	kev_ransomware: boolean;
	exploit_score: number;
	assets: number;
	targets: number;
	software: number;
	findings: number;
	top_evidence: string;
	first_seen: string | null;
}

export interface CveIndex {
	items: CveIndexRow[];
	total: number;
	matched: number;
	page: number;
	size: number;
	severity_counts: Record<string, number>;
	software_scans: number;
	finding_scans: number;
	corpus_ready: boolean;
	generated_at: string;
}
