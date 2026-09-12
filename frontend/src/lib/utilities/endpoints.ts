import type { QueryError } from '$lib/types/asset-query';
import { lex, unquote } from './query-lexer';
import { exactToken } from './scan-insights';
import type { SortOption } from '$lib/components/scans/results/table/columns';
import {
	ENDPOINT_CLASS_LABELS,
	ENDPOINT_CLASS_ORDER,
	EndpointSource,
	INTEREST_LABELS,
	SOURCE_LABELS,
	STATUS_CLASS_LABELS,
	WHY_INTERESTS
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

export interface TreeLeaf {
	id: string;
	url: string;
	host: string;
	path: string;
	params: string[];
	param_count: number;
	endpoint_class: string;
	is_probed: boolean;
	status_code: number | null;
	content_length: number | null;
	sources: string[];
	interest: string[];
}

export interface FolderChip {
	name: string;
	path: string;
	count: number;
	glyph: string;
	archive_only: boolean;
	query: string;
}

export interface HostIdentity {
	status_code: number | null;
	title: string | null;
	tech: string[];
	http_asset_id: string | null;
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
	class_mix: Record<string, number>;
	sources: string[];
	interest: string[];
	has_params: boolean;
	params: number;
	verified: number;
	unprobed: number;
	new_count: number;
	gone_count: number;
	anomaly: string | null;
	archive_only: boolean;
	glyph: string;
	sample_url: string | null;
	leaf: TreeLeaf | null;
	query: string;
	children: TreeNode[];
	lazy: boolean;
	folders: number;
	top_folders: string[];
	chips: FolderChip[];
	api: number;
	walled: number;
	unfiltered_count: number;
	identity: HostIdentity | null;
}

export interface HostPage {
	items: TreeNode[];
	total: number;
	total_endpoints: number;
	root_only: number;
	page: number;
	size: number;
	error: QueryError | null;
}

export interface ParamStat {
	name: string;
	count: number;
	interest: string | null;
}

export interface HostBrief {
	host: string;
	identity: HostIdentity | null;
	total: number;
	probed: number;
	live: number;
	with_params: number;
	api: number;
	walled: number;
	interesting: number;
	new: number;
	gone: number;
	findings: number;
	previous_scan_at: string | null;
	params: ParamStat[];
	params_total: number;
	by_class: Record<string, number>;
	static_total: number;
}

export interface MergedLeaf {
	key: string;
	path: string;
	name: string;
	params: string[];
	param_count: number;
	endpoint_class: string;
	hosts: number;
	endpoints: number;
	status_mix: Record<string, number>;
	unprobed: number;
	interest: string[];
	sources: string[];
	host_names: string[];
	new_count: number;
	sample_id: string;
	sample_url: string;
	sample_status: number | null;
	query: string;
}

export interface MergedLeafPage {
	items: MergedLeaf[];
	total: number;
	truncated: boolean;
}

export function leafToEndpoint(leaf: TreeLeaf, scanId: string): EndpointRead {
	const dir = leaf.path.endsWith('/')
		? leaf.path
		: leaf.path.slice(0, leaf.path.lastIndexOf('/') + 1);
	return {
		id: leaf.id,
		scan_id: scanId,
		target_id: '',
		signature: '',
		url: leaf.url,
		host: leaf.host,
		port: 0,
		scheme: '',
		path: leaf.path,
		dir_path: dir,
		filename: null,
		extension: null,
		depth: 0,
		params: leaf.params,
		param_count: leaf.param_count,
		variants: 1,
		more_variants: false,
		methods: [],
		sources: leaf.sources,
		primary_source: leaf.sources[0] ?? '',
		evidence: [],
		found_on: null,
		is_probed: leaf.is_probed,
		status_code: leaf.status_code,
		content_type: null,
		content_length: leaf.content_length,
		title: null,
		words: null,
		lines: null,
		response_time: null,
		redirect_location: null,
		tech: [],
		endpoint_class: leaf.endpoint_class,
		interest: leaf.interest,
		http_asset_id: null,
		subdomain_id: null,
		archive_last_seen: null,
		discovered_at: '',
		is_new: false
	};
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
	static_total: number;
}

export const EMPTY_ENDPOINT_FACETS: EndpointFacetSet = {
	endpoint_class: [],
	source: [],
	interest: [],
	status_class: [],
	extension: [],
	host: [],
	total: 0,
	static_total: 0
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
	urls_dropped: Record<string, number>;
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
	new: number;
	gone: number;
	previous_scan_id: string | null;
	previous_scan_at: string | null;
	by_class: Record<string, number>;
	by_source: Record<string, number>;
}

export interface GonePage extends EndpointPage {
	previous_scan_id: string | null;
	previous_scan_at: string | null;
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
	browsed: 'any' | 'yes' | 'no';
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
		newOnly: false,
		browsed: 'any'
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
	hide_static?: boolean;
	hide_root_only?: boolean;
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

export const HOST_SORTS: SortOption[] = [
	{ key: 'relevance', label: 'Relevance' },
	{ key: 'endpoints', label: 'Endpoints' },
	{ key: 'verified', label: 'Verified' },
	{ key: 'input', label: 'Input' },
	{ key: 'api', label: 'API' },
	{ key: 'new', label: 'New' },
	{ key: 'host', label: 'Host' }
];

export const ENDPOINT_VIEWS = ['hosts', 'merged', 'list'] as const;
export type EndpointView = (typeof ENDPOINT_VIEWS)[number];

export function endpointActiveFacetCount(q: EndpointQuery): number {
	return (
		(q.host ? 1 : 0) +
		(q.dir ? 1 : 0) +
		(q.endpointClass ? 1 : 0) +
		(q.source ? 1 : 0) +
		(q.interest ? 1 : 0) +
		(q.statusClass ? 1 : 0) +
		(q.probed !== 'any' ? 1 : 0) +
		(q.newOnly ? 1 : 0) +
		(q.browsed !== 'any' ? 1 : 0)
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
	if (q.browsed !== 'any')
		chips.push({
			id: 'browsed',
			label: q.browsed === 'yes' ? 'Browsed' : 'Not browsed',
			remove: (x) => ({ ...x, browsed: 'any' })
		});
	return chips;
}

export function compileEndpointQuery(
	q: EndpointQuery,
	sortKey: string,
	dir: 1 | -1,
	page: number,
	size: number
): EndpointFilter {
	const search = q.search.trim();
	const browsed =
		q.browsed === 'any' ? '' : `${q.browsed === 'no' ? 'not ' : ''}source:${EndpointSource.PROXY}`;
	return {
		q: (browsed ? (search ? `(${search}) and ${browsed}` : browsed) : search) || null,
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

const LOCATION_FIELDS = new Set(['dir', 'directory', 'folder', 'path', 'file', 'filename', 'url']);

export function highlightTerms(search: string, known: (name: string) => boolean): string[] {
	const out: string[] = [];
	const { tokens } = lex(search, known);
	for (let i = 0; i < tokens.length; i++) {
		const t = tokens[i];
		if (t.kind === 'term') {
			const word = unquote(t.text).trim();
			if (word && !CONNECTOR_WORDS.has(word.toLowerCase())) out.push(word);
		} else if (t.kind === 'field' && LOCATION_FIELDS.has(t.text.toLowerCase())) {
			const value = tokens.slice(i + 1, i + 3).find((n) => n.kind === 'value');
			if (value) {
				const raw = unquote(value.text).trim();
				for (const part of raw.startsWith('[') ? raw.slice(1, -1).split(',') : [raw]) {
					const v = part.trim().replace(/\*/g, '');
					if (v && v !== '/') out.push(v);
				}
			}
		}
	}
	return [...new Set(out)];
}

const CONNECTOR_WORDS = new Set(['and', 'or', 'not']);

export function hostOnlyToken(search: string, known: (name: string) => boolean): string | null {
	const { tokens } = lex(search, known);
	const meaningful = tokens.filter((t) => t.kind !== 'space');
	if (meaningful.length < 2 || meaningful.length > 3) return null;
	const [field, ...rest] = meaningful;
	if (field.kind !== 'field' || field.text.toLowerCase() !== 'host') return null;
	const value = rest.find((t) => t.kind === 'value');
	if (!value || rest.some((t) => t.kind !== 'value' && t.kind !== 'operator')) return null;
	const raw = unquote(value.text).trim();
	return raw && !/[*[\]]/.test(raw) ? raw : null;
}

export function whyReasons(interest: string[], limit = 2): string[] {
	return WHY_INTERESTS.filter((k) => interest.includes(k)).slice(0, limit);
}

export function curlFor(e: { url: string; methods: string[] }): string {
	const method = e.methods.find((m) => m !== 'GET') ?? 'GET';
	const flag = method === 'GET' ? '' : ` -X ${method}`;
	return `curl -sk${flag} '${e.url.replace(/'/g, "'\\''")}'`;
}

export function locationTokens(host: string, path: string): string {
	return `${exactToken('host', host)} ${exactToken('path', path)}`;
}

export function locationTokensFromUrl(url: string): string | null {
	const raw = url.trim();
	if (!raw) return null;
	try {
		const u = new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `https://${raw}`);
		if (!u.hostname) return null;
		const hasPath = /^[^/]*\/\/[^/]+\//.test(u.href) && u.pathname !== '/';
		return hasPath ? locationTokens(u.hostname, u.pathname) : exactToken('host', u.hostname);
	} catch {
		return null;
	}
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
