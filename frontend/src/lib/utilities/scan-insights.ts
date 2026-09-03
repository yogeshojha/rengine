import type { SubdomainRead } from '$lib/types/subdomain';
import type { HttpAssetRead } from '$lib/types/http-asset';
import type { IpAddressRead } from '$lib/types/ip-address';
import type { PortRead } from '$lib/types/port';
import { quoteValue } from '$lib/utilities/query-lexer';
import type { QueryError } from '$lib/types/asset-query';
import type { StatusClass } from './scan-correlation';

const DAY = 24 * 60 * 60 * 1000;

export function certState(
	s: SubdomainRead
): 'expired' | 'expiring' | 'self-signed' | 'valid' | null {
	if (s.tls_self_signed) return 'self-signed';
	if (s.tls_expired) return 'expired';
	if (s.tls_not_after) {
		const t = new Date(s.tls_not_after).getTime();
		if (t < Date.now() + 30 * DAY) return 'expiring';
		return 'valid';
	}
	return null;
}

export function daysUntilExpiry(s: SubdomainRead): number | null {
	if (!s.tls_not_after) return null;
	return Math.round((new Date(s.tls_not_after).getTime() - Date.now()) / DAY);
}

export interface WebAssetQuery {
	search: string;
	status: string[];
	tech: string[];
	service: string[];
	cert: string[];
	source: string[];
	cdn: 'any' | 'yes' | 'no';
	waf: 'any' | 'present' | 'none';
	liveOnly: boolean;
	hasScreenshot: boolean;
	issuesOnly: boolean;
	newOnly: boolean;
}

export function emptyQuery(): WebAssetQuery {
	return {
		search: '',
		status: [],
		tech: [],
		service: [],
		cert: [],
		source: [],
		cdn: 'any',
		waf: 'any',
		liveOnly: false,
		hasScreenshot: false,
		issuesOnly: false,
		newOnly: false
	};
}

export function activeFacetCount(q: WebAssetQuery): number {
	return (
		q.status.length +
		q.tech.length +
		q.service.length +
		q.cert.length +
		q.source.length +
		(q.cdn !== 'any' ? 1 : 0) +
		(q.waf !== 'any' ? 1 : 0) +
		(q.liveOnly ? 1 : 0) +
		(q.hasScreenshot ? 1 : 0) +
		(q.issuesOnly ? 1 : 0) +
		(q.newOnly ? 1 : 0)
	);
}

export interface FilterChip {
	id: string;
	label: string;
	remove: (q: WebAssetQuery) => WebAssetQuery;
}

// mirrors api/app/services/subdomain.py _STATUS_LABELS
export const STATUS_CLASS_TABS: { key: string; label: string }[] = [
	{ key: 'all', label: 'All' },
	{ key: '2xx', label: '2xx OK' },
	{ key: '3xx', label: '3xx Redirect' },
	{ key: '4xx', label: '4xx Client' },
	{ key: '5xx', label: '5xx Server' },
	{ key: 'none', label: 'No HTTP' }
];

export const WEB_ASSET_SORTS: { key: string; label: string }[] = [
	{ key: 'status', label: 'Status' },
	{ key: 'name', label: 'Host' },
	{ key: 'title', label: 'Title' },
	{ key: 'ip', label: 'IP' },
	{ key: 'cert', label: 'Cert' },
	{ key: 'discovered', label: 'Found' },
	{ key: 'size', label: 'Size' },
	{ key: 'time', label: 'Time' }
];

const CERT_CHIP: Record<string, string> = {
	expired: 'Cert expired',
	expiring: 'Cert expiring',
	'self-signed': 'Self-signed cert',
	valid: 'Cert valid'
};

type ListKey = 'tech' | 'service' | 'cert' | 'source';

export function queryChips(q: WebAssetQuery): FilterChip[] {
	const chips: FilterChip[] = [];
	const list = (key: ListKey, fmt: (v: string) => string) => {
		for (const v of q[key])
			chips.push({
				id: `${key}:${v}`,
				label: fmt(v),
				remove: (x) => ({ ...x, [key]: x[key].filter((o) => o !== v) })
			});
	};
	list('tech', (v) => v);
	list('service', (v) => `Service ${v}`);
	list('cert', (v) => CERT_CHIP[v] ?? v);
	list('source', (v) => `Source ${v}`);
	if (q.cdn !== 'any')
		chips.push({
			id: 'cdn',
			label: q.cdn === 'yes' ? 'Behind CDN' : 'Not behind CDN',
			remove: (x) => ({ ...x, cdn: 'any' })
		});
	if (q.waf !== 'any')
		chips.push({
			id: 'waf',
			label: q.waf === 'none' ? 'No WAF' : 'WAF present',
			remove: (x) => ({ ...x, waf: 'any' })
		});
	if (q.liveOnly)
		chips.push({ id: 'live', label: 'Live', remove: (x) => ({ ...x, liveOnly: false }) });
	if (q.newOnly)
		chips.push({ id: 'new', label: 'New this scan', remove: (x) => ({ ...x, newOnly: false }) });
	if (q.hasScreenshot)
		chips.push({
			id: 'screenshot',
			label: 'With screenshot',
			remove: (x) => ({ ...x, hasScreenshot: false })
		});
	if (q.issuesOnly)
		chips.push({ id: 'issues', label: 'Has issues', remove: (x) => ({ ...x, issuesOnly: false }) });
	return chips;
}

