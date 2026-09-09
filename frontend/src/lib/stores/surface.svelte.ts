import { surfaceApi } from '$lib/api/surface';
import type { SurfaceCoverage, SurfaceOverview } from '$lib/types/surface';

function createSurfaceStore() {
	let overview = $state<SurfaceOverview | null>(null);
	let loading = $state(false);
	let fetchedProjectId = $state<string | null>(null);
	let inflight: Promise<void> | null = null;

	async function load(projectId: string, force = false): Promise<void> {
		if (!projectId) return;
		if (!force && fetchedProjectId === projectId) return;
		if (inflight) return inflight;
		loading = true;
		inflight = surfaceApi
			.overview(projectId)
			.then((data) => {
				overview = data;
				fetchedProjectId = projectId;
			})
			.catch(() => {
				if (fetchedProjectId !== projectId) overview = null;
			})
			.finally(() => {
				loading = false;
				inflight = null;
			});
		return inflight;
	}

	return {
		get overview() {
			return overview;
		},
		get loading() {
			return loading;
		},
		get dimensions() {
			return overview?.dimensions ?? [];
		},
		get exposures() {
			return overview?.exposures ?? 0;
		},
		coverage(dimension: string): SurfaceCoverage | null {
			return overview?.dimensions.find((d) => d.dimension === dimension) ?? null;
		},
		total(dimension: string): number | null {
			const found = overview?.dimensions.find((d) => d.dimension === dimension);
			return found ? found.total : null;
		},
		load,
		reset() {
			overview = null;
			fetchedProjectId = null;
			loading = false;
			inflight = null;
		}
	};
}

export const surfaceStore = createSurfaceStore();
