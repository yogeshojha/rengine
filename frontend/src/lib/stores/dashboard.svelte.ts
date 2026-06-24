import { dashboardApi } from '$lib/api/dashboard';
import { scansApi } from '$lib/api/scans';
import type { DashboardSignals } from '$lib/types/dashboard';
import type { ScanChanges, ScanChangeWindow } from '$lib/types/scan';

function createDashboardStore() {
	let projectId = $state<string | undefined>(undefined);
	let signals = $state<DashboardSignals | null>(null);
	let changes = $state<ScanChanges | null>(null);
	let changeWindow = $state<ScanChangeWindow>('7d');
	let loadingSignals = $state(false);
	let signalsError = $state<string | null>(null);
	let hasFetched = $state(false);

	function fetchSignals() {
		const pid = projectId;
		if (!pid) return;
		loadingSignals = true;
		dashboardApi
			.signals(pid)
			.then((s) => {
				if (pid !== projectId) return;
				signals = s;
				signalsError = null;
				hasFetched = true;
			})
			.catch((e) => {
				if (pid === projectId)
					signalsError = e instanceof Error ? e.message : 'Failed to load signals';
			})
			.finally(() => {
				if (pid === projectId) loadingSignals = false;
			});
	}

	function fetchChanges() {
		const pid = projectId;
		const win = changeWindow;
		if (!pid) return;
		scansApi
			.changes(pid, win)
			.then((c) => {
				if (pid === projectId && win === changeWindow) changes = c;
			})
			.catch(() => {});
	}

	return {
		get signals() {
			return signals;
		},
		get changes() {
			return changes;
		},
		get changeWindow() {
			return changeWindow;
		},
		get loadingSignals() {
			return loadingSignals;
		},
		get signalsError() {
			return signalsError;
		},
		get hasFetched() {
			return hasFetched;
		},

		init(pid: string) {
			if (pid === projectId) {
				if (!hasFetched && !loadingSignals) {
					fetchSignals();
					fetchChanges();
				}
				return;
			}
			projectId = pid;
			signals = null;
			changes = null;
			signalsError = null;
			hasFetched = false;
			fetchSignals();
			fetchChanges();
		},

		refresh() {
			fetchSignals();
			fetchChanges();
		},

		markStale() {
			hasFetched = false;
		},

		setChangeWindow(win: ScanChangeWindow) {
			changeWindow = win;
			fetchChanges();
		},

		retrySignals() {
			fetchSignals();
		},

		clear() {
			projectId = undefined;
			signals = null;
			changes = null;
			changeWindow = '7d';
			loadingSignals = false;
			signalsError = null;
			hasFetched = false;
		}
	};
}

export const dashboardStore = createDashboardStore();
