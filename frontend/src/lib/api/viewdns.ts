import { api } from './client';
import type { ViewDNSCacheRead } from '$lib/types/viewdns';

export const viewdnsApi = {
	async ipHistory(
		domain: string,
		cachedOnly: boolean = false
	): Promise<ViewDNSCacheRead | null> {
		const params = cachedOnly ? '?cached_only=true' : '';
		return api.get<ViewDNSCacheRead | null>(
			`/tools/viewdns/ip-history/${encodeURIComponent(domain)}${params}`
		);
	},

	async reverseIp(
		host: string,
		cachedOnly: boolean = false
	): Promise<ViewDNSCacheRead | null> {
		const params = cachedOnly ? '?cached_only=true' : '';
		return api.get<ViewDNSCacheRead | null>(
			`/tools/viewdns/reverse-ip/${encodeURIComponent(host)}${params}`
		);
	},

	async reverseNs(
		nameserver: string,
		cachedOnly: boolean = false
	): Promise<ViewDNSCacheRead | null> {
		const params = cachedOnly ? '?cached_only=true' : '';
		return api.get<ViewDNSCacheRead | null>(
			`/tools/viewdns/reverse-ns/${encodeURIComponent(nameserver)}${params}`
		);
	},

	async reverseWhois(
		query: string,
		cachedOnly: boolean = false
	): Promise<ViewDNSCacheRead | null> {
		const params = new URLSearchParams({ q: query });
		if (cachedOnly) params.append('cached_only', 'true');
		return api.get<ViewDNSCacheRead | null>(
			`/tools/viewdns/reverse-whois?${params.toString()}`
		);
	}
};
