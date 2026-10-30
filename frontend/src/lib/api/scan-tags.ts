import { api } from './client';
import type { ScanTagAssignment, ScanTagRead } from '$lib/types/scan';

export const scanTagsApi = {
	list(projectId: string) {
		return api.get<ScanTagRead[]>(`/scan-tags?project_id=${encodeURIComponent(projectId)}`);
	},
	assign(projectId: string, scanIds: string[], add: string[], remove: string[] = []) {
		return api.post<ScanTagAssignment[]>(
			`/scan-tags/assign?project_id=${encodeURIComponent(projectId)}`,
			{ scan_ids: scanIds, add, remove }
		);
	}
};
