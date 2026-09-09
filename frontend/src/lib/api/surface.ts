import { api } from './client';
import type { SurfaceCoverage, SurfaceOverview } from '$lib/types/surface';

export const surfaceApi = {
	async overview(projectId: string): Promise<SurfaceOverview> {
		return api.get<SurfaceOverview>(`/surface/overview?project_id=${projectId}`);
	},

	async coverage(projectId: string, dimension: string): Promise<SurfaceCoverage> {
		return api.get<SurfaceCoverage>(
			`/surface/coverage?project_id=${projectId}&dimension=${encodeURIComponent(dimension)}`
		);
	}
};
