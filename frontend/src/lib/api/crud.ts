import { api } from './client';
import type { ActionResult } from '$lib/types/action-result';

export interface CrudApi<Read, Create, Update, Tested extends ActionResult = ActionResult> {
	list(): Promise<Read[]>;
	get(id: string): Promise<Read>;
	create(data: Create): Promise<Read>;
	update(id: string, data: Update): Promise<Read>;
	remove(id: string): Promise<void>;
	test(id: string): Promise<Tested>;
}

/**
 * The list/get/create/update/remove/test calls of a resource mounted at
 * `path`, where each row lives at `${path}/${id}` and is tested with a POST to
 * `${path}/${id}/test`.
 */
export function crudApi<Read, Create, Update, Tested extends ActionResult = ActionResult>(
	path: string
): CrudApi<Read, Create, Update, Tested> {
	return {
		list: () => api.get<Read[]>(path),
		get: (id) => api.get<Read>(`${path}/${id}`),
		create: (data) => api.post<Read>(path, data),
		update: (id, data) => api.patch<Read>(`${path}/${id}`, data),
		remove: (id) => api.delete(`${path}/${id}`),
		test: (id) => api.post<Tested>(`${path}/${id}/test`)
	};
}
