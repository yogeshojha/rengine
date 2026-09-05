import type { QueryError } from '$lib/types/asset-query';
import type { SortOption } from '$lib/components/scans/results/table/columns';
import {
	ENDPOINT_CLASS_LABELS,
	ENDPOINT_CLASS_ORDER,
	INTEREST_LABELS,
	SOURCE_LABELS,
	STATUS_CLASS_LABELS
} from '$lib/config/endpoints';

export interface SourceEvidence {
	source: string;
	label: string;
	kind: string;
	detail: string | null;
	found_on: string | null;
	observed_at: string | null;
}

export interface EndpointRead {
	id: string;
	scan_id: string;
	target_id: string;
	signature: string;
	url: string;
	host: string;
	port: number;
	scheme: string;
	path: string;
	dir_path: string;
	filename: string | null;
	extension: string | null;
	depth: number;
	params: string[];
	param_count: number;
	variants: number;
	more_variants: boolean;
	methods: string[];
	sources: string[];
	primary_source: string;
	evidence: SourceEvidence[];
	found_on: string | null;
	is_probed: boolean;
	status_code: number | null;
	content_type: string | null;
	content_length: number | null;
	title: string | null;
	words: number | null;
	lines: number | null;
	response_time: number | null;
	redirect_location: string | null;
	tech: string[];
	endpoint_class: string;
	interest: string[];
	http_asset_id: string | null;
	subdomain_id: string | null;
	archive_last_seen: string | null;
	discovered_at: string;
	is_new: boolean;
}

export interface EndpointDetail extends EndpointRead {
	param_samples: Record<string, string>[];
	discovery: Record<string, { at?: string; detail?: string; found_on?: string }>;
	content_hash: string | null;
	siblings: number;
}

export interface TreeNode {
	key: string;
	name: string;
	path: string;
	host: string | null;
	kind: string;
	depth: number;
	direct_count: number;
	subtree_count: number;
	child_count: number;
	hosts: number;
	status_mix: Record<string, number>;
	sources: string[];
	interest: string[];
	has_params: boolean;
	unprobed: number;
	sample_url: string | null;
	query: string;
	children: TreeNode[];
}

export interface EndpointTree {
	mode: string;
	nodes: TreeNode[];
	total_endpoints: number;
	total_nodes: number;
	truncated: boolean;
	error: QueryError | null;
}

export interface EndpointFacet {
	value: string;
	label: string;
	count: number;
}

export interface EndpointFacetSet {
	endpoint_class: EndpointFacet[];
	source: EndpointFacet[];
	interest: EndpointFacet[];
	status_class: EndpointFacet[];
	extension: EndpointFacet[];
	host: EndpointFacet[];
	total: number;
}

export const EMPTY_ENDPOINT_FACETS: EndpointFacetSet = {
	endpoint_class: [],
	source: [],
	interest: [],
	status_class: [],
	extension: [],
	host: [],
	total: 0
};

export interface EndpointCoverageRead {
	id: string;
	source: string;
	label: string;
	tool: string | null;
	status: string;
	hosts_total: number;
	hosts_scanned: number | null;
	hosts_dropped: string[];
	urls_found: number | null;
	urls_stored: number | null;
	urls_probed: number | null;
	pages_fetched: number | null;
	depth_reached: number | null;
	errors: number | null;
	capped: boolean;
	cap_reason: string | null;
	error: string | null;
	started_at: string;
	ended_at: string | null;
	duration_seconds: number | null;
}

export interface EndpointSummary {
	total: number;
	probed: number;
	live: number;
	with_params: number;
	interesting: number;
	hosts: number;
	by_class: Record<string, number>;
	by_source: Record<string, number>;
}

export interface EndpointQuery {
	search: string;
	host: string;
	dir: string;
	subtree: boolean;
	endpointClass: string;
	source: string;
	interest: string;
	statusClass: string;
	probed: 'any' | 'yes' | 'no';
	newOnly: boolean;
}

export function emptyEndpointQuery(): EndpointQuery {
	return {
		search: '',
		host: '',
		dir: '',
		subtree: true,
		endpointClass: '',
		source: '',
		interest: '',
		statusClass: '',
		probed: 'any',
		newOnly: false
	};
}

export interface EndpointFilter {
	q: string | null;
	host: string | null;
	dir_path: string | null;
	subtree: boolean;
	endpoint_class: string | null;
	source: string | null;
	interest: string | null;
	status_class: string | null;
	probed: boolean | null;
	new: boolean;
	sort: string;
	direction: 'asc' | 'desc';
	page: number;
	size: number;
}

export interface EndpointPage {
	items: EndpointRead[];
	total: number;
	total_capped: boolean;
	page: number;
	size: number;
	error: QueryError | null;
}

