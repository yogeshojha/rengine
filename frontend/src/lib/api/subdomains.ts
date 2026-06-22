import { api } from './client';
import type { SubdomainRead, SubdomainSummary, TargetSubdomainRead } from '$lib/types/subdomain';

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
	async listByScan(
		projectId: string,
		scanId: string,
		params: ListParams = {}
	): Promise<SubdomainRead[]> {
		const q = buildQuery({ project_id: projectId, scan_id: scanId }, params);
		return api.get<SubdomainRead[]>(`/subdomains?${q}`);
	},

	async scanSummary(projectId: string, scanId: string): Promise<SubdomainSummary> {
		return api.get<SubdomainSummary>(
			`/subdomains/summary?project_id=${projectId}&scan_id=${scanId}`
		);
	},

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
	}
};
