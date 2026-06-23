import { api } from './client';
import type { DashboardSignals } from '$lib/types/dashboard';

export const dashboardApi = {
	async signals(projectId: string): Promise<DashboardSignals> {
		return api.get<DashboardSignals>(`/dashboard/signals?project_id=${projectId}`);
	}
};
