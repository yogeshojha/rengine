import { scanEnginesApi } from '$lib/api/scan-engines';
import type { EngineCatalog, StageCatalogEntry } from '$lib/types/scan-engine';

function createEngineCatalogStore() {
	let catalog = $state<EngineCatalog | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	return {
		get catalog() {
			return catalog;
		},
		get stages() {
			return catalog?.stages ?? [];
		},
		get presets() {
			return catalog?.presets ?? [];
		},
		get toolOptions() {
			return catalog?.tool_options ?? [];
		},
		get targetTypes() {
			return catalog?.target_types ?? [];
		},
		get isLoading() {
			return isLoading;
		},
		get error() {
			return error;
		},
		get hasFetched() {
			return hasFetched;
		},

		stage(name: string): StageCatalogEntry | undefined {
			return catalog?.stages.find((s) => s.name === name);
		},

		byPhase(): { phase: string; stages: StageCatalogEntry[] }[] {
			if (!catalog) return [];
			return catalog.phases.map((phase) => ({
				phase,
				stages: catalog!.stages.filter((s) => s.phase === phase)
			}));
		},

		async fetch(force = false) {
			if (isLoading || (hasFetched && !force)) return;
			isLoading = true;
			error = null;
			try {
				catalog = await scanEnginesApi.catalog();
				hasFetched = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to load engine catalog';
			} finally {
				isLoading = false;
			}
		},

		clear() {
			catalog = null;
			error = null;
			hasFetched = false;
		}
	};
}

export const engineCatalogStore = createEngineCatalogStore();
