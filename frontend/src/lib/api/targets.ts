import { api } from './client';
import type {
	Target,
	TargetCreate,
	TargetUpdate,
	TargetValidationRequest,
	TargetValidationResponse,
	TargetType,
	TargetBulkCreateRequest,
	TargetBulkCreateResponse,
	TargetImportRequest,
	EnrichmentRefreshResponse
} from '$lib/types/target';

import type { TargetDetailRead } from '@/types/target-detail';

import type { PaginatedResponse, TargetCounts } from '$lib/types/pagination';
import type { SignalFilter, SortDir, SortKey, TargetSummary } from '$lib/utilities/target-signals';

interface ListTargetsParams {
	project_slug?: string;
	search?: string;
	organization_ids?: string[];
	tag_ids?: string[];
	target_type?: TargetType;
	signal?: SignalFilter | null;
	sort_by?: SortKey;
	sort_dir?: SortDir;
	page?: number;
	size?: number;
}

type TargetStatsParams = Pick<
	ListTargetsParams,
	'project_slug' | 'search' | 'organization_ids' | 'tag_ids' | 'target_type'
>;

function buildTargetQuery(params: ListTargetsParams | TargetStatsParams): URLSearchParams {
	const sp = new URLSearchParams();
	if (params.project_slug) sp.append('project_slug', params.project_slug);
	if ('search' in params && params.search?.trim()) sp.append('search', params.search.trim());
	for (const id of params.organization_ids ?? []) sp.append('organization_ids', id);
	for (const id of params.tag_ids ?? []) sp.append('tag_ids', id);
	if (params.target_type) sp.append('target_type', params.target_type);
	return sp;
}

export const targetsApi = {
	async list(params?: ListTargetsParams): Promise<PaginatedResponse<Target>> {
		const sp = buildTargetQuery(params ?? {});
		if (params?.signal) sp.append('signal', params.signal);
		if (params?.sort_by) sp.append('sort_by', params.sort_by);
		if (params?.sort_dir) sp.append('sort_dir', params.sort_dir);
		if (params?.page) sp.append('page', params.page.toString());
		if (params?.size) sp.append('size', params.size.toString());

		const query = sp.toString();
		return api.get<PaginatedResponse<Target>>(query ? `/targets?${query}` : '/targets');
	},

	async getStats(params: TargetStatsParams): Promise<TargetSummary> {
		const query = buildTargetQuery(params).toString();
		return api.get<TargetSummary>(`/targets/stats?${query}`);
	},

	async getMatchingIds(params: ListTargetsParams): Promise<string[]> {
		const sp = buildTargetQuery(params);
		if (params.signal) sp.append('signal', params.signal);
		return api.get<string[]>(`/targets/ids?${sp.toString()}`);
	},

	async bulkEnrich(
		targetIds: string[],
		kind: 'whois' | 'dns' | 'bgp'
	): Promise<{ queued: number }> {
		return api.post<{ queued: number }>('/targets/enrich/bulk', {
			target_ids: targetIds,
			kind
		});
	},

	async bulkAddTags(targetIds: string[], tagNames: string[]): Promise<{ updated: number }> {
		return api.post<{ updated: number }>('/targets/tags/bulk', {
			target_ids: targetIds,
			tag_names: tagNames
		});
	},

	async bulkAddOrganizations(
		targetIds: string[],
		organizationNames: string[]
	): Promise<{ updated: number }> {
		return api.post<{ updated: number }>('/targets/organizations/bulk', {
			target_ids: targetIds,
			organization_names: organizationNames
		});
	},

	async getCounts(projectSlug: string): Promise<TargetCounts> {
		return api.get<TargetCounts>(`/targets/counts?project_slug=${projectSlug}`);
	},

	async get(targetId: string): Promise<Target> {
		return api.get<Target>(`/targets/${targetId}`);
	},

	async create(data: TargetCreate): Promise<Target> {
		return api.post<Target>('/targets', data);
	},

	async update(targetId: string, data: TargetUpdate): Promise<Target> {
		return api.patch<Target>(`/targets/${targetId}`, data);
	},

	async delete(targetId: string): Promise<void> {
		return api.delete(`/targets/${targetId}`);
	},

	async validate(data: TargetValidationRequest): Promise<TargetValidationResponse> {
		return api.post<TargetValidationResponse>('/targets/validate', data);
	},

	async bulkCreate(data: TargetBulkCreateRequest): Promise<TargetBulkCreateResponse> {
		return api.post<TargetBulkCreateResponse>('/targets/bulk', data);
	},

	async importJson(data: TargetImportRequest): Promise<TargetBulkCreateResponse> {
		return api.post<TargetBulkCreateResponse>('/targets/import/json', data);
	},

	async importCsv(projectSlug: string, file: File): Promise<TargetBulkCreateResponse> {
		const formData = new FormData();
		formData.append('file', file);

		const response = await fetch(`/api/v1/targets/import/csv?project_slug=${projectSlug}`, {
			method: 'POST',
			body: formData,
			credentials: 'include'
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.detail || `API Error: ${response.status}`);
		}

		return response.json();
	},

	async refreshDns(targetId: string): Promise<EnrichmentRefreshResponse> {
		return api.post<EnrichmentRefreshResponse>(`/targets/${targetId}/dns/refresh`);
	},

	async refreshWhois(targetId: string): Promise<EnrichmentRefreshResponse> {
		return api.post<EnrichmentRefreshResponse>(`/targets/${targetId}/whois/refresh`);
	},

	async refreshBgp(targetId: string): Promise<EnrichmentRefreshResponse> {
		return api.post<EnrichmentRefreshResponse>(`/targets/${targetId}/bgp/refresh`);
	},

	async getDetail(targetId: string): Promise<TargetDetailRead> {
		return api.get<TargetDetailRead>(`/targets/${targetId}/detail`);
	}
};
