import { api } from './client';
import type {
	Target,
	TargetCreate,
	TargetUpdate,
	TargetValidationRequest,
	TargetValidationResponse,
	TargetType
} from '$lib/types/target';
import type { PaginatedResponse, TargetCounts } from '$lib/types/pagination';

interface ListTargetsParams {
	project_slug?: string;
	organization_slug?: string;
	target_type?: TargetType;
	page?: number;
	size?: number;
}

export const targetsApi = {
	async list(params?: ListTargetsParams): Promise<PaginatedResponse<Target>> {
		const searchParams = new URLSearchParams();

		if (params?.project_slug) {
			searchParams.append('project_slug', params.project_slug);
		}
		if (params?.organization_slug) {
			searchParams.append('organization_slug', params.organization_slug);
		}
		if (params?.target_type) {
			searchParams.append('target_type', params.target_type);
		}
		if (params?.page) {
			searchParams.append('page', params.page.toString());
		}
		if (params?.size) {
			searchParams.append('size', params.size.toString());
		}

		const query = searchParams.toString();
		const url = query ? `/targets?${query}` : '/targets';

		return api.get<PaginatedResponse<Target>>(url);
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
	}
};
