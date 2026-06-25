import type { HttpAssetRead } from '$lib/types/http-asset';
import type { IpAddressRead } from '$lib/types/ip-address';
import type { PortRead } from '$lib/types/port';
import type { SubdomainRead } from '$lib/types/subdomain';

export type StatusClass = 'success' | 'info' | 'warning' | 'destructive' | 'muted';

export function httpStatusClass(code: number | null | undefined): StatusClass {
	if (code == null) return 'muted';
	if (code >= 200 && code < 300) return 'success';
	if (code >= 300 && code < 400) return 'info';
	if (code >= 400 && code < 500) return 'warning';
	if (code >= 500) return 'destructive';
	return 'muted';
}

const STATUS_TEXT: Record<StatusClass, string> = {
	success: 'text-success',
	info: 'text-info',
	warning: 'text-warning',
	destructive: 'text-destructive',
	muted: 'text-muted-foreground'
};

export function httpStatusTextClass(code: number | null | undefined): string {
	return STATUS_TEXT[httpStatusClass(code)];
}

export interface Tally {
	name: string;
	count: number;
}

function tally(values: Iterable<string>): Tally[] {
	const counts = new Map<string, number>();
	for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
	return [...counts.entries()]
		.map(([name, count]) => ({ name, count }))
		.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

export function techDistribution(assets: HttpAssetRead[]): Tally[] {
	return tally(assets.flatMap((a) => a.tech ?? []));
}

export function webserverDistribution(assets: HttpAssetRead[]): Tally[] {
	return tally(assets.map((a) => a.webserver).filter((w): w is string => !!w));
}

export interface StatusBucket {
	label: string;
	klass: StatusClass;
	count: number;
}

export function statusDistribution(assets: HttpAssetRead[]): StatusBucket[] {
	const buckets: Record<string, StatusBucket> = {
		'2xx': { label: '2xx', klass: 'success', count: 0 },
		'3xx': { label: '3xx', klass: 'info', count: 0 },
		'4xx': { label: '4xx', klass: 'warning', count: 0 },
		'5xx': { label: '5xx', klass: 'destructive', count: 0 }
	};
	for (const a of assets) {
		if (a.status_code == null) continue;
		const key = `${Math.floor(a.status_code / 100)}xx`;
		if (buckets[key]) buckets[key].count += 1;
	}
	return Object.values(buckets).filter((b) => b.count > 0);
}

export interface TlsHealth {
	withTls: number;
	expired: number;
	selfSigned: number;
	expiringSoon: number;
}

export function tlsHealth(assets: HttpAssetRead[]): TlsHealth {
	const soon = Date.now() + 30 * 24 * 60 * 60 * 1000;
	let withTls = 0;
	let expired = 0;
	let selfSigned = 0;
	let expiringSoon = 0;
	for (const a of assets) {
		if (!a.tls_version && !a.tls_not_after) continue;
		withTls += 1;
		if (a.tls_expired) expired += 1;
		if (a.tls_self_signed) selfSigned += 1;
		if (a.tls_not_after && !a.tls_expired) {
			const t = new Date(a.tls_not_after).getTime();
			if (t < soon) expiringSoon += 1;
		}
	}
	return { withTls, expired, selfSigned, expiringSoon };
}

export interface IpGroup {
	ip: string;
	meta: IpAddressRead | null;
	ports: PortRead[];
	assets: HttpAssetRead[];
	hosts: string[];
}

export function correlateByIp(
	ips: IpAddressRead[],
	ports: PortRead[],
	assets: HttpAssetRead[],
	subdomains: SubdomainRead[]
): IpGroup[] {
	const groups = new Map<string, IpGroup>();
	const get = (ip: string): IpGroup => {
		let g = groups.get(ip);
		if (!g) {
			g = { ip, meta: null, ports: [], assets: [], hosts: [] };
			groups.set(ip, g);
		}
		return g;
	};
	for (const ip of ips) get(ip.ip).meta = ip;
	for (const p of ports) get(p.ip).ports.push(p);
	const hostSets = new Map<string, Set<string>>();
	const addHost = (ip: string, host: string) => {
		let set = hostSets.get(ip);
		if (!set) {
			set = new Set();
			hostSets.set(ip, set);
		}
		set.add(host);
	};
	for (const a of assets) {
		if (!a.ip) continue;
		get(a.ip).assets.push(a);
		addHost(a.ip, a.host);
	}
	for (const s of subdomains) {
		for (const ip of s.resolved_ips ?? []) addHost(ip, s.name);
	}
	for (const [ip, set] of hostSets) get(ip).hosts = [...set].sort();
	return [...groups.values()].sort((a, b) =>
		a.ip.localeCompare(b.ip, undefined, { numeric: true })
	);
}

export function formatBytes(n: number | null | undefined): string {
	if (n == null) return '—';
	if (n < 1024) return `${n} B`;
	if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
	return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatResponseTime(seconds: number | null | undefined): string {
	if (seconds == null) return '—';
	if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
	return `${seconds.toFixed(2)}s`;
}
