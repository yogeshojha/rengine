import { tokenize, unquote } from './scan-insights';
import type { DslKey, Facet } from './scan-insights';

export interface IpQuery {
	search: string;
	asn: string[];
	country: string[];
	port: string[];
	service: string[];
	cdn: 'any' | 'yes' | 'no';
	aliveOnly: boolean;
	hostedOnly: boolean;
	openOnly: boolean;
	sensitiveOnly: boolean;
	version: 0 | 4 | 6;
}

export function emptyIpQuery(): IpQuery {
	return {
		search: '',
		asn: [],
		country: [],
		port: [],
		service: [],
		cdn: 'any',
		aliveOnly: false,
		hostedOnly: false,
		openOnly: false,
		sensitiveOnly: false,
		version: 0
	};
}

// mirror shared/models/scan_correlation.py
export interface IpGroupFilter {
	text: string | null;
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
	host: string | null;
	ptr: string | null;
	org: string | null;
	prefix: string | null;
	sort: string;
	order: 'asc' | 'desc';
	limit: number;
	offset: number;
}

export interface IpFacetSet {
	asn: Facet[];
	country: Facet[];
	port: Facet[];
	service: Facet[];
}

export const EMPTY_IP_FACETS: IpFacetSet = { asn: [], country: [], port: [], service: [] };

export const IP_DSL_KEYS: DslKey[] = [
	{ key: 'asn', hint: 'Autonomous system', facet: 'asn' },
	{ key: 'country', hint: 'Country', facet: 'country' },
	{ key: 'port', hint: 'Open port', facet: 'port' },
	{ key: 'service', hint: 'Port service', facet: 'service' },
	{
		key: 'is',
		hint: 'IP property',
		values: ['alive', 'cdn', 'hosted', 'open', 'sensitive', 'v4', 'v6']
	},
	{ key: 'cdn', hint: 'Fronted by a CDN', values: ['yes', 'no'] },
	{ key: 'host', hint: 'Host name contains' },
	{ key: 'org', hint: 'Network operator contains' },
	{ key: 'ptr', hint: 'PTR record contains' },
	{ key: 'prefix', hint: 'Announced prefix' }
];

export function ipActiveFacetCount(q: IpQuery): number {
	return (
		q.asn.length +
		q.country.length +
		q.port.length +
		q.service.length +
		(q.cdn !== 'any' ? 1 : 0) +
		(q.aliveOnly ? 1 : 0) +
		(q.hostedOnly ? 1 : 0) +
		(q.openOnly ? 1 : 0) +
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
	if (q.aliveOnly)
		chips.push({ id: 'alive', label: 'Responding', remove: (x) => ({ ...x, aliveOnly: false }) });
	if (q.hostedOnly)
		chips.push({ id: 'hosted', label: 'Has hosts', remove: (x) => ({ ...x, hostedOnly: false }) });
	if (q.openOnly)
		chips.push({ id: 'open', label: 'Open ports', remove: (x) => ({ ...x, openOnly: false }) });
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

const uniq = <T>(a: T[]): T[] => a.filter((x, i) => a.indexOf(x) === i);

export function compileIpQuery(
	q: IpQuery,
	sortKey: string,
	dir: 1 | -1,
	offset: number,
	limit: number
): IpGroupFilter {
	const f: IpGroupFilter = {
		text: null,
		asns: q.asn.map(Number).filter((n) => !Number.isNaN(n)),
		countries: [...q.country],
		ports: q.port.map(Number).filter((n) => !Number.isNaN(n)),
		services: [...q.service],
		cdn: q.cdn,
		alive: q.aliveOnly ? 'yes' : 'any',
		version: q.version,
		sensitive: q.sensitiveOnly,
		hosted: q.hostedOnly,
		open: q.openOnly,
		host: null,
		ptr: null,
		org: null,
		prefix: null,
		sort: sortKey,
		order: dir === 1 ? 'asc' : 'desc',
		limit,
		offset
	};
	const words: string[] = [];
	for (const part of tokenize(q.search)) {
		const i = part.indexOf(':');
		if (i <= 0) {
			words.push(unquote(part));
			continue;
		}
		const key = part.slice(0, i).toLowerCase();
		const raw = unquote(part.slice(i + 1));
		const v = raw.toLowerCase();
		switch (key) {
			case 'asn': {
				const n = parseInt(v.replace(/^as/, ''), 10);
				if (!Number.isNaN(n)) f.asns.push(n);
				break;
			}
			case 'country':
				f.countries.push(raw.toUpperCase());
				break;
			case 'port': {
				const n = parseInt(v, 10);
				if (!Number.isNaN(n)) f.ports.push(n);
				break;
			}
			case 'service':
				f.services.push(raw);
				break;
			case 'cdn':
				f.cdn = /^(true|yes)$/.test(v) ? 'yes' : 'no';
				break;
			case 'is':
				if (v === 'alive') f.alive = 'yes';
				else if (v === 'cdn') f.cdn = 'yes';
				else if (v === 'hosted') f.hosted = true;
				else if (v === 'open') f.open = true;
				else if (v === 'sensitive') f.sensitive = true;
				else if (v === 'v4') f.version = 4;
				else if (v === 'v6') f.version = 6;
				break;
			case 'host':
				f.host = raw;
				break;
			case 'org':
				f.org = raw;
				break;
			case 'ptr':
				f.ptr = raw;
				break;
			case 'prefix':
				f.prefix = raw;
				break;
			case 'ip':
				words.push(raw);
				break;
			default:
				words.push(part);
		}
	}
	f.text = words.length ? words.join(' ') : null;
	f.asns = uniq(f.asns);
	f.countries = uniq(f.countries);
	f.ports = uniq(f.ports);
	f.services = uniq(f.services);
	return f;
}
