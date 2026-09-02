import { api } from './client';
import type {
	EngineCatalog,
	EnginePreviewRequest,
	EnginePreviewResult,
	ScanEngine,
	ScanEngineCreate,
	ScanEngineUpdate
} from '$lib/types/scan-engine';

export const scanEnginesApi = {
	async catalog(): Promise<EngineCatalog> {
		return api.get<EngineCatalog>('/engines/catalog');
	},

	async preview(body: EnginePreviewRequest): Promise<EnginePreviewResult> {
		return api.post<EnginePreviewResult>('/engines/preview', body);
	},

	async list(projectId: string): Promise<ScanEngine[]> {
		return api.get<ScanEngine[]>(`/engines?project_id=${projectId}`);
	},

	async get(id: string, projectId: string): Promise<ScanEngine> {
		return api.get<ScanEngine>(`/engines/${id}?project_id=${projectId}`);
	},

	async create(projectId: string, data: ScanEngineCreate): Promise<ScanEngine> {
		return api.post<ScanEngine>(`/engines?project_id=${projectId}`, data);
	},

	async update(id: string, projectId: string, data: ScanEngineUpdate): Promise<ScanEngine> {
		return api.patch<ScanEngine>(`/engines/${id}?project_id=${projectId}`, data);
	},

	async delete(id: string, projectId: string): Promise<{ deleted: true }> {
		return api.delete<{ deleted: true }>(`/engines/${id}?project_id=${projectId}`);
	},

	async duplicate(id: string, projectId: string): Promise<ScanEngine> {
		return api.post<ScanEngine>(`/engines/${id}/duplicate?project_id=${projectId}`);
	},

	async exportYaml(id: string, projectId: string): Promise<{ yaml: string }> {
		return api.get<{ yaml: string }>(`/engines/${id}/export?project_id=${projectId}`);
	},

	async importYaml(projectId: string, yaml: string): Promise<ScanEngine> {
		return api.post<ScanEngine>(`/engines/import?project_id=${projectId}`, { yaml });
	}
};
