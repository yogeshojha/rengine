import { watchesApi } from '$lib/api/watches';
import type { Watch } from '$lib/types/watch';

function createWatchesStore() {
	let watches = $state<Watch[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);

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
			if (isLoading) return;
			isLoading = true;
			error = null;
			try {
				watches = await watchesApi.list(projectId);
				fetchedProjectId = projectId;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Watches not loaded';
			} finally {
				isLoading = false;
			}
		},

		async refresh() {
			if (!fetchedProjectId) return;
			try {
				watches = await watchesApi.list(fetchedProjectId);
			} catch (e) {
				error = e instanceof Error ? e.message : 'Watches not loaded';
			}
		},

		upsert(watch: Watch) {
			const index = watches.findIndex((w) => w.id === watch.id);
			watches = index === -1 ? [watch, ...watches] : watches.with(index, watch);
		},

		remove(id: string) {
			watches = watches.filter((w) => w.id !== id);
		},

		clear() {
			watches = [];
			isLoading = false;
			error = null;
			fetchedProjectId = null;
		}
	};
}

export const watchesStore = createWatchesStore();
