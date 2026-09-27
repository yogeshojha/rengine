import { api } from './client';
import type { DatasetRead, DatasetSyncResult, QueueHealth } from '$lib/types/dataset';

export const datasetsApi = {
	async list(): Promise<DatasetRead[]> {
		return api.get<DatasetRead[]>('/datasets');
	},

	async sync(kind: string): Promise<DatasetSyncResult> {
		return api.post<DatasetSyncResult>(`/datasets/${encodeURIComponent(kind)}/sync`, {});
	},

	async queues(): Promise<QueueHealth> {
		return api.get<QueueHealth>('/health/queues');
	}
};
