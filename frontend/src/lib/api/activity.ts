import { api } from './client';
import type { ActivityLog } from '$lib/types/activity';
import type { PaginatedResponse } from '$lib/types/pagination';

export interface ActivityFilters {
	project_id?: string;
}

export const activityApi = {
	list: (
		filters: ActivityFilters = {},
		page = 1,
		size = 20
	): Promise<PaginatedResponse<ActivityLog>> => {
		const params = new URLSearchParams();
		params.set('page', String(page));
		params.set('size', String(size));

		if (filters.project_id) params.set('project_id', filters.project_id);

		return api.get<PaginatedResponse<ActivityLog>>(`/activity?${params.toString()}`);
	}
};
