import { api } from './client';
import type {
	EndpointCoverageRead,
	EndpointDetail,
	EndpointFacetSet,
	EndpointFilter,
	EndpointPage,
	EndpointSummary,
	EndpointTree,
	HostPage,
	MergedLeafPage,
	ScanStructure
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

export const servicesApi = {
	async search(
		projectId: string,
		scanId: string,
		filter: ServiceFilter
	): Promise<ServiceSearchResult> {
		return api.post<ServiceSearchResult>(
			`/ports/search?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async leads(projectId: string, scanId: string, filter: ServiceFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(
			`/ports/search/leads?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async groups(
		projectId: string,
		scanId: string,
		groupBy: string,
		filter: ServiceFilter
	): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/ports/search/groups?project_id=${projectId}&scan_id=${scanId}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string): Promise<ServiceFacetSet> {
		return api.get<ServiceFacetSet>(`/ports/facets?project_id=${projectId}&scan_id=${scanId}`);
	},

	async exposure(projectId: string, scanId: string): Promise<ScanExposure> {
		return api.get<ScanExposure>(`/ports/exposure?project_id=${projectId}&scan_id=${scanId}`);
	},

	async origins(projectId: string, scanId: string): Promise<OriginExposure> {
		return api.get<OriginExposure>(`/ports/origins?project_id=${projectId}&scan_id=${scanId}`);
	}
};

export const endpointsApi = {
	async search(projectId: string, scanId: string, filter: EndpointFilter): Promise<EndpointPage> {
		return api.post<EndpointPage>(
			`/endpoints/search?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async leads(projectId: string, scanId: string, filter: EndpointFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(
			`/endpoints/search/leads?project_id=${projectId}&scan_id=${scanId}`,
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
			`/endpoints/search/groups?project_id=${projectId}&scan_id=${scanId}&group_by=${encodeURIComponent(groupBy)}`,
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
			`/endpoints/tree?project_id=${projectId}&scan_id=${scanId}&mode=${encodeURIComponent(mode)}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string, q?: string | null): Promise<EndpointFacetSet> {
		const search = q ? `&q=${encodeURIComponent(q)}` : '';
		return api.get<EndpointFacetSet>(
			`/endpoints/facets?project_id=${projectId}&scan_id=${scanId}${search}`
		);
	},

	async summary(projectId: string, scanId: string, host?: string | null): Promise<EndpointSummary> {
		const scope = host ? `&host=${encodeURIComponent(host)}` : '';
		return api.get<EndpointSummary>(
			`/endpoints/summary?project_id=${projectId}&scan_id=${scanId}${scope}`
		);
	},

	async treeHosts(projectId: string, scanId: string, filter: EndpointFilter): Promise<HostPage> {
		return api.post<HostPage>(
			`/endpoints/tree/hosts?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async mergedLeaves(
		projectId: string,
		scanId: string,
		filter: EndpointFilter
	): Promise<MergedLeafPage> {
		return api.post<MergedLeafPage>(
			`/endpoints/tree/leaves?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async coverage(projectId: string, scanId: string): Promise<EndpointCoverageRead[]> {
		return api.get<EndpointCoverageRead[]>(
			`/endpoints/coverage?project_id=${projectId}&scan_id=${scanId}`
		);
	},

	async structure(projectId: string, scanId: string): Promise<ScanStructure> {
		return api.get<ScanStructure>(`/endpoints/structure?project_id=${projectId}&scan_id=${scanId}`);
	},

	async detail(projectId: string, scanId: string, id: string): Promise<EndpointDetail> {
		return api.get<EndpointDetail>(`/endpoints/${id}?project_id=${projectId}&scan_id=${scanId}`);
	}
};
