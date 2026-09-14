import { api } from './client';
import type {
	DashboardActivity,
	DashboardDiscovery,
	DashboardOverview,
	DashboardPrograms,
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
	},
	async activity(projectId: string, window: DashboardWindow): Promise<DashboardActivity> {
		return api.get<DashboardActivity>(
			`/dashboard/activity?project_id=${projectId}&window=${window}`
		);
	},
	async programs(projectId: string, window: DashboardWindow): Promise<DashboardPrograms> {
		return api.get<DashboardPrograms>(
			`/dashboard/programs?project_id=${projectId}&window=${window}`
		);
	}
};
