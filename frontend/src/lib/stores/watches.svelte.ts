import { watchesApi } from '$lib/api/watches';
import type { Watch } from '$lib/types/watch';

function createWatchesStore() {
	let watches = $state<Watch[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let seq = 0;
	let loadingFor: string | null = null;

	return {
		get watches() {
			return watches;
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
				const rows = await watchesApi.list(projectId);
				if (my !== seq) return;
				watches = rows;
				fetchedProjectId = projectId;
			} catch (e) {
				if (my !== seq) return;
				error = e instanceof Error ? e.message : 'Watches not loaded';
				if (fetchedProjectId !== projectId) {
					watches = [];
					fetchedProjectId = null;
				}
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
				const rows = await watchesApi.list(fetchedProjectId);
				if (my !== seq) return;
				watches = rows;
				error = null;
			} catch {}
		},

		upsert(watch: Watch) {
			const index = watches.findIndex((w) => w.id === watch.id);
			watches = index === -1 ? [watch, ...watches] : watches.with(index, watch);
		},

		remove(id: string) {
			watches = watches.filter((w) => w.id !== id);
		},

		clear() {
			seq++;
			watches = [];
			isLoading = false;
			loadingFor = null;
			error = null;
			fetchedProjectId = null;
		}
	};
}

export const watchesStore = createWatchesStore();
