import { dashboardApi } from '$lib/api/dashboard';
import {
	DEFAULT_DASHBOARD_WINDOW,
	type DashboardDiscovery,
	type DashboardOverview,
	type DashboardWindow
} from '$lib/types/dashboard';

function createDashboardStore() {
	let projectId = $state<string | undefined>(undefined);
	let overview = $state<DashboardOverview | null>(null);
	let discovery = $state<DashboardDiscovery | null>(null);
	let changeWindow = $state<DashboardWindow>(DEFAULT_DASHBOARD_WINDOW);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);
	let seq = 0;

	async function load() {
		const pid = projectId;
		const win = changeWindow;
		if (!pid) return;
		const mySeq = ++seq;
		loading = true;
		try {
			const data = await dashboardApi.overview(pid, win);
			if (mySeq !== seq) return;
			overview = data;
			error = null;
			hasFetched = true;
		} catch (e) {
			if (mySeq !== seq) return;
			error = e instanceof Error ? e.message : 'Dashboard could not be loaded';
		} finally {
			if (mySeq === seq) loading = false;
		}
		void loadDiscovery(pid, mySeq);
	}

	// the certificate walk is the one slow rollup, so it lands after the page has painted
	async function loadDiscovery(pid: string, mySeq: number) {
		try {
			const data = await dashboardApi.discovery(pid);
			if (mySeq === seq) discovery = data;
		} catch {
			if (mySeq === seq) discovery = null;
		}
	}

	return {
		get overview() {
			return overview;
		},
		get discovery() {
			return discovery;
		},
		get window() {
			return changeWindow;
		},
		get loading() {
			return loading;
		},
		get error() {
			return error;
		},
		get hasFetched() {
			return hasFetched;
		},

		init(pid: string) {
			if (pid === projectId) {
				if (!hasFetched && !loading) void load();
				return;
			}
			projectId = pid;
			overview = null;
			discovery = null;
			error = null;
			hasFetched = false;
			void load();
		},

		refresh() {
			void load();
		},

		markStale() {
			hasFetched = false;
		},

		setWindow(win: DashboardWindow) {
			if (win === changeWindow) return;
			changeWindow = win;
			void load();
		},

		clear() {
			seq++;
			projectId = undefined;
			overview = null;
			discovery = null;
			changeWindow = DEFAULT_DASHBOARD_WINDOW;
			loading = false;
			error = null;
			hasFetched = false;
		}
	};
}

export const dashboardStore = createDashboardStore();
