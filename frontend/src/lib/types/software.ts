import type { QueryError } from './asset-query';

export interface SoftwareCaveat {
	kind: string;
	label: string;
}

export interface SoftwareCve {
	id: string;
	scan_id: string;
	target_id: string;
	target_value: string | null;
	cve: string;
	name: string;
	version: string;
	vendor: string;
	product: string;
	cpe: string;
	version_source: string;
	version_source_label: string;
	severity: string;
	cvss_score: number | null;
	epss_score: number | null;
	epss_percentile: number | null;
	band: string | null;
	is_kev: boolean;
	kev_ransomware: boolean;
	kev_due_date: string | null;
	exploit_score: number;
	intel_kinds: string[];
	confidence: string;
	confidence_label: string;
	caveats: SoftwareCaveat[];
	evidence: string;
	evidence_label: string;
	description: string | null;
	host: string | null;
	ip: string | null;
	port: number | null;
	url: string | null;
	http_asset_id: string | null;
	port_id: string | null;
	discovered_at: string;
	is_new: boolean;
}

export interface SoftwarePage {
	items: SoftwareCve[];
	total: number;
	total_capped: boolean;
	error?: QueryError | null;
}

export interface SoftwareFacet {
	key: string;
	label: string;
	count: number;
}

export interface SoftwareFacets {
	severity: SoftwareFacet[];
	confidence: SoftwareFacet[];
	source: SoftwareFacet[];
	caveat: SoftwareFacet[];
	evidence: SoftwareFacet[];
	product: SoftwareFacet[];
}

export interface SoftwareComponent {
	name: string;
	version: string | null;
	vendor: string | null;
	product: string | null;
	version_source: string;
	mapped: boolean;
	cves: number;
	assets: number;
}

export interface SoftwareCoverage {
	components: number;
	mapped: number;
	unmapped: number;
	matched: number;
	findings: number;
	feed_ready: boolean;
	feed_age_hours: number | null;
	stale: boolean;
	unmapped_names: SoftwareComponent[];
}

export interface SoftwareFilter {
	q?: string;
	limit?: number;
	offset?: number;
	sort?: string;
	direction?: string;
}
