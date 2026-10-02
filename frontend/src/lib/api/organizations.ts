import { api } from './client';

export interface Organization {
	id: string;
	name: string;
	slug: string;
	project_id: string;
	created_at: string;
	created_by: string;
	target_count: number;
}

export interface OrganizationUpdate {
	name?: string;
	description?: string | null;
}

export interface OrganizationCreate {
	name: string;
	project_slug: string;
}

interface ListOrganizationsParams {
	project_slug: string;
}

export const organizationsApi = {
	async list(params: ListOrganizationsParams): Promise<Organization[]> {
		const searchParams = new URLSearchParams({ project_slug: params.project_slug });
		return api.get<Organization[]>(`/organizations?${searchParams}`);
	},

	async create(data: OrganizationCreate): Promise<Organization> {
		return api.post<Organization>('/organizations', data);
	},

	async update(id: string, data: OrganizationUpdate): Promise<Organization> {
		return api.patch<Organization>(`/organizations/${id}`, data);
	},

	async remove(id: string): Promise<void> {
		await api.delete(`/organizations/${id}`);
	}
};
