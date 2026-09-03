import { api } from './client';
import type { HttpAssetDetail } from '$lib/types/http-asset';
import type { IpGroupPage } from '$lib/utilities/scan-insights';
import type { IpFacetSet, IpGroupFilter } from '$lib/utilities/ip-groups';

export const httpAssetsApi = {
	async detail(projectId: string, assetId: string): Promise<HttpAssetDetail> {
		return api.get<HttpAssetDetail>(`/http-assets/${assetId}?project_id=${projectId}`);
	}
};

export const ipsApi = {
	async groups(
		projectId: string,
		scanId: string,
		params: { search?: string; limit?: number; offset?: number } = {}
	): Promise<IpGroupPage> {
		const sp = new URLSearchParams({ project_id: projectId, scan_id: scanId });
		if (params.search) sp.append('search', params.search);
		if (params.limit != null) sp.append('limit', String(params.limit));
		if (params.offset != null) sp.append('offset', String(params.offset));
		return api.get<IpGroupPage>(`/ips/groups?${sp.toString()}`);
	},

	async search(projectId: string, scanId: string, filter: IpGroupFilter): Promise<IpGroupPage> {
		return api.post<IpGroupPage>(`/ips/search?project_id=${projectId}&scan_id=${scanId}`, filter);
	},

	async facets(projectId: string, scanId: string): Promise<IpFacetSet> {
		return api.get<IpFacetSet>(`/ips/facets?project_id=${projectId}&scan_id=${scanId}`);
	}
};
