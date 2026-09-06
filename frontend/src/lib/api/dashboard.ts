import { api } from './client';
import type {
	DashboardDiscovery,
	DashboardOverview,
	DashboardReadiness,
	DashboardWindow
} from '$lib/types/dashboard';

export const dashboardApi = {
	async overview(projectId: string, window: DashboardWindow): Promise<DashboardOverview> {
		return api.get<DashboardOverview>(
			`/dashboard/overview?project_id=${projectId}&window=${window}`
		);
	},
	async discovery(projectId: string): Promise<DashboardDiscovery> {
		return api.get<DashboardDiscovery>(`/dashboard/discovery?project_id=${projectId}`);
	},
	async readiness(): Promise<DashboardReadiness> {
		return api.get<DashboardReadiness>('/dashboard/readiness');
	}
};
