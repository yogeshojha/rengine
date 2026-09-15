import { api } from './client';
import type {
	SurfaceCoverage,
	SurfaceDelete,
	SurfaceDeleteResult,
	SurfaceOverview
} from '$lib/types/surface';

export const surfaceApi = {
	async overview(projectId: string): Promise<SurfaceOverview> {
		return api.get<SurfaceOverview>(`/surface/overview?project_id=${projectId}`);
	},

	async coverage(projectId: string, dimension: string): Promise<SurfaceCoverage> {
		return api.get<SurfaceCoverage>(
			`/surface/coverage?project_id=${projectId}&dimension=${encodeURIComponent(dimension)}`
		);
	},

	async remove(
		body: SurfaceDelete,
		scope: { projectId: string; scanId?: string }
	): Promise<SurfaceDeleteResult> {
		const params = new URLSearchParams({ project_id: scope.projectId });
		if (scope.scanId) params.set('scan_id', scope.scanId);
		return api.post<SurfaceDeleteResult>(`/surface/delete?${params}`, body);
	}
};
