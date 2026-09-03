import { api } from './client';
import type { SubdomainSummary, TargetSubdomainRead } from '$lib/types/subdomain';
import type {
	Facet,
	SubdomainFilter,
	SubdomainSearchResult,
	SubdomainFacetSet,
	SubdomainRelation,
	SubdomainInsights,
	SubdomainCorrelation
} from '$lib/utilities/scan-insights';

interface ListParams {
	active_only?: boolean;
	search?: string;
	limit?: number;
	offset?: number;
}

function buildQuery(base: Record<string, string>, params: ListParams): string {
	const sp = new URLSearchParams(base);
	if (params.active_only) sp.append('active_only', 'true');
	if (params.search) sp.append('search', params.search);
	if (params.limit != null) sp.append('limit', String(params.limit));
	if (params.offset != null) sp.append('offset', String(params.offset));
	return sp.toString();
}

export const subdomainsApi = {
	async rollup(
		projectId: string,
		targetId: string,
		params: ListParams = {}
	): Promise<TargetSubdomainRead[]> {
		const q = buildQuery({ project_id: projectId, target_id: targetId }, params);
		return api.get<TargetSubdomainRead[]>(`/subdomains/rollup?${q}`);
	},

	async rollupSummary(projectId: string, targetId: string): Promise<SubdomainSummary> {
		return api.get<SubdomainSummary>(
			`/subdomains/rollup/summary?project_id=${projectId}&target_id=${targetId}`
		);
	},

	async search(
		projectId: string,
		scanId: string,
		filter: SubdomainFilter
	): Promise<SubdomainSearchResult> {
		return api.post<SubdomainSearchResult>(
			`/subdomains/search?project_id=${projectId}&scan_id=${scanId}`,
			filter
		);
	},

	async facets(projectId: string, scanId: string): Promise<SubdomainFacetSet> {
		return api.get<SubdomainFacetSet>(
			`/subdomains/facets?project_id=${projectId}&scan_id=${scanId}`
		);
	},

	async related(projectId: string, scanId: string, name: string): Promise<SubdomainRelation[]> {
		return api.get<SubdomainRelation[]>(
			`/subdomains/related?project_id=${projectId}&scan_id=${scanId}&name=${encodeURIComponent(name)}`
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

	async insights(projectId: string, scanId: string): Promise<SubdomainInsights> {
		return api.get<SubdomainInsights>(
			`/subdomains/insights?project_id=${projectId}&scan_id=${scanId}`
		);
	},

	async correlation(
		projectId: string,
		scanId: string,
		name: string
	): Promise<SubdomainCorrelation> {
		return api.get<SubdomainCorrelation>(
			`/subdomains/correlation?project_id=${projectId}&scan_id=${scanId}&name=${encodeURIComponent(name)}`
		);
	}
};
