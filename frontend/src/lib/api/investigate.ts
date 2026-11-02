import { api } from './client';
import type { InvestigateBrief, InvestigateFrame, Investigation } from '$lib/types/investigate';

export const investigateApi = {
	brief(projectId: string, scanId: string, fingerprint: string): Promise<InvestigateBrief> {
		const query = new URLSearchParams({
			project_id: projectId,
			scan_id: scanId,
			fingerprint
		});
		return api.get<InvestigateBrief>(`/investigate/brief?${query}`);
	},

	run(
		projectId: string,
		body: { scan_id: string; fingerprint: string },
		onFrame: (frame: InvestigateFrame) => void,
		signal?: AbortSignal
	): Promise<void> {
		return api.stream(
			`/investigate/run?project_id=${projectId}`,
			body,
			(event, data) => onFrame({ event, data } as InvestigateFrame),
			signal
		);
	},

	approve(projectId: string, planIds: string[]): Promise<Investigation> {
		return api.post<Investigation>(`/investigate/approve?project_id=${projectId}`, {
			plan_ids: planIds
		});
	},

	decline(projectId: string, planIds: string[]): Promise<Investigation> {
		return api.post<Investigation>(`/investigate/decline?project_id=${projectId}`, {
			plan_ids: planIds
		});
	}
};
