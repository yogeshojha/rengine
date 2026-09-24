import { api } from './client';
import type {
	DashboardActivity,
	DashboardDiscovery,
	DashboardOverview,
	DashboardPrograms,
	DashboardReadiness,
	DashboardSurfaceRisk,
	DashboardWindow,
	SurfaceRiskFilters
} from '$lib/types/dashboard';
import { appendTargetScope, type TargetScope } from '$lib/utilities/surface-scope';

const scoped = (projectId: string, scope: TargetScope, extra: Record<string, string> = {}) =>
	appendTargetScope(new URLSearchParams({ project_id: projectId, ...extra }), scope).toString();

export const dashboardApi = {
	async overview(
		projectId: string,
		window: DashboardWindow,
		scope: TargetScope = {}
	): Promise<DashboardOverview> {
		return api.get<DashboardOverview>(
			`/dashboard/overview?${scoped(projectId, scope, { window })}`
		);
	},
	async discovery(projectId: string): Promise<DashboardDiscovery> {
		return api.get<DashboardDiscovery>(`/dashboard/discovery?project_id=${projectId}`);
	},
	async readiness(): Promise<DashboardReadiness> {
		return api.get<DashboardReadiness>('/dashboard/readiness');
	},
	async activity(
		projectId: string,
		window: DashboardWindow,
		scope: TargetScope = {}
	): Promise<DashboardActivity> {
		return api.get<DashboardActivity>(
			`/dashboard/activity?${scoped(projectId, scope, { window })}`
		);
	},
	async surfaceRisk(
		projectId: string,
		filters: SurfaceRiskFilters = {}
	): Promise<DashboardSurfaceRisk> {
		const scope: TargetScope = {
			targetIds: filters.targetIds,
			organizationId: filters.organizationId ?? undefined,
			tagId: filters.tagId ?? undefined
		};
		return api.get<DashboardSurfaceRisk>(`/dashboard/surface-risk?${scoped(projectId, scope)}`);
	},
	async programs(projectId: string, window: DashboardWindow): Promise<DashboardPrograms> {
		return api.get<DashboardPrograms>(
			`/dashboard/programs?project_id=${projectId}&window=${window}`
		);
	}
};
