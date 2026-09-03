import { api } from './client';
import type { HttpAssetDetail } from '$lib/types/http-asset';
import type { QueryGroups, QueryLeads } from '$lib/types/asset-query';
import type { IpFacetSet, IpGroupFilter, IpSearchResult } from '$lib/utilities/ip-groups';

export const httpAssetsApi = {
	async detail(projectId: string, assetId: string): Promise<HttpAssetDetail> {
		return api.get<HttpAssetDetail>(`/http-assets/${assetId}?project_id=${projectId}`);
	}
};

export const ipsApi = {
	async search(projectId: string, scanId: string, filter: IpGroupFilter): Promise<IpSearchResult> {
		return api.post<IpSearchResult>(
			`/ips/search?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async leads(projectId: string, scanId: string, filter: IpGroupFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(
			`/ips/search/leads?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async groups(
		projectId: string,
		scanId: string,
		groupBy: string,
		filter: IpGroupFilter
	): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/ips/search/groups?project_id=${projectId}&scan_id=${scanId}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string): Promise<IpFacetSet> {
		return api.get<IpFacetSet>(`/ips/facets?project_id=${projectId}&scan_id=${scanId}`);
	}
};
