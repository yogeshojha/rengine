import type { QueryError } from '$lib/types/asset-query';
import type { Facet, IpGroupRead } from './scan-insights';
import type { SortOption } from '$lib/components/scans/results/table/columns';

export interface IpQuery {
	search: string;
	exposure: string[];
	asn: string[];
	country: string[];
	port: string[];
	service: string[];
	cdn: 'any' | 'yes' | 'no';
	hostedOnly: boolean;
	sensitiveOnly: boolean;
	version: 0 | 4 | 6;
}

export function emptyIpQuery(): IpQuery {
	return {
		search: '',
		exposure: [],
		asn: [],
		country: [],
		port: [],
		service: [],
		cdn: 'any',
		hostedOnly: false,
		sensitiveOnly: false,
		version: 0
	};
}

export interface IpGroupFilter {
	q: string | null;
	exposure: string[];
	asns: number[];
	countries: string[];
	ports: number[];
	services: string[];
	cdn: 'any' | 'yes' | 'no';
	alive: 'any' | 'yes' | 'no';
	version: number;
	sensitive: boolean;
	hosted: boolean;
	open: boolean;
	sort: string;
	order: 'asc' | 'desc';
	limit: number;
	offset: number;
}

export interface IpSearchResult {
	items: IpGroupRead[];
	total: number;
	total_capped: boolean;
	error: QueryError | null;
}

export interface IpFacetSet {
	exposure: Facet[];
	asn: Facet[];
	country: Facet[];
	port: Facet[];
	service: Facet[];
}

export const EMPTY_IP_FACETS: IpFacetSet = {
	exposure: [],
	asn: [],
	country: [],
	port: [],
	service: []
};

// mirrors shared/definitions/asset_query.py IP_EXPOSURE
export const IP_EXPOSURE_TABS: { key: string; label: string }[] = [
	{ key: 'all', label: 'All' },
	{ key: 'open', label: 'Open ports' },
	{ key: 'responding', label: 'Responding' },
	{ key: 'quiet', label: 'No response' }
];

export const IP_SORTS: SortOption[] = [
	{ key: 'hosts', label: 'Hosts' },
	{ key: 'ports', label: 'Ports' },
	{ key: 'ip', label: 'Address' },
	{ key: 'asn', label: 'Network' },
	{ key: 'country', label: 'Country' },
	{ key: 'assets', label: 'Web services' }
];

export function ipActiveFacetCount(q: IpQuery): number {
	return (
		q.exposure.length +
		q.asn.length +
		q.country.length +
		q.port.length +
		q.service.length +
		(q.cdn !== 'any' ? 1 : 0) +
		(q.hostedOnly ? 1 : 0) +
		(q.sensitiveOnly ? 1 : 0) +
		(q.version !== 0 ? 1 : 0)
	);
}

export interface IpFilterChip {
	id: string;
	label: string;
	remove: (q: IpQuery) => IpQuery;
}

type ListKey = 'asn' | 'country' | 'port' | 'service';

export function ipQueryChips(q: IpQuery, facets: IpFacetSet): IpFilterChip[] {
	const chips: IpFilterChip[] = [];
	const list = (key: ListKey, fmt: (v: string) => string) => {
		for (const v of q[key])
			chips.push({
				id: `${key}:${v}`,
				label: fmt(v),
				remove: (x) => ({ ...x, [key]: x[key].filter((o) => o !== v) })
			});
	};
	list('asn', (v) => facets.asn.find((f) => f.value === v)?.label ?? `AS${v}`);
	list('country', (v) => v);
	list('port', (v) => `Port ${v}`);
	list('service', (v) => `Service ${v}`);
	if (q.cdn !== 'any')
		chips.push({
			id: 'cdn',
			label: q.cdn === 'yes' ? 'Behind CDN' : 'Not behind CDN',
			remove: (x) => ({ ...x, cdn: 'any' })
		});
	if (q.hostedOnly)
		chips.push({ id: 'hosted', label: 'Has hosts', remove: (x) => ({ ...x, hostedOnly: false }) });
	if (q.sensitiveOnly)
		chips.push({
			id: 'sensitive',
			label: 'Sensitive services',
			remove: (x) => ({ ...x, sensitiveOnly: false })
		});
	if (q.version !== 0)
		chips.push({ id: 'version', label: `IPv${q.version}`, remove: (x) => ({ ...x, version: 0 }) });
	return chips;
}

export function compileIpQuery(
	q: IpQuery,
	sortKey: string,
	dir: 1 | -1,
	offset: number,
	limit: number
): IpGroupFilter {
	return {
		q: q.search.trim() || null,
		exposure: [...q.exposure],
		asns: q.asn.map(Number).filter((n) => !Number.isNaN(n)),
		countries: [...q.country],
		ports: q.port.map(Number).filter((n) => !Number.isNaN(n)),
		services: [...q.service],
		cdn: q.cdn,
		alive: 'any',
		version: q.version,
		sensitive: q.sensitiveOnly,
		hosted: q.hostedOnly,
		open: false,
		sort: sortKey,
		order: dir === 1 ? 'asc' : 'desc',
		limit,
		offset
	};
}
