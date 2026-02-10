import { api } from './client';

export interface AnnouncedPrefixRead {
	prefix: string;
	ip_version: number;
	first_seen: string | null;
	last_seen: string | null;
}

export interface ASNNeighbourRead {
	neighbour_asn: number;
	relationship: string; // 'upstream' | 'downstream' | 'uncertain'
	power: number;
}

export interface ASOverviewRead {
	asn: number;
	holder: string;
	rir: string | null;
	announced: boolean;
	block_name: string | null;
	block_resource: string | null;
}

export interface NetworkInfoRead {
	ip: string;
	prefix: string;
	asn: number;
}

export interface AbuseContactRead {
	resource: string;
	abuse_emails: string[];
	rir: string | null;
}

export interface PrefixOverviewRead {
	prefix: string;
	asn: number;
	holder: string;
	is_announced: boolean;
}

export interface RelatedPrefixRead {
	related_prefix: string;
	relationship: string; // 'overlap' | 'more_specific' | 'less_specific'
	origin_asn: number | null;
}

export type RIPEStatLookupType =
	| 'announced_prefixes'
	| 'asn_neighbours'
	| 'as_overview'
	| 'network_info'
	| 'abuse_contact'
	| 'prefix_overview'
	| 'related_prefixes';

export interface RIPEStatResult<T = unknown> {
	lookup_type: RIPEStatLookupType;
	query_value: string;
	result_count: number;
	cached: boolean;
	queried_at: string | null;
	data: T;
}


export const ripestatApi = {
	async getAnnouncedPrefixes(
		asn: string,
		cachedOnly = false
	): Promise<RIPEStatResult<AnnouncedPrefixRead[]> | null> {
		const params = cachedOnly ? '?cached_only=true' : '';
		return api.get(`/tools/ripestat/prefixes/${asn}${params}`);
	},

	async getASNNeighbours(
		asn: string,
		cachedOnly = false
	): Promise<RIPEStatResult<ASNNeighbourRead[]> | null> {
		const params = cachedOnly ? '?cached_only=true' : '';
		return api.get(`/tools/ripestat/neighbours/${asn}${params}`);
	},

	async getASOverview(
		asn: string,
		cachedOnly = false
	): Promise<RIPEStatResult<ASOverviewRead> | null> {
		const params = cachedOnly ? '?cached_only=true' : '';
		return api.get(`/tools/ripestat/overview/${asn}${params}`);
	},

	async getNetworkInfo(
		ip: string,
		cachedOnly = false
	): Promise<RIPEStatResult<NetworkInfoRead[]> | null> {
		const params = cachedOnly ? '?cached_only=true' : '';
		return api.get(`/tools/ripestat/network-info/${ip}${params}`);
	},

	async getAbuseContact(
		resource: string,
		cachedOnly = false
	): Promise<RIPEStatResult<AbuseContactRead> | null> {
		const q = new URLSearchParams({ resource });
		if (cachedOnly) q.append('cached_only', 'true');
		return api.get(`/tools/ripestat/abuse-contact?${q}`);
	},

	async getPrefixOverview(
		prefix: string,
		cachedOnly = false
	): Promise<RIPEStatResult<PrefixOverviewRead[]> | null> {
		const q = new URLSearchParams({ prefix });
		if (cachedOnly) q.append('cached_only', 'true');
		return api.get(`/tools/ripestat/prefix-overview?${q}`);
	},

	async getRelatedPrefixes(
		prefix: string,
		cachedOnly = false
	): Promise<RIPEStatResult<RelatedPrefixRead[]> | null> {
		const q = new URLSearchParams({ prefix });
		if (cachedOnly) q.append('cached_only', 'true');
		return api.get(`/tools/ripestat/related-prefixes?${q}`);
	}
};
