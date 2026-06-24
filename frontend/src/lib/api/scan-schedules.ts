import { api } from './client';
import type {
	ScanScheduleCreate,
	ScanScheduleRead,
	ScanScheduleUpdate
} from '$lib/types/scan-schedule';
import type { ScanRead } from '$lib/types/scan';
import type { PaginatedResponse } from '$lib/types/pagination';

export const scanSchedulesApi = {
	async list(projectId: string): Promise<ScanScheduleRead[]> {
		return api.get<ScanScheduleRead[]>(`/schedules?project_id=${projectId}`);
	},

	async get(id: string, projectId: string): Promise<ScanScheduleRead> {
		return api.get<ScanScheduleRead>(`/schedules/${id}?project_id=${projectId}`);
	},

	async create(projectId: string, data: ScanScheduleCreate): Promise<ScanScheduleRead> {
		return api.post<ScanScheduleRead>(`/schedules?project_id=${projectId}`, data);
	},

	async update(id: string, projectId: string, data: ScanScheduleUpdate): Promise<ScanScheduleRead> {
		return api.patch<ScanScheduleRead>(`/schedules/${id}?project_id=${projectId}`, data);
	},

	async remove(id: string, projectId: string): Promise<void> {
		return api.delete<void>(`/schedules/${id}?project_id=${projectId}`);
	},

	async pause(id: string, projectId: string): Promise<ScanScheduleRead> {
		return api.post<ScanScheduleRead>(`/schedules/${id}/pause?project_id=${projectId}`);
	},

	async resume(id: string, projectId: string): Promise<ScanScheduleRead> {
		return api.post<ScanScheduleRead>(`/schedules/${id}/resume?project_id=${projectId}`);
	},

	async runNow(id: string, projectId: string): Promise<ScanRead[]> {
		return api.post<ScanRead[]>(`/schedules/${id}/run-now?project_id=${projectId}`);
	},

	async listScans(
		id: string,
		projectId: string,
		page = 1,
		size = 20
	): Promise<PaginatedResponse<ScanRead>> {
		return api.get<PaginatedResponse<ScanRead>>(
			`/schedules/${id}/scans?project_id=${projectId}&page=${page}&size=${size}`
		);
	}
};