export const ENDPOINT_CLASS_TABS: { key: string; label: string }[] = [
	{ key: 'all', label: 'All' },
	...ENDPOINT_CLASS_ORDER.map((key) => ({ key, label: ENDPOINT_CLASS_LABELS[key] }))
];

export const ENDPOINT_SORTS: SortOption[] = [
	{ key: 'relevance', label: 'Relevance' },
	{ key: 'path', label: 'Path' },
	{ key: 'host', label: 'Host' },
	{ key: 'status', label: 'Status' },
	{ key: 'params', label: 'Parameters' },
	{ key: 'depth', label: 'Depth' },
	{ key: 'length', label: 'Size' },
	{ key: 'class', label: 'Kind' },
	{ key: 'seen', label: 'First seen' }
];

export function endpointActiveFacetCount(q: EndpointQuery): number {
	return (
		(q.host ? 1 : 0) +
		(q.dir ? 1 : 0) +
		(q.endpointClass ? 1 : 0) +
		(q.source ? 1 : 0) +
		(q.interest ? 1 : 0) +
		(q.statusClass ? 1 : 0) +
		(q.probed !== 'any' ? 1 : 0) +
		(q.newOnly ? 1 : 0)
	);
}

export interface EndpointFilterChip {
	id: string;
	label: string;
	remove: (q: EndpointQuery) => EndpointQuery;
}

export function endpointQueryChips(q: EndpointQuery): EndpointFilterChip[] {
	const chips: EndpointFilterChip[] = [];
	if (q.host) chips.push({ id: 'host', label: q.host, remove: (x) => ({ ...x, host: '' }) });
	if (q.dir)
		chips.push({
			id: 'dir',
			label: q.dir,
			remove: (x) => ({ ...x, dir: '', subtree: true })
		});
	if (q.endpointClass)
		chips.push({
			id: 'class',
			label: ENDPOINT_CLASS_LABELS[q.endpointClass] ?? q.endpointClass,
			remove: (x) => ({ ...x, endpointClass: '' })
		});
	if (q.source)
		chips.push({
			id: 'source',
			label: SOURCE_LABELS[q.source] ?? q.source,
			remove: (x) => ({ ...x, source: '' })
		});
	if (q.interest)
		chips.push({
			id: 'interest',
			label: INTEREST_LABELS[q.interest] ?? q.interest,
			remove: (x) => ({ ...x, interest: '' })
		});
	if (q.statusClass)
		chips.push({
			id: 'status',
			label: STATUS_CLASS_LABELS[q.statusClass] ?? q.statusClass,
			remove: (x) => ({ ...x, statusClass: '' })
		});
	if (q.probed !== 'any')
		chips.push({
			id: 'probed',
			label: q.probed === 'yes' ? 'Verified' : 'Not verified',
			remove: (x) => ({ ...x, probed: 'any' })
		});
	if (q.newOnly) chips.push({ id: 'new', label: 'New', remove: (x) => ({ ...x, newOnly: false }) });
	return chips;
}

export function compileEndpointQuery(
	q: EndpointQuery,
	sortKey: string,
	dir: 1 | -1,
	page: number,
	size: number
): EndpointFilter {
	return {
		q: q.search.trim() || null,
		host: q.host || null,
		dir_path: q.dir || null,
		subtree: q.subtree,
		endpoint_class: q.endpointClass || null,
		source: q.source || null,
		interest: q.interest || null,
		status_class: q.statusClass || null,
		probed: q.probed === 'any' ? null : q.probed === 'yes',
		new: q.newOnly,
		sort: sortKey,
		direction: dir === 1 ? 'asc' : 'desc',
		page,
		size
	};
}

export function endpointLabel(e: EndpointRead): string {
	if (e.path === '/') return '/';
	return e.filename ?? e.path;
}

export function paramSuffix(e: EndpointRead): string {
	return e.param_count ? `?${e.params.join('&')}` : '';
}

export interface StructureFinding {
	kind: string;
	label: string;
	detail: string;
	count: number;
	query: string;
	samples: string[];
}

export interface PathSpread {
	path: string;
	hosts: number;
	endpoints: number;
	query: string;
}

export interface StructureLine {
	key: string;
	label: string;
	detail: string | null;
	count: number;
	hosts: number;
	query: string;
}

export interface ScanStructure {
	endpoints: number;
	hosts: number;
	probed: number;
	directories: number;
	max_depth: number;
	with_params: number;
	headline: string | null;
	findings: StructureFinding[];
	shared_paths: PathSpread[];
	interest: StructureLine[];
	by_class: StructureLine[];
	by_source: StructureLine[];
}
