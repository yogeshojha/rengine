export type ViewDNSLookupType = 'ip_history' | 'reverse_ip' | 'reverse_ns' | 'reverse_whois';

export interface IPHistoryRecord {
	ip: string;
	location: string;
	owner: string;
	last_seen: string | null;
}

export interface IPHistoryResponse {
	lookup_type: 'ip_history';
	domain: string;
	records: IPHistoryRecord[];
}

export interface ReverseIPDomain {
	name: string;
	last_resolved: string | null;
}

export interface ReverseIPResponse {
	lookup_type: 'reverse_ip';
	host: string;
	domain_count: number;
	domains: ReverseIPDomain[];
}

export interface ReverseNSDomain {
	domain: string;
}

export interface ReverseNSResponse {
	lookup_type: 'reverse_ns';
	nameserver: string;
	domain_count: number;
	domains: ReverseNSDomain[];
}

export interface ReverseWhoisMatch {
	domain: string;
	created_date: string | null;
	registrar: string;
}

export interface ReverseWhoisResponse {
	lookup_type: 'reverse_whois';
	query: string;
	result_count: number;
	matches: ReverseWhoisMatch[];
}

export type ViewDNSResponse =
	| IPHistoryResponse
	| ReverseIPResponse
	| ReverseNSResponse
	| ReverseWhoisResponse;

export interface ViewDNSCacheRead {
	lookup_type: ViewDNSLookupType;
	query_value: string;
	result_count: number;
	cached: boolean;
	queried_at: string | null;
	data: ViewDNSResponse;
}

export type DiscoverySourceType = 'reverse_whois' | 'reverse_ip' | 'reverse_ns';

export const DISCOVERY_SOURCE_LABELS: Record<DiscoverySourceType, string> = {
	reverse_whois: 'Reverse WHOIS',
	reverse_ip: 'Reverse IP',
	reverse_ns: 'Reverse NS'
};

export const DISCOVERY_SOURCE_DESCRIPTIONS: Record<DiscoverySourceType, string> = {
	reverse_whois: 'Domains registered by the same entity',
	reverse_ip: 'Domains hosted on the same IP',
	reverse_ns: 'Domains sharing the same nameserver'
};
