import { scansApi } from '$lib/api/scans';
import type {
	ScanBatchCreate,
	ScanDaily,
	ScanRead,
	ScanStats,
	ScanStatus,
	ScanSortKey,
	ScanSortDir,
	ScanTargetTrend,
	ScanTimeRange
} from '$lib/types/scan';
import { SCAN_TIME_RANGES } from '$lib/types/scan';
import { isLiveStatus } from '$lib/utilities/scan-status';
import { parseScanQuery, type ParsedScanQuery } from '$lib/utilities/scan-query';
import type { PaginatedResponse } from '$lib/types/pagination';

export const HISTORY_DAYS = 30;
const DAY_MS = 86_400_000;

interface ScanFilters {
	projectId?: string;
	targetIds: string[];
	query: string;
	statuses: ScanStatus[];
	startedFrom: string | null;
	startedTo: string | null;
	latest: boolean;
	sortKey: ScanSortKey;
	sortDir: ScanSortDir;
}

interface PaginationState {
	currentPage: number;
	pageSize: number;
	totalItems: number;
	totalPages: number;
}

function defaultFilters(): ScanFilters {
	return {
		query: '',
		targetIds: [],
		statuses: [],
		startedFrom: null,
		startedTo: null,
		latest: false,
		sortKey: 'started',
		sortDir: 'desc'
	};
}

