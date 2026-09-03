import type { QueryError } from '$lib/types/asset-query';
import type { Facet } from './scan-insights';
import type { SortOption } from '$lib/components/scans/results/table/columns';
import { SERVICE_CLASS_LABELS, SERVICE_CLASS_ORDER } from '$lib/config/service-classes';

export interface ServiceRead {
	id: string;
	ip: string;
	port: number;
	protocol: string;
	state: string;
	service_name: string | null;
	service_class: string;
	description: string;
	registered: boolean;
	source: string;
	is_http: boolean;
	tls: boolean;
	product: string | null;
	version: string | null;
	banner: string | null;
	asn: number | null;
	asn_org: string | null;
	country: string | null;
	prefix: string | null;
	is_cdn: boolean;
	cdn_name: string | null;
	scan_policy: string | null;
	host_count: number;
	hosts: string[];
	web_count: number;
	status_code: number | null;
	url: string | null;
	title: string | null;
	is_sensitive: boolean;
	is_new: boolean;
}

export interface ServiceQuery {
	search: string;
	classes: string[];
	port: string[];
	service: string[];
	source: string[];
	asn: string[];
	country: string[];
	cdn: 'any' | 'yes' | 'no';
	http: 'any' | 'yes' | 'no';
	sensitiveOnly: boolean;
	namedOnly: boolean;
	newOnly: boolean;
}

export function emptyServiceQuery(): ServiceQuery {
	return {
		search: '',
		classes: [],
		port: [],
		service: [],
		source: [],
		asn: [],
		country: [],
		cdn: 'any',
		http: 'any',
		sensitiveOnly: false,
		namedOnly: false,
		newOnly: false
	};
}

export interface ServiceFilter {
	q: string | null;
	classes: string[];
	ports: number[];
	services: string[];
	sources: string[];
	asns: number[];
	countries: string[];
	cdn: 'any' | 'yes' | 'no';
	http: 'any' | 'yes' | 'no';
	sensitive: boolean;
	named: boolean;
	new: boolean;
	sort: string;
	order: 'asc' | 'desc';
	limit: number;
	offset: number;
}

export interface ServiceSearchResult {
	items: ServiceRead[];
	total: number;
	total_capped: boolean;
	error: QueryError | null;
}

export interface ServiceFacetSet {
	class: Facet[];
	port: Facet[];
	service: Facet[];
	source: Facet[];
	asn: Facet[];
	country: Facet[];
}

export const EMPTY_SERVICE_FACETS: ServiceFacetSet = {
	class: [],
	port: [],
	service: [],
	source: [],
	asn: [],
	country: []
};

export const SERVICE_CLASS_TABS: { key: string; label: string }[] = [
	{ key: 'all', label: 'All' },
	...SERVICE_CLASS_ORDER.map((key) => ({ key, label: SERVICE_CLASS_LABELS[key] }))
];

export const SERVICE_SORTS: SortOption[] = [
	{ key: 'exposure', label: 'Exposure' },
	{ key: 'port', label: 'Port' },
	{ key: 'service', label: 'Service' },
	{ key: 'product', label: 'Software' },
	{ key: 'ip', label: 'Address' },
	{ key: 'hosts', label: 'Hosts' },
	{ key: 'asn', label: 'Network' },
	{ key: 'country', label: 'Country' }
];

export function serviceActiveFacetCount(q: ServiceQuery): number {
	return (
		q.classes.length +
		q.port.length +
		q.service.length +
		q.source.length +
		q.asn.length +
		q.country.length +
		(q.cdn !== 'any' ? 1 : 0) +
		(q.http !== 'any' ? 1 : 0) +
		(q.sensitiveOnly ? 1 : 0) +
		(q.namedOnly ? 1 : 0) +
		(q.newOnly ? 1 : 0)
	);
}

export interface ServiceFilterChip {
	id: string;
	label: string;
	remove: (q: ServiceQuery) => ServiceQuery;
}

type ListKey = 'classes' | 'port' | 'service' | 'source' | 'asn' | 'country';

export function serviceQueryChips(q: ServiceQuery, facets: ServiceFacetSet): ServiceFilterChip[] {
	const chips: ServiceFilterChip[] = [];
	const list = (key: ListKey, fmt: (v: string) => string) => {
		for (const v of q[key])
			chips.push({
				id: `${key}:${v}`,
				label: fmt(v),
				remove: (x) => ({ ...x, [key]: x[key].filter((o) => o !== v) })
			});
	};
	list('classes', (v) => SERVICE_CLASS_LABELS[v] ?? v);
	list('port', (v) => `Port ${v}`);
	list('service', (v) => facets.service.find((f) => f.value === v)?.label ?? v);
	list('source', (v) => facets.source.find((f) => f.value === v)?.label ?? v);
	list('asn', (v) => facets.asn.find((f) => f.value === v)?.label ?? `AS${v}`);
	list('country', (v) => v);
	if (q.cdn !== 'any')
		chips.push({
			id: 'cdn',
			label: q.cdn === 'yes' ? 'On a CDN' : 'Not on a CDN',
			remove: (x) => ({ ...x, cdn: 'any' })
		});
	if (q.http !== 'any')
		chips.push({
			id: 'http',
			label: q.http === 'yes' ? 'Answers HTTP' : 'No HTTP',
			remove: (x) => ({ ...x, http: 'any' })
		});
	if (q.sensitiveOnly)
		chips.push({
			id: 'sensitive',
			label: 'Sensitive ports',
			remove: (x) => ({ ...x, sensitiveOnly: false })
		});
	if (q.namedOnly)
		chips.push({
			id: 'named',
			label: 'Software named',
			remove: (x) => ({ ...x, namedOnly: false })
		});
	return chips;
}

export function compileServiceQuery(
	q: ServiceQuery,
	sortKey: string,
	dir: 1 | -1,
	offset: number,
	limit: number
): ServiceFilter {
	return {
		q: q.search.trim() || null,
		classes: [...q.classes],
		ports: q.port.map(Number).filter((n) => !Number.isNaN(n)),
		services: [...q.service],
		sources: [...q.source],
		asns: q.asn.map(Number).filter((n) => !Number.isNaN(n)),
		countries: [...q.country],
		cdn: q.cdn,
		http: q.http,
		sensitive: q.sensitiveOnly,
		named: q.namedOnly,
		new: q.newOnly,
		sort: sortKey,
		order: dir === 1 ? 'asc' : 'desc',
		limit,
		offset
	};
}

export interface ExposureBand {
	key: string;
	label: string;
	count: number;
	addresses: number;
	query: string;
}

export interface ExposureLine {
	key: string;
	label: string;
	detail: string | null;
	count: number;
	query: string;
}

export interface ScanExposure {
	services: number;
	addresses: number;
	web_services: number;
	non_web_services: number;
	answering_http: number;
	sensitive: number;
	named: number;
	passive_only: number;
	nonstandard_web: number;
	bands: ExposureBand[];
	top_services: ExposureLine[];
	coverage: ExposureLine[];
	scanned: number;
}

export function serviceLabel(s: ServiceRead): string {
	if (s.product) return s.version ? `${s.product} ${s.version}` : s.product;
	return s.service_name ?? `Port ${s.port}`;
}

// banners name the build, not the brand: "OpenSSH_6.6.1p1 Ubuntu-2" -> "OpenSSH"
export function productBrand(product: string | null | undefined): string {
	return (product ?? '').split(/[\s/_(,-]/)[0] ?? '';
}
