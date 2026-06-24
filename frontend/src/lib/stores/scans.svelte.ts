import { scansApi } from '$lib/api/scans';
import type {
	ScanChanges,
	ScanChangeWindow,
	ScanCreate,
	ScanExportRow,
	ScanRead,
	ScanStats,
	ScanStatus,
	ScanSortKey,
	ScanSortDir,
	ScanTargetGroup,
	ScanTimeRange
} from '$lib/types/scan';
import { isLiveStatus } from '$lib/utilities/scan-status';
import type { PaginatedResponse } from '$lib/types/pagination';

interface ScanFilters {
	projectId?: string;
	targetId?: string;
	search: string;
	statuses: ScanStatus[];
	engines: string[];
	contexts: string[];
	timeRange: ScanTimeRange;
	sortKey: ScanSortKey;
	sortDir: ScanSortDir;
	scheduled: boolean | null;
}

export type ScheduleMode = 'all' | 'scheduled' | 'manual';

interface PaginationState {
	currentPage: number;
	pageSize: number;
	totalItems: number;
	totalPages: number;
}

function defaultFilters(): ScanFilters {
	return {
		search: '',
		statuses: [],
		engines: [],
		contexts: [],
		timeRange: 'all',
		sortKey: 'started',
		sortDir: 'desc',
		scheduled: null
	};
}