function createScansStore() {
	let scans = $state<ScanRead[]>([]);
	let stats = $state<ScanStats | null>(null);
	let daily = $state<ScanDaily | null>(null);
	let trends = $state<Record<string, ScanTargetTrend>>({});

	let isLoading = $state(false);
	let refreshing = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	let filters = $state<ScanFilters>(defaultFilters());
	let pagination = $state<PaginationState>({
		currentPage: 1,
		pageSize: 25,
		totalItems: 0,
		totalPages: 0
	});

	let loadSeq = 0;
	let queryDebounce: ReturnType<typeof setTimeout> | undefined;

	const parsed = $derived<ParsedScanQuery>(parseScanQuery(filters.query));

	const hasActiveFilters = $derived(
		filters.query.trim() !== '' ||
			filters.statuses.length > 0 ||
			filters.startedFrom !== null ||
			filters.startedTo !== null
	);

	const hasLive = $derived(scans.some((s) => isLiveStatus(s.status)));

	function filterParams() {
		const q = parsed;
		return {
			target_id: filters.targetIds,
			status: filters.statuses.length
				? filters.statuses
				: q.statuses.length
					? q.statuses
					: undefined,
			engine: q.engines.length ? q.engines : undefined,
			search: q.search || undefined,
			severity: q.severities.length ? q.severities : undefined,
			short: q.flags.partial ?? null,
			added: q.flags.added ?? null,
			started_from: filters.startedFrom,
			started_to: filters.startedTo,
			sort_by: filters.sortKey,
			sort_dir: filters.sortDir
		};
	}

	async function fetchAll(page: number | undefined, silent: boolean) {
		const projectId = filters.projectId;
		if (!projectId) return;
		if (parsed.error) {
			isLoading = false;
			return;
		}
		if (page !== undefined) pagination.currentPage = page;
		if (silent) refreshing = true;
		else isLoading = true;
		const seq = ++loadSeq;
		const size = pagination.pageSize;
		try {
			const res: PaginatedResponse<ScanRead> = await scansApi.list(projectId, {
				...filterParams(),
				latest: filters.latest && filters.targetIds.length === 0,
				page: pagination.currentPage,
				size
			});
			if (seq !== loadSeq) return;
			scans = res.items;
			pagination.totalItems = res.total;
			pagination.totalPages = res.pages;
			error = null;
			hasFetched = true;
			fetchTrends(projectId, res.items);
		} catch (e) {
			if (seq === loadSeq && !silent) {
				error = e instanceof Error ? e.message : 'Scans not loaded';
			}
		} finally {
			if (seq === loadSeq) {
				isLoading = false;
				refreshing = false;
			}
		}
	}

	function fetchTrends(projectId: string, rows: ScanRead[]) {
		const ids = [...new Set(rows.map((s) => s.target_id))];
		if (!ids.length) return;
		scansApi
			.trends(projectId, ids)
			.then((list) => {
				if (projectId !== filters.projectId) return;
				const next = { ...trends };
				for (const t of list) next[t.target_id] = t;
				trends = next;
			})
			.catch(() => {});
	}

	function fetchStats() {
		const projectId = filters.projectId;
		const targetIds = filters.targetIds;
		const current = () => projectId === filters.projectId && targetIds === filters.targetIds;
		if (!projectId) return;
		scansApi
			.stats(projectId, targetIds)
			.then((s) => {
				if (current()) stats = s;
			})
			.catch(() => {});
		scansApi
			.daily(projectId, HISTORY_DAYS, targetIds)
			.then((d) => {
				if (current()) daily = d;
			})
			.catch(() => {});
	}

	function reload() {
		pagination.currentPage = 1;
		fetchAll(1, false);
	}

	async function each(
		ids: string[],
		act: (id: string, projectId: string) => Promise<unknown>
	): Promise<{ ok: number; failed: number }> {
		const projectId = filters.projectId;
		if (!projectId) return { ok: 0, failed: ids.length };
		const results = await Promise.allSettled(ids.map((id) => act(id, projectId)));
		const ok = results.filter((r) => r.status === 'fulfilled').length;
		store.refresh();
		return { ok, failed: ids.length - ok };
	}

	function applyRow(updated: ScanRead) {
		const i = scans.findIndex((s) => s.id === updated.id);
		if (i !== -1) scans[i] = { ...scans[i], ...updated, findings: scans[i].findings };
	}

	const store = {
		get scans() {
			return scans;
		},
		get stats() {
			return stats;
		},
		get days() {
			return daily?.days ?? [];
		},
		get daily() {
			return daily;
		},
		get trends() {
			return trends;
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
		get filters() {
			return filters;
		},
		get parsed() {
			return parsed;
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

		init(projectId: string, targetIds: string[] = []) {
			const scopeChanged =
				projectId !== filters.projectId || targetIds.join(',') !== filters.targetIds.join(',');
			if (scopeChanged) {
				filters = { ...defaultFilters(), projectId, targetIds };
				pagination.currentPage = 1;
				scans = [];
				stats = null;
				daily = null;
				trends = {};
				hasFetched = false;
				fetchAll(1, false);
				fetchStats();
			} else if (!hasFetched && !isLoading) {
				fetchAll(undefined, false);
				fetchStats();
			}
		},

		refresh() {
			fetchAll(pagination.currentPage, true);
			fetchStats();
		},

		markStale() {
			hasFetched = false;
		},

		setLatest(latest: boolean) {
			if (filters.latest === latest) return;
			filters.latest = latest;
			scans = [];
			reload();
		},

		loadTargetScans(targetId: string, exclude: string, size = 50): Promise<ScanRead[]> {
			const projectId = filters.projectId;
			if (!projectId) return Promise.resolve([]);
			return scansApi
				.list(projectId, { target_id: targetId, size, sort_by: 'started', sort_dir: 'desc' })
				.then((r) => r.items.filter((s) => s.id !== exclude));
		},

		setQuery(q: string, immediate = false) {
			filters.query = q;
			if (queryDebounce) clearTimeout(queryDebounce);
			if (parseScanQuery(q).error) return;
			if (immediate) reload();
			else queryDebounce = setTimeout(() => reload(), 300);
		},

		setStatuses(statuses: ScanStatus[]) {
			filters.statuses = statuses;
			reload();
		},

		setRange(from: string | null, to: string | null) {
			filters.startedFrom = from;
			filters.startedTo = to;
			reload();
		},

		setTimeRange(range: ScanTimeRange) {
			const n = SCAN_TIME_RANGES.find((r) => r.key === range)?.days;
			store.setRange(n ? new Date(Date.now() - n * DAY_MS).toISOString() : null, null);
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
			filters.query = '';
			filters.statuses = [];
			filters.startedFrom = null;
			filters.startedTo = null;
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
				applyRow(await scansApi.cancel(scan.id, projectId));
				store.refresh();
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan not cancelled';
				return false;
			}
		},

		async pause(scan: ScanRead): Promise<ScanRead | null> {
			const projectId = filters.projectId;
			if (!projectId) return null;
			try {
				const updated = await scansApi.pause(scan.id, projectId);
				applyRow(updated);
				store.refresh();
				return updated;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan not paused';
				return null;
			}
		},

		async resume(scan: ScanRead): Promise<ScanRead | null> {
			const projectId = filters.projectId;
			if (!projectId) return null;
			try {
				const updated = await scansApi.resume(scan.id, projectId);
				applyRow(updated);
				store.refresh();
				return updated;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan not resumed';
				return null;
			}
		},

		async remove(scan: ScanRead): Promise<boolean> {
			const projectId = filters.projectId;
			if (!projectId) return false;
			try {
				await scansApi.remove(scan.id, projectId);
				scans = scans.filter((s) => s.id !== scan.id);
				store.refresh();
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan not deleted';
				return false;
			}
		},

		removeMany(ids: string[]) {
			return each(ids, (id, pid) => scansApi.remove(id, pid));
		},

		cancelMany(ids: string[]) {
			return each(ids, (id, pid) => scansApi.cancel(id, pid));
		},

		async cancelAll(): Promise<number | null> {
			const projectId = filters.projectId;
			if (!projectId) return null;
			error = null;
			try {
				const { cancelled } = await scansApi.cancelAll(projectId, filters.targetIds);
				store.refresh();
				return cancelled;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scans not cancelled';
				return null;
			}
		},

		async launchScans(projectId: string, body: ScanBatchCreate): Promise<ScanRead[] | null> {
			error = null;
			try {
				const created = await scansApi.launchBatch(projectId, body);
				if (projectId === filters.projectId) store.refresh();
				return created;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scans not started';
				return null;
			}
		},

		clear() {
			loadSeq++;
			scans = [];
			stats = null;
			daily = null;
			trends = {};
			filters = defaultFilters();
			pagination = { currentPage: 1, pageSize: 25, totalItems: 0, totalPages: 0 };
			error = null;
			hasFetched = false;
		}
	};
	return store;
}

export const scansStore = createScansStore();
