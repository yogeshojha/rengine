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
	let fetchedProjectId = $state<string | null>(null);
	let seq = 0;
	let loadingFor: string | null = null;

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
		get fetchedProjectId() {
			return fetchedProjectId;
		},

		async fetchContexts(projectId: string) {
			if (isLoading && loadingFor === projectId) return;
			const my = ++seq;
			loadingFor = projectId;
			isLoading = true;
			error = null;
			try {
				const rows = await scanContextsApi.list(projectId);
				if (my !== seq) return;
				contexts = rows;
				hasFetched = true;
				fetchedProjectId = projectId;
			} catch (e) {
				if (my === seq) error = e instanceof Error ? e.message : 'Scan contexts not loaded';
			} finally {
				if (my === seq) {
					isLoading = false;
					loadingFor = null;
				}
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
				error = e instanceof Error ? e.message : 'Scan context not created';
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
				return updated;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan context not saved';
				return null;
			}
		},

		async deleteContext(id: string, projectId?: string): Promise<boolean> {
			error = null;
			try {
				const pid = projectId ?? contexts.find((c) => c.id === id)?.project_id ?? '';
				await scanContextsApi.remove(id, pid);
				contexts = contexts.filter((c) => c.id !== id);
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan context not deleted';
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
				error = e instanceof Error ? e.message : 'Scan context not duplicated';
				return null;
			}
		},

		clear() {
			seq++;
			contexts = [];
			isLoading = false;
			loadingFor = null;
			error = null;
			hasFetched = false;
			fetchedProjectId = null;
		}
	};
}

export const scanContextsStore = createScanContextsStore();
