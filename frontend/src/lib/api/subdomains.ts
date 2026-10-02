import { api } from './client';
import { scopeQuery, type TargetScope } from '$lib/utilities/surface-scope';
import type { HostingComposition } from '$lib/types/hosting';
import type { CorrelationGraph } from '$lib/types/correlation';
import type { RenderGroups } from '$lib/types/subdomain';
import type { QueryCounts, QueryGroups, QueryLeads } from '$lib/types/asset-query';
import type {
	Facet,
	SubdomainFilter,
	SubdomainSearchResult,
	SubdomainFacetSet,
	SubdomainInsights,
	SubdomainCorrelation,
	HygieneSummary
} from '$lib/utilities/scan-insights';

export const subdomainsApi = {
	async search(
		projectId: string,
		scanId: string,
		filter: SubdomainFilter
	): Promise<SubdomainSearchResult> {
		return api.post<SubdomainSearchResult>(
			`/subdomains/search?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async counts(
		projectId: string,
		scanId: string,
		queries: string[],
		scope: TargetScope = {}
	): Promise<QueryCounts> {
		return api.post<QueryCounts>(
			`/subdomains/search/counts?${scopeQuery({ projectId, scanId, ...scope })}`,
			{
				queries
			}
		);
	},

	async tabs(projectId: string, scanId: string, filter: SubdomainFilter): Promise<QueryCounts> {
		return api.post<QueryCounts>(
			`/subdomains/search/tabs?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async leads(projectId: string, scanId: string, filter: SubdomainFilter): Promise<QueryLeads> {
		return api.post<QueryLeads>(
			`/subdomains/search/leads?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async groups(
		projectId: string,
		scanId: string,
		groupBy: string,
		filter: SubdomainFilter
	): Promise<QueryGroups> {
		return api.post<QueryGroups>(
			`/subdomains/search/groups?${scopeQuery({ projectId, scanId })}&group_by=${encodeURIComponent(groupBy)}`,
			filter
		);
	},

	async renders(projectId: string, scanId: string, filter: SubdomainFilter): Promise<RenderGroups> {
		return api.post<RenderGroups>(
			`/subdomains/search/renders?${scopeQuery({ projectId, scanId })}`,
			filter
		);
	},

	async correlationGraph(
		projectId: string,
		scanId: string,
		scope: TargetScope = {}
	): Promise<CorrelationGraph> {
		return api.get<CorrelationGraph>(
			`/subdomains/correlation-graph?${scopeQuery({ projectId, scanId, ...scope })}`
		);
	},

	async hosting(projectId: string, scanId: string): Promise<HostingComposition> {
		return api.get<HostingComposition>(`/subdomains/hosting?${scopeQuery({ projectId, scanId })}`);
	},

	async facets(
		projectId: string,
		scanId: string,
		scope: TargetScope = {}
	): Promise<SubdomainFacetSet> {
		return api.get<SubdomainFacetSet>(
			`/subdomains/facets?${scopeQuery({ projectId, scanId, ...scope })}`
		);
	},

	async tech(projectId: string, scanId: string, search = '', limit = 100): Promise<Facet[]> {
		const sp = new URLSearchParams({
			project_id: projectId,
			scan_id: scanId,
			limit: String(limit)
		});
		if (search.trim()) sp.append('search', search.trim());
		return api.get<Facet[]>(`/subdomains/tech?${sp.toString()}`);
	},

	async hygiene(
		projectId: string,
		scanId: string,
		scope: TargetScope = {}
	): Promise<HygieneSummary> {
		return api.get<HygieneSummary>(
			`/subdomains/hygiene?${scopeQuery({ projectId, scanId, ...scope })}`
		);
	},

	async posture(
		projectId: string,
		scanId: string,
		scope: TargetScope = {}
	): Promise<HygieneSummary> {
		return api.get<HygieneSummary>(
			`/subdomains/posture?${scopeQuery({ projectId, scanId, ...scope })}`
		);
	},

	async insights(projectId: string, scanId: string): Promise<SubdomainInsights> {
		return api.get<SubdomainInsights>(`/subdomains/insights?${scopeQuery({ projectId, scanId })}`);
	},

	async correlation(
		projectId: string,
		scanId: string,
		name: string
	): Promise<SubdomainCorrelation> {
		return api.get<SubdomainCorrelation>(
			`/subdomains/correlation?${scopeQuery({ projectId, scanId })}&name=${encodeURIComponent(name)}`
		);
	}
};
