import { reportsApi } from '$lib/api/reports';
import type { ReportCatalog, SectionCatalogEntry, ThemeSummary } from '$lib/types/report';

function createReportCatalogStore() {
	let catalog = $state<ReportCatalog | null>(null);
	let isLoading = $state(false);
	let hasFetched = $state(false);
	let loadError = $state<string | null>(null);

	return {
		get catalog() {
			return catalog;
		},
		/** Why the catalog did not load; shown inline where the catalog is used. */
		get loadError() {
			return loadError;
		},
		get sections(): SectionCatalogEntry[] {
			return catalog?.sections ?? [];
		},
		get themes(): ThemeSummary[] {
			return catalog?.themes ?? [];
		},
		get aiAvailable(): boolean {
			return catalog?.ai_available ?? false;
		},

		section(name: string): SectionCatalogEntry | undefined {
			return catalog?.sections.find((s) => s.name === name);
		},

		theme(slug: string): ThemeSummary | undefined {
			return catalog?.themes.find((t) => t.slug === slug);
		},

		sectionsByGroup(group: string): SectionCatalogEntry[] {
			return this.sections.filter((s) => s.group === group);
		},

		async fetch(force = false) {
			if (isLoading || (hasFetched && !force)) return;
			isLoading = true;
			try {
				catalog = await reportsApi.catalog();
				hasFetched = true;
				loadError = null;
			} catch (e) {
				loadError = e instanceof Error ? e.message : 'Report catalog not loaded';
			} finally {
				isLoading = false;
			}
		},

		reset() {
			catalog = null;
			isLoading = false;
			hasFetched = false;
			loadError = null;
		}
	};
}

export const reportCatalog = createReportCatalogStore();
