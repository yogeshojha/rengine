import { api } from './client';
import type {
	ScanContextRead,
	ScanContextCreate,
	ScanContextUpdate
} from '$lib/types/scan-context';

export const scanContextsApi = {
	async list(projectId: string): Promise<ScanContextRead[]> {
		return api.get<ScanContextRead[]>(`/contexts?project_id=${projectId}`);
	},

	async get(id: string, projectId: string): Promise<ScanContextRead> {
		return api.get<ScanContextRead>(`/contexts/${id}?project_id=${projectId}`);
	},

	async create(projectId: string, data: ScanContextCreate): Promise<ScanContextRead> {
		return api.post<ScanContextRead>(`/contexts?project_id=${projectId}`, data);
	},

	async update(
		id: string,
		projectId: string,
		data: ScanContextUpdate
	): Promise<ScanContextRead> {
		return api.patch<ScanContextRead>(`/contexts/${id}?project_id=${projectId}`, data);
	},

	async remove(id: string, projectId: string): Promise<{ deleted: true }> {
		return api.delete<{ deleted: true }>(`/contexts/${id}?project_id=${projectId}`);
	},

	async duplicate(id: string, projectId: string): Promise<ScanContextRead> {
		return api.post<ScanContextRead>(`/contexts/${id}/duplicate?project_id=${projectId}`);
	}
};
