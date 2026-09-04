import type { QueryError } from '$lib/types/asset-query';
import type { SortOption } from '$lib/components/scans/results/table/columns';
import type { Facet } from './scan-insights';
import {
	PROTOCOL_LABELS,
	SCANNER_LABELS,
	SEVERITY_LABELS,
	SEVERITY_ORDER,
	VULN_STATE_LABELS
} from '$lib/config/vulnerabilities';

export interface AssetContext {
	host: string | null;
	url: string | null;
	status_code: number | null;
	title: string | null;
	webserver: string | null;
	tech: string[];
	screenshot_path: string | null;
	ip: string | null;
	asn: number | null;
	asn_org: string | null;
	country: string | null;
	is_cdn: boolean;
	cdn_name: string | null;
	waf: string | null;
	open_ports: number;
	service_name: string | null;
}

export interface Corroboration {
	template_id: string;
	template_name: string;
	severity: string;
	scanner: string;
	basis: string;
	shared: string[];
}

export interface VulnerabilityRead {
	id: string;
	scan_id: string;
	target_id: string;
	fingerprint: string;
	scanner: string;
	template_id: string;
	template_name: string;
	template_path: string | null;
	template_url: string | null;
	severity: string;
	protocol: string;
	matcher_name: string | null;
	extractor_name: string | null;
	extracted_results: string[];
	description: string | null;
	impact: string | null;
	remediation: string | null;
	references: string[];
	tags: string[];
	authors: string[];
	cve_ids: string[];
	cwe_ids: string[];
	cvss_metrics: string | null;
	cvss_score: number | null;
	epss_score: number | null;
	epss_percentile: number | null;
	cpe: string | null;
	is_kev: boolean;
	matched_at: string;
	host: string | null;
	ip: string | null;
	port: number | null;
	scheme: string | null;
	url: string | null;
	path: string | null;
	curl_command: string | null;
	request: string | null;
	response: string | null;
	interaction: Record<string, unknown>;
	observed_at: string | null;
	discovered_at: string;
	state: string;
	note: string | null;
	is_new: boolean;
	host_count: number;
	sets: string[];
	corroborated_by: Corroboration[];
	colocated: number;
	asset: AssetContext | null;
}

export interface IssueRead {
	template_id: string;
	template_name: string;
	template_url: string | null;
	scanner: string;
	severity: string;
	protocol: string;
	tags: string[];
	sets: string[];
	cve_ids: string[];
	cwe_ids: string[];
	cvss_score: number | null;
	epss_score: number | null;
	is_kev: boolean;
	description: string | null;
	remediation: string | null;
	findings: number;
	hosts: number;
	addresses: number;
	locations: number;
	sample_hosts: string[];
	corroborated: number;
	new_count: number;
	states: Record<string, number>;
	first_seen: string;
	last_seen: string;
	sample_id: string;
}

export interface IssuePage {
	items: IssueRead[];
	total: number;
	total_capped: boolean;
	error: QueryError | null;
}

export interface BulkTriageResult {
	state: string;
	fingerprints: number;
	updated: number;
}

export const VULN_VIEWS = [
	{ key: 'issues', label: 'Issues' },
	{ key: 'findings', label: 'Findings' }
] as const;
export type VulnView = (typeof VULN_VIEWS)[number]['key'];
export const DEFAULT_VULN_VIEW: VulnView = 'issues';

export interface VulnQuery {
	search: string;
	severities: string[];
	states: string[];
	protocols: string[];
	templates: string[];
	tags: string[];
	hosts: string[];
	scanners: string[];
	kevOnly: boolean;
	cveOnly: boolean;
	newOnly: boolean;
	corroboratedOnly: boolean;
	includeInfo: boolean;
	includeSuppressed: boolean;
}

export function emptyVulnQuery(): VulnQuery {
	return {
		search: '',
		severities: [],
		states: [],
		protocols: [],
		templates: [],
		tags: [],
		hosts: [],
		scanners: [],
		kevOnly: false,
		cveOnly: false,
		newOnly: false,
		corroboratedOnly: false,
		includeInfo: true,
		includeSuppressed: false
	};
}

