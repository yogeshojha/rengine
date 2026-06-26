import type { SubdomainRead } from '$lib/types/subdomain';
import type { HttpAssetRead } from '$lib/types/http-asset';
import type { IpAddressRead } from '$lib/types/ip-address';
import type { PortRead } from '$lib/types/port';
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
		issuesOnly: false
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
		(q.issuesOnly ? 1 : 0)
	);
}

// mirror api/app/services/subdomain.py + ip_address.py
export interface Facet {
	value: string;
	label: string;
	count: number;
}

export interface SubdomainFilter {
	text: string | null;
	statuses: string[];
	tech: string[];
	services: string[];
	ports: number[];
	cert: string[];
	sources: string[];
	cdn: 'any' | 'yes' | 'no';
	waf: 'any' | 'present' | 'none';
	live: boolean;
	screenshot: boolean;
	issues: boolean;
	sensitive: boolean;
	auth: boolean;
	important: boolean;
	wildcard: boolean;
	ip: string | null;
	title: string | null;
	sort: string;
	order: 'asc' | 'desc';
	limit: number;
	offset: number;
}

export interface SubdomainSearchResult {
	items: SubdomainRead[];
	total: number;
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
	status_reframe: InsightBucket[];
	cert_buckets: InsightBucket[];
	top_tech: InsightTally[];
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
}

export interface IpGroupPage {
	items: IpGroupRead[];
	total: number;
}

const uniq = (a: string[]): string[] => a.filter((x, i) => a.indexOf(x) === i);

export function compileQuery(
	q: WebAssetQuery,
	sortKey: string,
	dir: 1 | -1,
	offset: number,
	limit: number
): SubdomainFilter {
	const f: SubdomainFilter = {
		text: null,
		statuses: [...q.status],
		tech: [...q.tech],
		services: [...q.service],
		ports: [],
		cert: [...q.cert],
		sources: [...q.source],
		cdn: q.cdn,
		waf: q.waf,
		live: q.liveOnly,
		screenshot: q.hasScreenshot,
		issues: q.issuesOnly,
		sensitive: false,
		auth: false,
		important: false,
		wildcard: false,
		ip: null,
		title: null,
		sort: sortKey,
		order: dir === 1 ? 'asc' : 'desc',
		limit,
		offset
	};
	const words: string[] = [];
	for (const part of q.search.trim().split(/\s+/).filter(Boolean)) {
		const i = part.indexOf(':');
		if (i <= 0) {
			words.push(part);
			continue;
		}
		const key = part.slice(0, i).toLowerCase();
		const raw = part.slice(i + 1);
		const v = raw.toLowerCase();
		switch (key) {
			case 'status':
				if (/^[2-5]xx$/.test(v) || v === 'none') f.statuses.push(v);
				else if (/^[1-5]\d\d$/.test(v)) f.statuses.push(`${v[0]}xx`);
				break;
			case 'tech':
				f.tech.push(raw);
				break;
			case 'service':
				f.services.push(raw);
				break;
			case 'port': {
				const n = parseInt(v, 10);
				if (!Number.isNaN(n)) f.ports.push(n);
				break;
			}
			case 'cert':
				if (['expired', 'expiring', 'self-signed', 'valid'].includes(v)) f.cert.push(v);
				break;
			case 'source':
				f.sources.push(raw);
				break;
			case 'cdn':
				f.cdn = /^(true|yes)$/.test(v) ? 'yes' : 'no';
				break;
			case 'waf':
				f.waf = v === 'none' ? 'none' : 'present';
				break;
			case 'sensitive':
				if (/^(true|yes)$/.test(v)) f.sensitive = true;
				break;
			case 'ip':
				f.ip = raw;
				break;
			case 'title':
				f.title = raw;
				break;
			case 'name':
			case 'host':
				words.push(raw);
				break;
			case 'is':
				if (v === 'live') f.live = true;
				else if (v === 'cdn') f.cdn = 'yes';
				else if (v === 'waf') f.waf = 'present';
				else if (v === 'auth') f.auth = true;
				else if (v === 'screenshot') f.screenshot = true;
				else if (v === 'important') f.important = true;
				else if (v === 'wildcard') f.wildcard = true;
				break;
			default:
				words.push(part);
		}
	}
	f.text = words.length ? words.join(' ') : null;
	f.statuses = uniq(f.statuses);
	f.tech = uniq(f.tech);
	f.services = uniq(f.services);
	f.cert = uniq(f.cert);
	f.sources = uniq(f.sources);
	f.ports = f.ports.filter((x, i) => f.ports.indexOf(x) === i);
	return f;
}
