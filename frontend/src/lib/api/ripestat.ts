import { api } from './client';
import type {
	AnnouncedPrefixRead,
	ASNNeighbourRead,
	ASOverviewRead,
	NetworkInfoRead,
	AbuseContactRead,
	PrefixOverviewRead,
	RelatedPrefixRead,
	RIPEStatLookupType,
	RIPEStatResult
} from '$lib/types/ripestat';

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
