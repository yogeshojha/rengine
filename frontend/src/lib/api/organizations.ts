import { api } from './client';

export interface Organization {
	id: string;
	name: string;
	slug: string;
	project_id: string;
	created_at: string;
	created_by: string;
}

export interface OrganizationCreate {
	name: string;
	project_slug: string;
}

interface ListOrganizationsParams {
	project_slug?: string;
}

export const organizationsApi = {
	async list(params?: ListOrganizationsParams): Promise<Organization[]> {
		const searchParams = new URLSearchParams();

		if (params?.project_slug) {
			searchParams.append('project_slug', params.project_slug);
		}

		const query = searchParams.toString();
		const url = query ? `/organizations?${query}` : '/organizations';

		return api.get<Organization[]>(url);
	},

	async get(projectSlug: string, slug: string): Promise<Organization> {
		return api.get<Organization>(`/organizations/${projectSlug}/${slug}`);
	},

	async create(data: OrganizationCreate): Promise<Organization> {
		return api.post<Organization>('/organizations', data);
	},

	async delete(projectSlug: string, slug: string): Promise<void> {
		return api.delete(`/organizations/${projectSlug}/${slug}`);
	}
};
