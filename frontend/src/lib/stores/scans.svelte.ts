import { scansApi } from '$lib/api/scans';
import type { ScanCreate, ScanRead, ScanStatus } from '$lib/types/scan';

interface ListScansParams {
	target_id?: string;
	status?: ScanStatus;
}

function createScansStore() {
	let scans = $state<ScanRead[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	return {
		get scans() {
			return scans;
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

		async fetchScans(projectId: string, params: ListScansParams = {}) {
			if (isLoading) return;
			isLoading = true;
			error = null;
			try {
				scans = await scansApi.list(projectId, params);
				hasFetched = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to fetch scans';
			} finally {
				isLoading = false;
			}
		},

		async launchScan(projectId: string, body: ScanCreate): Promise<ScanRead | null> {
			error = null;
			try {
				const created = await scansApi.launch(projectId, body);
				scans = [created, ...scans];
				return created;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to launch scan';
				return null;
			}
		},

		clear() {
			scans = [];
			error = null;
			hasFetched = false;
		}
	};
}

export const scansStore = createScansStore();
