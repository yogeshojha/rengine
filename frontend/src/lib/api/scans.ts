import { api } from './client';
import type { ScanCreate, ScanPreview, ScanRead, ScanStatus } from '$lib/types/scan';

interface ListScansParams {
	target_id?: string;
	status?: ScanStatus;
}

export const scansApi = {
	async preview(projectId: string, body: ScanCreate): Promise<ScanPreview> {
		return api.post<ScanPreview>(`/scans/preview?project_id=${projectId}`, body);
	},

	async launch(projectId: string, body: ScanCreate): Promise<ScanRead> {
		return api.post<ScanRead>(`/scans?project_id=${projectId}`, body);
	},

	async list(projectId: string, params: ListScansParams = {}): Promise<ScanRead[]> {
		const sp = new URLSearchParams({ project_id: projectId });
		if (params.target_id) sp.append('target_id', params.target_id);
		if (params.status) sp.append('status', params.status);
		return api.get<ScanRead[]>(`/scans?${sp.toString()}`);
	},

	async get(id: string, projectId: string): Promise<ScanRead> {
		return api.get<ScanRead>(`/scans/${id}?project_id=${projectId}`);
	}
};
