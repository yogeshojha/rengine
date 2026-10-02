import { tripwiresApi } from '$lib/api/tripwires';
import type { Tripwire, TripwireCatalog } from '$lib/types/tripwire';

function createTripwiresStore() {
	let tripwires = $state<Tripwire[]>([]);
	let catalog = $state<TripwireCatalog | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let catalogPending: Promise<void> | null = null;
	let seq = 0;
	let loadingFor: string | null = null;

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
			if (isLoading && loadingFor === projectId) return;
			const my = ++seq;
			loadingFor = projectId;
			isLoading = true;
			error = null;
			try {
				const rows = await tripwiresApi.list(projectId);
				if (my !== seq) return;
				tripwires = rows;
				fetchedProjectId = projectId;
			} catch (e) {
				if (my === seq) error = e instanceof Error ? e.message : 'Tripwires not loaded';
			} finally {
				if (my === seq) {
					isLoading = false;
					loadingFor = null;
				}
			}
		},

		async refresh() {
			if (!fetchedProjectId) return;
			const my = seq;
			try {
				const rows = await tripwiresApi.list(fetchedProjectId);
				if (my === seq) tripwires = rows;
			} catch (e) {
				if (my === seq) error = e instanceof Error ? e.message : 'Tripwires not loaded';
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
			seq++;
			tripwires = [];
			catalog = null;
			isLoading = false;
			loadingFor = null;
			error = null;
			fetchedProjectId = null;
		}
	};
}

export const tripwiresStore = createTripwiresStore();
