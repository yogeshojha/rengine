import { api } from './client';
import type { CloudBucketSummary } from '$lib/types/cloud-storage';

export const cloudStorageApi = {
	async scan(projectId: string, scanId: string): Promise<CloudBucketSummary> {
		const sp = new URLSearchParams({ project_id: projectId, scan_id: scanId });
		return api.get<CloudBucketSummary>(`/cloud-storage?${sp.toString()}`);
	},

	async target(projectId: string, targetId: string): Promise<CloudBucketSummary> {
		const sp = new URLSearchParams({ project_id: projectId });
		return api.get<CloudBucketSummary>(`/cloud-storage/target/${targetId}?${sp.toString()}`);
	},

	async triage(
		projectId: string,
		targetId: string,
		buckets: [string, string][],
		state: string
	): Promise<{ updated: number }> {
		const sp = new URLSearchParams({ project_id: projectId });
		return api.patch<{ updated: number }>(`/cloud-storage/triage?${sp.toString()}`, {
			target_id: targetId,
			buckets,
			state
		});
	}
};