export interface VulnFilter {
	q: string | null;
	severities: string[];
	states: string[];
	protocols: string[];
	templates: string[];
	tags: string[];
	hosts: string[];
	scanners: string[];
	kev: boolean;
	cve: boolean;
	new: boolean;
	corroborated: boolean;
	include_info: boolean;
	include_suppressed: boolean;
	sort: string;
	order: 'asc' | 'desc';
	limit: number;
	offset: number;
}

export interface VulnSearchResult {
	items: VulnerabilityRead[];
	total: number;
	total_capped: boolean;
	error: QueryError | null;
}

export interface VulnFacet {
	name: string;
	count: number;
	label: string | null;
}

export interface VulnFacetSet {
	severity: VulnFacet[];
	state: VulnFacet[];
	protocol: VulnFacet[];
	template: VulnFacet[];
	tag: VulnFacet[];
	host: VulnFacet[];
	scanner: VulnFacet[];
	issue_severity: VulnFacet[];
}

export const EMPTY_VULN_FACETS: VulnFacetSet = {
	severity: [],
	state: [],
	protocol: [],
	template: [],
	tag: [],
	host: [],
	scanner: [],
	issue_severity: []
};

export interface SeverityCount {
	severity: string;
	label: string;
	count: number;
}

export interface CoverageRead {
	id: string;
	scanner: string;
	group: string;
	status: string;
	severities: string[];
	template_sets: string[];
	templates_selected: number | null;
	templates_loaded: number | null;
	custom_templates: number;
	hosts_total: number;
	hosts_scanned: number | null;
	hosts_dropped: { host: string; reason: string }[];
	requests_sent: number | null;
	matched: number | null;
	errors: number | null;
	rate_limit: number | null;
	duration_seconds: number | null;
	error: string | null;
}

export interface RankedFinding {
	id: string;
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
	signals: string[];
}

export interface VulnHostRow {
	host: string;
	total: number;
	worst: string;
	counts: SeverityCount[];
	query: string;
}

export interface ScanVulnerabilities {
	ran: boolean;
	total: number;
	issues: number;
	actionable: number;
	new_count: number;
	kev_count: number;
	cve_count: number;
	suppressed: number;
	by_severity: SeverityCount[];
	headline: string;
	headline_detail: string;
	headline_query: string;
	headline_tone: string;
	affected_hosts: number;
	scanned_hosts: number;
	top_findings: RankedFinding[];
	top_hosts: VulnHostRow[];
	coverage: CoverageRead[];
	templates_run: number | null;
	requests_sent: number | null;
	duration_seconds: number | null;
}

export interface TriageResult {
	fingerprint: string;
	state: string;
	note: string | null;
	updated: number;
}

// the count tabs are the severity partition; findings sort worst-first by default
export const SEVERITY_TABS: { key: string; label: string }[] = [
	{ key: 'all', label: 'All' },
	...SEVERITY_ORDER.filter((s) => s !== 'unknown').map((key) => ({
		key,
		label: SEVERITY_LABELS[key]
	}))
];

export const VULN_SORTS: SortOption[] = [
	{ key: 'risk', label: 'Risk' },
	{ key: 'severity', label: 'Severity' },
	{ key: 'name', label: 'Finding' },
	{ key: 'template', label: 'Check' },
	{ key: 'host', label: 'Host' },
	{ key: 'cvss', label: 'CVSS' },
	{ key: 'epss', label: 'EPSS' },
	{ key: 'seen', label: 'First seen' }
];

export const ISSUE_SORTS: SortOption[] = [
	{ key: 'risk', label: 'Risk' },
	{ key: 'severity', label: 'Severity' },
	{ key: 'name', label: 'Finding' },
	{ key: 'host', label: 'Hosts affected' },
	{ key: 'findings', label: 'Findings' },
	{ key: 'cvss', label: 'CVSS' },
	{ key: 'epss', label: 'EPSS' },
	{ key: 'seen', label: 'First seen' }
];

