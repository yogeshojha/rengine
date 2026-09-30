import { tripwiresApi } from '$lib/api/tripwires';
import type { Tripwire, TripwireCatalog } from '$lib/types/tripwire';

function createTripwiresStore() {
	let tripwires = $state<Tripwire[]>([]);
	let catalog = $state<TripwireCatalog | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let catalogPending: Promise<void> | null = null;

	return {
		get tripwires() {
			return tripwires;
		},
		get catalog() {
			return catalog;
		},
		get isLoading() {
			return isLoading;
		},
		get error() {
			return error;
		},
		get fetchedProjectId() {
			return fetchedProjectId;
		},

		async fetch(projectId: string) {
			if (isLoading) return;
			isLoading = true;
			error = null;
			try {
				tripwires = await tripwiresApi.list(projectId);
				fetchedProjectId = projectId;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Tripwires not loaded';
			} finally {
				isLoading = false;
			}
		},

		async refresh() {
			if (!fetchedProjectId) return;
			try {
				tripwires = await tripwiresApi.list(fetchedProjectId);
			} catch (e) {
				error = e instanceof Error ? e.message : 'Tripwires not loaded';
			}
		},

		async loadCatalog(): Promise<TripwireCatalog | null> {
			if (catalog) return catalog;
			catalogPending ??= tripwiresApi
				.catalog()
				.then((c) => {
					catalog = c;
				})
				.catch(() => {})
				.finally(() => {
					catalogPending = null;
				});
			await catalogPending;
			return catalog;
		},

		dimension(key: string) {
			return catalog?.dimensions.find((d) => d.key === key) ?? null;
		},

		channelName(id: string): string | null {
			return catalog?.channels.find((c) => c.id === id)?.name ?? null;
		},

		stageTitle(name: string): string {
			return catalog?.stages.find((s) => s.name === name)?.title ?? name;
		},

		upsert(tripwire: Tripwire) {
			const index = tripwires.findIndex((t) => t.id === tripwire.id);
			tripwires = index === -1 ? [tripwire, ...tripwires] : tripwires.with(index, tripwire);
		},

		remove(id: string) {
			tripwires = tripwires.filter((t) => t.id !== id);
		},

		clear() {
			tripwires = [];
			catalog = null;
			isLoading = false;
			error = null;
			fetchedProjectId = null;
		}
	};
}

export const tripwiresStore = createTripwiresStore();
