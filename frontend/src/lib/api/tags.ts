import { api } from './client';

export interface Tag {
	id: string;
	name: string;
	slug: string;
	color: string;
	project_id: string;
	created_at: string;
	created_by: string;
	target_count: number;
}

export interface TagUpdate {
	name?: string;
	color?: string;
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

	async create(data: TagCreate): Promise<Tag> {
		return api.post<Tag>('/tags', data);
	},

	async update(id: string, data: TagUpdate): Promise<Tag> {
		return api.patch<Tag>(`/tags/${id}`, data);
	},

	async remove(id: string): Promise<void> {
		await api.delete(`/tags/${id}`);
	}
};