export function vulnActiveFacetCount(q: VulnQuery): number {
	return (
		q.severities.length +
		q.states.length +
		q.protocols.length +
		q.templates.length +
		q.tags.length +
		q.hosts.length +
		q.scanners.length +
		(q.kevOnly ? 1 : 0) +
		(q.cveOnly ? 1 : 0) +
		(q.newOnly ? 1 : 0) +
		(q.corroboratedOnly ? 1 : 0) +
		(q.includeInfo ? 0 : 1) +
		(q.includeSuppressed ? 1 : 0)
	);
}

export interface VulnFilterChip {
	id: string;
	label: string;
	remove: (q: VulnQuery) => VulnQuery;
}

type ListKey = 'severities' | 'states' | 'protocols' | 'templates' | 'tags' | 'hosts' | 'scanners';

export function vulnQueryChips(q: VulnQuery, facets: VulnFacetSet): VulnFilterChip[] {
	const chips: VulnFilterChip[] = [];
	const list = (key: ListKey, fmt: (v: string) => string) => {
		for (const v of q[key])
			chips.push({
				id: `${key}:${v}`,
				label: fmt(v),
				remove: (x) => ({ ...x, [key]: x[key].filter((o) => o !== v) })
			});
	};
	list('severities', (v) => SEVERITY_LABELS[v] ?? v);
	list('states', (v) => VULN_STATE_LABELS[v] ?? v);
	list('protocols', (v) => PROTOCOL_LABELS[v] ?? v);
	list('templates', (v) => v);
	list('tags', (v) => v);
	list('hosts', (v) => v);
	list('scanners', (v) => SCANNER_LABELS[v] ?? v);
	if (q.kevOnly)
		chips.push({ id: 'kev', label: 'Known exploited', remove: (x) => ({ ...x, kevOnly: false }) });
	if (q.cveOnly)
		chips.push({ id: 'cve', label: 'Has a CVE', remove: (x) => ({ ...x, cveOnly: false }) });
	if (q.newOnly)
		chips.push({ id: 'new', label: 'New this scan', remove: (x) => ({ ...x, newOnly: false }) });
	if (q.corroboratedOnly)
		chips.push({
			id: 'corroborated',
			label: 'Confirmed by another check',
			remove: (x) => ({ ...x, corroboratedOnly: false })
		});
	if (!q.includeInfo)
		chips.push({
			id: 'info',
			label: 'Info hidden',
			remove: (x) => ({ ...x, includeInfo: true })
		});
	if (q.includeSuppressed)
		chips.push({
			id: 'suppressed',
			label: 'Reviewed findings shown',
			remove: (x) => ({ ...x, includeSuppressed: false })
		});
	void facets;
	return chips;
}

export function compileVulnQuery(
	q: VulnQuery,
	sortKey: string,
	dir: 1 | -1,
	offset: number,
	limit: number
): VulnFilter {
	return {
		q: q.search.trim() || null,
		severities: [...q.severities],
		states: [...q.states],
		protocols: [...q.protocols],
		templates: [...q.templates],
		tags: [...q.tags],
		hosts: [...q.hosts],
		scanners: [...q.scanners],
		kev: q.kevOnly,
		cve: q.cveOnly,
		new: q.newOnly,
		corroborated: q.corroboratedOnly,
		include_info: q.includeInfo,
		include_suppressed: q.includeSuppressed,
		sort: sortKey,
		order: dir === 1 ? 'asc' : 'desc',
		limit,
		offset
	};
}

export function facetsAsRecord(facets: VulnFacetSet): Record<string, Facet[]> {
	const out: Record<string, Facet[]> = {};
	for (const [key, values] of Object.entries(facets) as [string, VulnFacet[]][]) {
		out[key] = values.map((f) => ({ value: f.name, label: f.label ?? f.name, count: f.count }));
	}
	return out;
}

export function locationLabel(v: VulnerabilityRead): string {
	const at = v.matched_at || v.url || v.host || '';
	try {
		const url = new URL(at);
		return `${url.pathname}${url.search}` || '/';
	} catch {
		return at;
	}
}

export function originLabel(v: VulnerabilityRead): string {
	const at = v.matched_at || v.url || '';
	try {
		const url = new URL(at);
		return url.host;
	} catch {
		return v.host ?? at;
	}
}

export function epssPercent(value: number | null | undefined): string | null {
	if (value === null || value === undefined) return null;
	return `${Math.round(value * 100)}%`;
}