function createScansStore() {
	let scans = $state<ScanRead[]>([]);
	let targetGroups = $state<ScanTargetGroup[]>([]);
	let groupByTarget = $state(false);
	let stats = $state<ScanStats | null>(null);
	let changes = $state<ScanChanges | null>(null);
	let changeWindow = $state<ScanChangeWindow>('7d');

	let isLoading = $state(false);
	let refreshing = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	let filters = $state<ScanFilters>(defaultFilters());
	let pagination = $state<PaginationState>({
		currentPage: 1,
		pageSize: 20,
		totalItems: 0,
		totalPages: 0
	});

	let loadSeq = 0;
	let searchDebounce: ReturnType<typeof setTimeout> | undefined;

	const hasActiveFilters = $derived(
		filters.search.trim() !== '' ||
			filters.statuses.length > 0 ||
			filters.engines.length > 0 ||
			filters.contexts.length > 0 ||
			filters.timeRange !== 'all' ||
			filters.scheduled !== null
	);

	const hasLive = $derived(
		groupByTarget
			? targetGroups.some((g) => g.running > 0)
			: scans.some((s) => isLiveStatus(s.status))
	);

	function filterParams() {
		return {
			target_id: filters.targetId,
			status: filters.statuses.length ? filters.statuses : undefined,
			engine: filters.engines.length ? filters.engines : undefined,
			context: filters.contexts.length ? filters.contexts : undefined,
			search: filters.search || undefined,
			time_range: filters.timeRange,
			sort_by: filters.sortKey,
			sort_dir: filters.sortDir,
			scheduled: filters.scheduled ?? undefined
		};
	}

	async function fetchAll(page: number | undefined, silent: boolean) {
		const projectId = filters.projectId;
		if (!projectId) return;
		if (page !== undefined) pagination.currentPage = page;
		if (silent) refreshing = true;
		else isLoading = true;
		const seq = ++loadSeq;
		const size = pagination.pageSize === -1 ? undefined : pagination.pageSize;
		try {
			if (groupByTarget) {
				const res = await scansApi.listTargets(projectId, {
					...filterParams(),
					page: pagination.currentPage,
					size
				});
				if (seq !== loadSeq) return;
				targetGroups = res.items;
				pagination.totalItems = res.total;
				pagination.totalPages = res.pages;
			} else {
				const res: PaginatedResponse<ScanRead> = await scansApi.list(projectId, {
					...filterParams(),
					page: pagination.currentPage,
					size
				});
				if (seq !== loadSeq) return;
				scans = res.items;
				pagination.totalItems = res.total;
				pagination.totalPages = res.pages;
			}
			error = null;
			hasFetched = true;
		} catch (e) {
			if (seq === loadSeq && !silent) {
				error = e instanceof Error ? e.message : 'Failed to load scans';
			}
		} finally {
			if (seq === loadSeq) {
				isLoading = false;
				refreshing = false;
			}
		}
	}

	function fetchStats() {
		const projectId = filters.projectId;
		const targetId = filters.targetId;
		if (!projectId) return;
		scansApi
			.stats(projectId, targetId)
			.then((s) => {
				if (projectId === filters.projectId && targetId === filters.targetId) stats = s;
			})
			.catch(() => {});
	}

	function fetchChanges() {
		const projectId = filters.projectId;
		const targetId = filters.targetId;
		const win = changeWindow;
		if (!projectId) return;
		scansApi
			.changes(projectId, win, targetId)
			.then((c) => {
				if (
					projectId === filters.projectId &&
					targetId === filters.targetId &&
					win === changeWindow
				)
					changes = c;
			})
			.catch(() => {});
	}

	function reload() {
		pagination.currentPage = 1;
		fetchAll(1, false);
	}

	return {
		get scans() {
			return scans;
		},
		get targetGroups() {
			return targetGroups;
		},
		get groupByTarget() {
			return groupByTarget;
		},
		get stats() {
			return stats;
		},
		get changes() {
			return changes;
		},
		get changeWindow() {
			return changeWindow;
		},
		get isLoading() {
			return isLoading;
		},
		get refreshing() {
			return refreshing;
		},
		get error() {
			return error;
		},
		get hasFetched() {
			return hasFetched;
		},
		get filters() {
			return filters;
		},
		get pagination() {
			return pagination;
		},
		get hasActiveFilters() {
			return hasActiveFilters;
		},
		get hasLive() {
			return hasLive;
		},
		get engineOptions() {
			return stats?.engines ?? [];
		},
		get contextOptions() {
			return stats?.contexts ?? [];
		},

		init(projectId: string, targetId?: string) {
			const scopeChanged =
				projectId !== filters.projectId || (targetId ?? undefined) !== filters.targetId;
			if (scopeChanged) {
				filters = { ...defaultFilters(), projectId, targetId };
				pagination.currentPage = 1;
				scans = [];
				targetGroups = [];
				stats = null;
				changes = null;
				hasFetched = false;
				fetchAll(1, false);
				fetchStats();
				fetchChanges();
			} else if (!hasFetched && !isLoading) {
				fetchAll(undefined, false);
				fetchStats();
				fetchChanges();
			}
		},

		refresh() {
			fetchAll(pagination.currentPage, true);
			fetchStats();
			fetchChanges();
		},

		markStale() {
			hasFetched = false;
		},

		setChangeWindow(win: ScanChangeWindow) {
			changeWindow = win;
			fetchChanges();
		},

		toggleGroupByTarget() {
			groupByTarget = !groupByTarget;
			pagination.currentPage = 1;
			scans = [];
			targetGroups = [];
			fetchAll(1, false);
		},

		loadTargetScans(targetId: string): Promise<ScanRead[]> {
			const projectId = filters.projectId;
			if (!projectId) return Promise.resolve([]);
			return scansApi
				.list(projectId, { ...filterParams(), target_id: targetId, size: 100 })
				.then((r) => r.items);
		},

		setSearch(q: string) {
			filters.search = q;
			if (searchDebounce) clearTimeout(searchDebounce);
			searchDebounce = setTimeout(() => reload(), 300);
		},

		setStatuses(statuses: ScanStatus[]) {
			filters.statuses = statuses;
			reload();
		},

		toggleStatus(s: ScanStatus) {
			filters.statuses = filters.statuses.includes(s)
				? filters.statuses.filter((v) => v !== s)
				: [...filters.statuses, s];
			reload();
		},

		toggleEngine(name: string) {
			filters.engines = filters.engines.includes(name)
				? filters.engines.filter((v) => v !== name)
				: [...filters.engines, name];
			reload();
		},

		toggleContext(name: string) {
			filters.contexts = filters.contexts.includes(name)
				? filters.contexts.filter((v) => v !== name)
				: [...filters.contexts, name];
			reload();
		},

		setTimeRange(range: ScanTimeRange) {
			filters.timeRange = range;
			reload();
		},

		get scheduleMode(): ScheduleMode {
			return filters.scheduled === null ? 'all' : filters.scheduled ? 'scheduled' : 'manual';
		},

		setScheduleMode(mode: ScheduleMode) {
			filters.scheduled = mode === 'all' ? null : mode === 'scheduled';
			reload();
		},

		setSort(key: ScanSortKey, dir?: ScanSortDir) {
			if (dir) {
				filters.sortKey = key;
				filters.sortDir = dir;
			} else if (filters.sortKey === key) {
				filters.sortDir = filters.sortDir === 'asc' ? 'desc' : 'asc';
			} else {
				filters.sortKey = key;
				filters.sortDir = 'desc';
			}
			reload();
		},

		clearFilters() {
			filters.search = '';
			filters.statuses = [];
			filters.engines = [];
			filters.contexts = [];
			filters.timeRange = 'all';
			filters.scheduled = null;
			reload();
		},

		setPage(page: number) {
			fetchAll(page, false);
		},

		setPageSize(size: number) {
			pagination.pageSize = size;
			pagination.currentPage = 1;
			fetchAll(1, false);
		},

		async cancel(scan: ScanRead): Promise<boolean> {
			const projectId = filters.projectId;
			if (!projectId) return false;
			try {
				await scansApi.cancel(scan.id, projectId);
				this.refresh();
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to cancel scan';
				return false;
			}
		},

		async remove(scan: ScanRead): Promise<boolean> {
			const projectId = filters.projectId;
			if (!projectId) return false;
			try {
				await scansApi.remove(scan.id, projectId);
				this.refresh();
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to delete scan';
				return false;
			}
		},

		async removeMany(ids: string[]): Promise<{ ok: number; failed: number }> {
			const projectId = filters.projectId;
			if (!projectId) return { ok: 0, failed: ids.length };
			const results = await Promise.allSettled(ids.map((id) => scansApi.remove(id, projectId)));
			const ok = results.filter((r) => r.status === 'fulfilled').length;
			this.refresh();
			return { ok, failed: ids.length - ok };
		},

		async cancelMany(ids: string[]): Promise<{ ok: number; failed: number }> {
			const projectId = filters.projectId;
			if (!projectId) return { ok: 0, failed: ids.length };
			const results = await Promise.allSettled(ids.map((id) => scansApi.cancel(id, projectId)));
			const ok = results.filter((r) => r.status === 'fulfilled').length;
			this.refresh();
			return { ok, failed: ids.length - ok };
		},

		exportAll(): Promise<ScanExportRow[]> {
			const projectId = filters.projectId;
			if (!projectId) return Promise.resolve([]);
			return scansApi.exportRows(projectId, {
				target_id: filters.targetId,
				status: filters.statuses.length ? filters.statuses : undefined,
				engine: filters.engines.length ? filters.engines : undefined,
				context: filters.contexts.length ? filters.contexts : undefined,
				search: filters.search || undefined,
				time_range: filters.timeRange,
				sort_by: filters.sortKey,
				sort_dir: filters.sortDir,
				scheduled: filters.scheduled ?? undefined
			});
		},

		async launchScan(projectId: string, body: ScanCreate): Promise<ScanRead | null> {
			error = null;
			try {
				const created = await scansApi.launch(projectId, body);
				if (projectId === filters.projectId) this.refresh();
				return created;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to launch scan';
				return null;
			}
		},

		clear() {
			scans = [];
			targetGroups = [];
			groupByTarget = false;
			stats = null;
			changes = null;
			filters = defaultFilters();
			pagination = { currentPage: 1, pageSize: 20, totalItems: 0, totalPages: 0 };
			error = null;
			hasFetched = false;
		}
	};
}

export const scansStore = createScansStore();
