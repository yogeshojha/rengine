import { scanSchedulesApi } from '$lib/api/scan-schedules';
import { scansStore } from '$lib/stores/scans.svelte';
import type {
	ScanScheduleCreate,
	ScanScheduleRead,
	ScanScheduleUpdate
} from '$lib/types/scan-schedule';

function createScanSchedulesStore() {
	let schedules = $state<ScanScheduleRead[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	function replace(updated: ScanScheduleRead) {
		schedules = schedules.map((s) => (s.id === updated.id ? updated : s));
	}

	return {
		get schedules() {
			return schedules;
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

		async fetchSchedules(projectId: string) {
			if (isLoading) return;
			isLoading = true;
			error = null;
			try {
				schedules = await scanSchedulesApi.list(projectId);
				hasFetched = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to fetch schedules';
			} finally {
				isLoading = false;
			}
		},

		async createSchedule(
			projectId: string,
			data: ScanScheduleCreate
		): Promise<ScanScheduleRead | null> {
			error = null;
			try {
				const created = await scanSchedulesApi.create(projectId, data);
				schedules = [created, ...schedules];
				return created;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to create schedule';
				return null;
			}
		},

		async updateSchedule(
			id: string,
			projectId: string,
			data: ScanScheduleUpdate
		): Promise<ScanScheduleRead | null> {
			error = null;
			try {
				const updated = await scanSchedulesApi.update(id, projectId, data);
				replace(updated);
				return updated;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to update schedule';
				return null;
			}
		},

		async setPaused(
			id: string,
			projectId: string,
			paused: boolean
		): Promise<ScanScheduleRead | null> {
			error = null;
			try {
				const updated = paused
					? await scanSchedulesApi.pause(id, projectId)
					: await scanSchedulesApi.resume(id, projectId);
				replace(updated);
				return updated;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to update schedule';
				return null;
			}
		},

		async runNow(id: string, projectId: string): Promise<number | null> {
			error = null;
			try {
				const scans = await scanSchedulesApi.runNow(id, projectId);
				scansStore.markStale();
				return scans.length;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to run schedule';
				return null;
			}
		},

		async deleteSchedule(id: string, projectId: string): Promise<boolean> {
			error = null;
			try {
				await scanSchedulesApi.remove(id, projectId);
				schedules = schedules.filter((s) => s.id !== id);
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to delete schedule';
				return false;
			}
		},

		clear() {
			schedules = [];
			error = null;
			hasFetched = false;
		}
	};
}

export const scanSchedulesStore = createScanSchedulesStore();
