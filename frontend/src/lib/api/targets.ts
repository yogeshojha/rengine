import { api } from './client';
import type {
	Target,
	TargetCreate,
	TargetUpdate,
	TargetValidationRequest,
	TargetValidationResponse,
	TargetType
} from '$lib/types/target';

interface ListTargetsParams {
	project_slug?: string;
	organization_slug?: string;
	target_type?: TargetType;
}

export const targetsApi = {
	async list(params?: ListTargetsParams): Promise<Target[]> {
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

		const query = searchParams.toString();
		const url = query ? `/targets?${query}` : '/targets';

		return api.get<Target[]>(url);
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
