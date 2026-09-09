import { api } from './client';
import { scopeQuery } from '$lib/utilities/surface-scope';
import type {
	EndpointCoverageRead,
	EndpointDetail,
	EndpointFacetSet,
	EndpointFilter,
	EndpointPage,
	EndpointSummary,
	EndpointTree,
	GonePage,
	HostPage,
	MergedLeafPage,
	ScanStructure,
	HostBrief
} from '$lib/utilities/endpoints';
import type { HttpAssetDetail } from '$lib/types/http-asset';
import type { QueryGroups, QueryLeads } from '$lib/types/asset-query';
import type { IpFacetSet, IpGroupFilter, IpSearchResult } from '$lib/utilities/ip-groups';
import type { OriginExposure } from '$lib/utilities/origins';
import type {
	ScanExposure,
	ServiceFacetSet,
	ServiceFilter,
	ServiceSearchResult
} from '$lib/utilities/services';

export const httpAssetsApi = {
	async detail(projectId: string, assetId: string): Promise<HttpAssetDetail> {
		return api.get<HttpAssetDetail>(`/http-assets/${assetId}?project_id=${projectId}`);
	}
};

export const ipsApi = {
	async search(projectId: string, scanId: string, filter: IpGroupFilter): Promise<IpSearchResult> {
		return api.post<IpSearchResult>(`/ips/search?${scopeQuery({ projectId, scanId })}`, filter);
	},

	async leads(projectId: string, scanId: string, filter: IpGroupFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(`/ips/search/leads?${scopeQuery({ projectId, scanId })}`, filter);
	},

	async groups(
		projectId: string,
		scanId: string,
		groupBy: string,
		filter: IpGroupFilter
	): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/ips/search/groups?${scopeQuery({ projectId, scanId })}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string): Promise<IpFacetSet> {
		return api.get<IpFacetSet>(`/ips/facets?${scopeQuery({ projectId, scanId })}`);
	}
};

export const servicesApi = {
	async search(
		projectId: string,
		scanId: string,
		filter: ServiceFilter
	): Promise<ServiceSearchResult> {
		return api.post<ServiceSearchResult>(
			`/ports/search?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async leads(projectId: string, scanId: string, filter: ServiceFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(`/ports/search/leads?${scopeQuery({ projectId, scanId })}`, filter);
	},

	async groups(
		projectId: string,
		scanId: string,
		groupBy: string,
		filter: ServiceFilter
	): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/ports/search/groups?${scopeQuery({ projectId, scanId })}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string): Promise<ServiceFacetSet> {
		return api.get<ServiceFacetSet>(`/ports/facets?${scopeQuery({ projectId, scanId })}`);
	},

	async exposure(projectId: string, scanId: string): Promise<ScanExposure> {
		return api.get<ScanExposure>(`/ports/exposure?${scopeQuery({ projectId, scanId })}`);
	},

	async origins(projectId: string, scanId: string): Promise<OriginExposure> {
		return api.get<OriginExposure>(`/ports/origins?${scopeQuery({ projectId, scanId })}`);
	}
};

export const endpointsApi = {
	async search(projectId: string, scanId: string, filter: EndpointFilter): Promise<EndpointPage> {
		return api.post<EndpointPage>(`/endpoints/search?${scopeQuery({ projectId, scanId })}`, filter);
	},

	async leads(projectId: string, scanId: string, filter: EndpointFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(
			`/endpoints/search/leads?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async groups(
		projectId: string,
		scanId: string,
		groupBy: string,
		filter: EndpointFilter
	): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/endpoints/search/groups?${scopeQuery({ projectId, scanId })}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async tree(
		projectId: string,
		scanId: string,
		mode: string,
		filter: EndpointFilter
	): Promise<EndpointTree> {
		return api.post<EndpointTree>(
			`/endpoints/tree?${scopeQuery({ projectId, scanId })}&mode=${encodeURIComponent(mode)}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string, q?: string | null): Promise<EndpointFacetSet> {
		const search = q ? `&q=${encodeURIComponent(q)}` : '';
		return api.get<EndpointFacetSet>(
			`/endpoints/facets?${scopeQuery({ projectId, scanId })}${search}`
		);
	},

	async summary(projectId: string, scanId: string, host?: string | null): Promise<EndpointSummary> {
		const scope = host ? `&host=${encodeURIComponent(host)}` : '';
		return api.get<EndpointSummary>(
			`/endpoints/summary?${scopeQuery({ projectId, scanId })}${scope}`
		);
	},

	async hostBrief(
		projectId: string,
		scanId: string,
		host: string,
		hideStatic: boolean
	): Promise<HostBrief> {
		return api.get<HostBrief>(
			`/endpoints/host?${scopeQuery({ projectId, scanId })}&host=${encodeURIComponent(host)}&hide_static=${hideStatic}`
		);
	},

	async gone(projectId: string, scanId: string, filter: EndpointFilter): Promise<GonePage> {
		return api.post<GonePage>(`/endpoints/gone?${scopeQuery({ projectId, scanId })}`, filter);
	},

	async verify(
		projectId: string,
		scanId: string,
		body: { host: string; dir_path: string | null; limit: number }
	): Promise<{ queued: number; unverified: number; accepted: boolean }> {
		return api.post(`/endpoints/verify?${scopeQuery({ projectId, scanId })}`, body);
	},

	async treeHosts(projectId: string, scanId: string, filter: EndpointFilter): Promise<HostPage> {
		return api.post<HostPage>(`/endpoints/tree/hosts?${scopeQuery({ projectId, scanId })}`, filter);
	},

	async mergedLeaves(
		projectId: string,
		scanId: string,
		filter: EndpointFilter
	): Promise<MergedLeafPage> {
		return api.post<MergedLeafPage>(
			`/endpoints/tree/leaves?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async coverage(projectId: string, scanId: string): Promise<EndpointCoverageRead[]> {
		return api.get<EndpointCoverageRead[]>(
			`/endpoints/coverage?${scopeQuery({ projectId, scanId })}`
		);
	},

	async structure(projectId: string, scanId: string): Promise<ScanStructure> {
		return api.get<ScanStructure>(`/endpoints/structure?${scopeQuery({ projectId, scanId })}`);
	},

	async detail(projectId: string, scanId: string, id: string): Promise<EndpointDetail> {
		return api.get<EndpointDetail>(`/endpoints/${id}?${scopeQuery({ projectId, scanId })}`);
	}
};
