import { api, API_PREFIX } from './client';
import { scopeQuery } from '$lib/utilities/surface-scope';
import type { ExportCreate, ExportRead } from '$lib/types/export';

export const exportsApi = {
	async create(projectId: string, body: ExportCreate): Promise<ExportRead> {
		return api.post<ExportRead>(`/exports?${scopeQuery({ projectId })}`, body);
	},

	async list(
		projectId: string,
		scope: { scanId?: string; targetId?: string } = {}
	): Promise<ExportRead[]> {
		const query = scopeQuery({
			projectId,
			scanId: scope.scanId,
			targetIds: scope.targetId ? [scope.targetId] : undefined
		});
		return api.get<ExportRead[]>(`/exports?${query}`);
	},

	async get(projectId: string, id: string): Promise<ExportRead> {
		return api.get<ExportRead>(`/exports/${id}?${scopeQuery({ projectId })}`);
	},

	async rerun(projectId: string, id: string): Promise<ExportRead> {
		return api.post<ExportRead>(`/exports/${id}/rerun?${scopeQuery({ projectId })}`, {});
	},

	async remove(projectId: string, id: string): Promise<void> {
		return api.delete<void>(`/exports/${id}?${scopeQuery({ projectId })}`);
	},

	downloadUrl(projectId: string, id: string): string {
		return `${API_PREFIX}/exports/${id}/download?${scopeQuery({ projectId })}`;
	}
};
