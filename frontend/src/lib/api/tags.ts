import { api } from './client';

export interface Tag {
	id: string;
	name: string;
	slug: string;
	color: string;
	project_id: string;
	created_at: string;
	created_by: string;
}

export interface TagCreate {
	name: string;
	color: string;
	project_slug: string;
}

interface ListTagsParams {
	project_slug?: string;
}

export const tagsApi = {
	async list(params?: ListTagsParams): Promise<Tag[]> {
		const searchParams = new URLSearchParams();

		if (params?.project_slug) {
			searchParams.append('project_slug', params.project_slug);
		}

		const query = searchParams.toString();
		const url = query ? `/tags?${query}` : '/tags';

		return api.get<Tag[]>(url);
	},

	async get(projectSlug: string, slug: string): Promise<Tag> {
		return api.get<Tag>(`/tags/${projectSlug}/${slug}`);
	},

	async create(data: TagCreate): Promise<Tag> {
		return api.post<Tag>('/tags', data);
	},

	async delete(projectSlug: string, slug: string): Promise<void> {
		return api.delete(`/tags/${projectSlug}/${slug}`);
	},

	async initPredefined(projectSlug: string): Promise<void> {
		return api.post(`/tags/init-predefined?project_slug=${projectSlug}`, {});
	}
};
