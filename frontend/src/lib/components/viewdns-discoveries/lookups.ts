import { viewdnsApi } from '$lib/api/viewdns';
import { TargetType } from '$lib/types/target';
import type {
	DiscoverySourceType,
	ReverseIPResponse,
	ReverseNSResponse,
	ReverseWhoisResponse,
	ViewDNSCacheRead
} from '$lib/types/viewdns';

export interface Lookup {
	source: DiscoverySourceType;
	queryValue: string;
	fetch: (q: string, cachedOnly: boolean) => Promise<ViewDNSCacheRead | null>;
}

export interface LookupWhois {
	registrant_name?: string | null;
	registrant_email?: string | null;
	nameservers?: string[] | null;
}

export function planLookups(
	targetType: TargetType,
	targetValue: string,
	whois: LookupWhois | null
): Lookup[] {
	if (targetType === TargetType.IP) {
		return [{ source: 'reverse_ip', queryValue: targetValue, fetch: viewdnsApi.reverseIp }];
	}
	if (targetType !== TargetType.DOMAIN || !whois) return [];

	const lookups: Lookup[] = [];
	const registrant = whois.registrant_name || whois.registrant_email;
	if (registrant) {
		lookups.push({
			source: 'reverse_whois',
			queryValue: registrant,
			fetch: viewdnsApi.reverseWhois
		});
	}
	const ns = whois.nameservers?.[0];
	if (ns) {
		lookups.push({ source: 'reverse_ns', queryValue: ns, fetch: viewdnsApi.reverseNs });
	}
	return lookups;
}

export function extractDomains(cache: ViewDNSCacheRead, source: DiscoverySourceType): string[] {
	const data = cache.data;
	switch (source) {
		case 'reverse_whois':
			return (data as ReverseWhoisResponse).matches?.map((m) => m.domain).filter(Boolean) ?? [];
		case 'reverse_ip':
			return (data as ReverseIPResponse).domains?.map((m) => m.name).filter(Boolean) ?? [];
		case 'reverse_ns':
			return (data as ReverseNSResponse).domains?.map((m) => m.domain).filter(Boolean) ?? [];
	}
}

export function discoveredDomains(
	cache: ViewDNSCacheRead,
	source: DiscoverySourceType,
	targetValue: string
): string[] {
	const own = targetValue.toLowerCase();
	return extractDomains(cache, source).filter((d) => d.toLowerCase() !== own);
}
