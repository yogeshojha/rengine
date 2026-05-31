import { scanContextsApi } from '$lib/api/scan-contexts';
import type {
	ScanContextRead,
	ScanContextCreate,
	ScanContextUpdate
} from '$lib/types/scan-context';

function createScanContextsStore() {
	let contexts = $state<ScanContextRead[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);
	let activeContext = $state<ScanContextRead | null>(null);

	return {
		get contexts() {
			return contexts;
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
		get activeContext() {
			return activeContext;
		},

		async fetchContexts(projectId: string) {
			if (isLoading) return;
			isLoading = true;
			error = null;
			try {
				contexts = await scanContextsApi.list(projectId);
				hasFetched = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to fetch scan contexts';
			} finally {
				isLoading = false;
			}
		},

		async createContext(
			projectId: string,
			data: ScanContextCreate
		): Promise<ScanContextRead | null> {
			error = null;
			try {
				const created = await scanContextsApi.create(projectId, data);
				contexts = [...contexts, created];
				return created;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to create scan context';
				return null;
			}
		},

		async updateContext(
			id: string,
			projectId: string,
			data: ScanContextUpdate
		): Promise<ScanContextRead | null> {
			error = null;
			try {
				const updated = await scanContextsApi.update(id, projectId, data);
				contexts = contexts.map((c) => (c.id === id ? updated : c));
				if (activeContext?.id === id) {
					activeContext = updated;
				}
				return updated;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to update scan context';
				return null;
			}
		},

		async deleteContext(id: string, projectId?: string): Promise<boolean> {
			error = null;
			try {
				const pid = projectId ?? contexts.find((c) => c.id === id)?.project_id ?? '';
				await scanContextsApi.remove(id, pid);
				contexts = contexts.filter((c) => c.id !== id);
				if (activeContext?.id === id) {
					activeContext = null;
				}
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to delete scan context';
				return false;
			}
		},

		async duplicateContext(id: string, projectId: string): Promise<ScanContextRead | null> {
			error = null;
			try {
				const duplicate = await scanContextsApi.duplicate(id, projectId);
				contexts = [...contexts, duplicate];
				return duplicate;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to duplicate scan context';
				return null;
			}
		},

		setActiveContext(context: ScanContextRead | null) {
			activeContext = context;
		},

		clear() {
			contexts = [];
			activeContext = null;
			error = null;
			hasFetched = false;
		}
	};
}

export const scanContextsStore = createScanContextsStore();
