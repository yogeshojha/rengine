import { api, API_PREFIX } from './client';
import type { ExportCreate, ExportRead } from '$lib/types/export';

function scopeQuery(projectId: string, extra: Record<string, string> = {}): string {
	const sp = new URLSearchParams({ project_id: projectId });
	for (const [key, value] of Object.entries(extra)) if (value) sp.set(key, value);
	return sp.toString();
}

export const exportsApi = {
	async create(projectId: string, body: ExportCreate): Promise<ExportRead> {
		return api.post<ExportRead>(`/exports?${scopeQuery(projectId)}`, body);
	},

	async list(
		projectId: string,
		scope: { scanId?: string; targetId?: string } = {}
	): Promise<ExportRead[]> {
		const query = scopeQuery(projectId, {
			scan_id: scope.scanId ?? '',
			target_id: scope.targetId ?? ''
		});
		return api.get<ExportRead[]>(`/exports?${query}`);
	},

	async get(projectId: string, id: string): Promise<ExportRead> {
		return api.get<ExportRead>(`/exports/${id}?${scopeQuery(projectId)}`);
	},

	async rerun(projectId: string, id: string): Promise<ExportRead> {
		return api.post<ExportRead>(`/exports/${id}/rerun?${scopeQuery(projectId)}`, {});
	},

	async remove(projectId: string, id: string): Promise<void> {
		return api.delete<void>(`/exports/${id}?${scopeQuery(projectId)}`);
	},

	downloadUrl(projectId: string, id: string): string {
		return `${API_PREFIX}/exports/${id}/download?${scopeQuery(projectId)}`;
	}
};
