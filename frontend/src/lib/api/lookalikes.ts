import { api } from './client';
import type { LookalikeSummary } from '$lib/types/lookalike';

export const lookalikesApi = {
	async scan(projectId: string, scanId: string): Promise<LookalikeSummary> {
		const sp = new URLSearchParams({ project_id: projectId, scan_id: scanId });
		return api.get<LookalikeSummary>(`/lookalikes?${sp.toString()}`);
	},

	async target(projectId: string, targetId: string): Promise<LookalikeSummary> {
		const sp = new URLSearchParams({ project_id: projectId });
		return api.get<LookalikeSummary>(`/lookalikes/target/${targetId}?${sp.toString()}`);
	},

	async triage(
		projectId: string,
		targetId: string,
		domains: string[],
		state: string
	): Promise<{ updated: number }> {
		const sp = new URLSearchParams({ project_id: projectId });
		return api.patch<{ updated: number }>(`/lookalikes/triage?${sp.toString()}`, {
			target_id: targetId,
			domains,
			state
		});
	}
};