export function tokenize(search: string): string[] {
	return search.match(/(?:[^\s"]+|"[^"]*")+/g) ?? [];
}

export function filterToken(key: string, value: string): string {
	return `${key}:${quoteValue(value)}`;
}

export function exactToken(key: string, value: string): string {
	return `${key}=${quoteValue(value)}`;
}

export function appendToken(search: string, token: string): string {
	const parts = tokenize(search);
	if (parts.includes(token)) return search;
	return [...parts, token].join(' ');
}

// mirror api/app/services/subdomain.py + ip_address.py
export interface Facet {
	value: string;
	label: string;
	count: number;
}

export interface SubdomainFilter {
	q: string | null;
	statuses: string[];
	tech: string[];
	services: string[];
	cert: string[];
	sources: string[];
	cdn: 'any' | 'yes' | 'no';
	waf: 'any' | 'present' | 'none';
	live: boolean;
	screenshot: boolean;
	issues: boolean;
	new: boolean;
	sort: string;
	order: 'asc' | 'desc';
	limit: number;
	offset: number;
}

export interface SubdomainSearchResult {
	items: SubdomainRead[];
	total: number;
	total_capped: boolean;
	error: QueryError | null;
}

export interface SubdomainFacetSet {
	status: Facet[];
	tech: Facet[];
	service: Facet[];
	source: Facet[];
	cert: Facet[];
}

export interface SubdomainRelation {
	kind: string;
	reason: string;
	value: string;
	hosts: string[];
}

export const RELATION_LABELS: Record<string, string> = {
	ip: 'resolve to the same IP',
	cname: 'share a CNAME target',
	favicon: 'share a favicon',
	asn: 'sit in the same network',
	cert: 'share a TLS certificate'
};

export function relationLabel(r: SubdomainRelation): string {
	const fallback = r.reason.replace(/\s*\(.*\)$/, '');
	return RELATION_LABELS[r.kind] ?? fallback.charAt(0).toLowerCase() + fallback.slice(1);
}

export interface InsightStat {
	key: string;
	label: string;
	value: number;
	filter: string;
}

export interface InsightAttention {
	key: string;
	label: string;
	count: number;
	filter: string;
	tone: 'destructive' | 'warning';
}

export interface InsightBucket {
	key: string;
	label: string;
	count: number;
	klass: StatusClass;
}

export interface InsightTally {
	name: string;
	count: number;
}

export interface InsightCluster {
	kind: string;
	reason: string;
	value: string;
	count: number;
}

export interface SubdomainInsights {
	surface: InsightStat[];
	attention: InsightAttention[];
	sources: InsightTally[];
	resolution: InsightBucket[];
	status_reframe: InsightBucket[];
	cert_buckets: InsightBucket[];
	top_tech: InsightTally[];
	tech_total: number;
	top_asn: InsightTally[];
	services: InsightTally[];
	clusters: InsightCluster[];
}

export interface SubdomainCorrelation {
	primary_asset: HttpAssetRead | null;
	services: HttpAssetRead[];
	ports: PortRead[];
	ip_metas: IpAddressRead[];
	related: SubdomainRelation[];
}

export interface IpGroupRead {
	ip: string;
	version: number;
	asn: number | null;
	asn_org: string | null;
	country: string | null;
	prefix: string | null;
	is_cdn: boolean;
	cdn_name: string | null;
	is_alive: boolean | null;
	ptr_hostnames: string[];
	ports: PortRead[];
	host_count: number;
	hosts: string[];
	port_count: number;
	has_sensitive: boolean;
	asset_count: number;
}

export interface IpGroupPage {
	items: IpGroupRead[];
	total: number;
}

export function compileQuery(
	q: WebAssetQuery,
	sortKey: string,
	dir: 1 | -1,
	offset: number,
	limit: number
): SubdomainFilter {
	return {
		q: q.search.trim() || null,
		statuses: [...q.status],
		tech: [...q.tech],
		services: [...q.service],
		cert: [...q.cert],
		sources: [...q.source],
		cdn: q.cdn,
		waf: q.waf,
		live: q.liveOnly,
		screenshot: q.hasScreenshot,
		issues: q.issuesOnly,
		new: q.newOnly,
		sort: sortKey,
		order: dir === 1 ? 'asc' : 'desc',
		limit,
		offset
	};
}
