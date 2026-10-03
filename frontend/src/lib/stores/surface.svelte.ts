import { surfaceApi } from '$lib/api/surface';
import type { SurfaceCoverage, SurfaceOverview } from '$lib/types/surface';

function createSurfaceStore() {
	let overview = $state<SurfaceOverview | null>(null);
	let error = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let inflight: Promise<void> | null = null;
	let inflightId: string | null = null;
	let wanted: string | null = null;

	async function load(projectId: string, force = false): Promise<void> {
		if (!projectId) return;
		wanted = projectId;
		if (!force && fetchedProjectId === projectId) return;
		if (inflight && inflightId === projectId) return inflight;
		error = null;
		const pending: Promise<void> = surfaceApi
			.overview(projectId)
			.then((data) => {
				if (wanted !== projectId) return;
				overview = data;
				fetchedProjectId = projectId;
			})
			.catch((e) => {
				if (wanted !== projectId) return;
				error = e instanceof Error ? e.message : 'Coverage not loaded';
				if (fetchedProjectId !== projectId) {
					overview = null;
					fetchedProjectId = null;
				}
			})
			.finally(() => {
				if (inflight !== pending) return;
				inflight = null;
				inflightId = null;
			});
		inflight = pending;
		inflightId = projectId;
		return pending;
	}

	return {
		get overview() {
			return overview;
		},
		get error() {
			return error;
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
			error = null;
			fetchedProjectId = null;
			inflight = null;
			inflightId = null;
			wanted = null;
		}
	};
}

export const surfaceStore = createSurfaceStore();
