import { SvelteMap } from 'svelte/reactivity';
import { scansApi } from '$lib/api/scans';
import { sseStore } from '$lib/stores/sse.svelte';
import { SCAN_EVENT_KIND, SSEChannel, SSEEventType, type ScanEvent } from '$lib/types/sse';
import {
	ACTIVITY_TERMINAL_STATUSES,
	SCAN_COUNT_COLUMNS,
	SCAN_STATUSES,
	type ScanActivityRead,
	type ScanRead
} from '$lib/types/scan';
import { isLiveStatus } from '$lib/utilities/scan-status';

const LIVE_STATUSES = SCAN_STATUSES.filter(isLiveStatus);
const REFRESH_DEBOUNCE_MS = 400;
const FALLBACK_POLL_MS = 30_000;
const LIVE_PAGE_SIZE = 25;

export interface LiveRun {
	stage: { name: string; title: string } | null;
	message: string | null;
	tool: string | null;
	commandId: string | null;
	done: string[];
	failed: string[];
}

const EMPTY_RUN: LiveRun = {
	stage: null,
	message: null,
	tool: null,
	commandId: null,
	done: [],
	failed: []
};

function runFromActivities(activities: ScanActivityRead[]): LiveRun {
	const terminal = activities.filter((a) => ACTIVITY_TERMINAL_STATUSES.includes(a.status));
	const running = activities.filter((a) => a.status === 'running').at(-1);
	return {
		...EMPTY_RUN,
		stage: running ? { name: running.name, title: running.title } : null,
		done: [...new Set(terminal.map((a) => a.name))],
		failed: terminal.filter((a) => a.status === 'failed').map((a) => a.name)
	};
}

function createLiveScansStore() {
	let projectId = $state<string | undefined>(undefined);
	let scans = $state<ScanRead[]>([]);
	let hasFetched = $state(false);
	let completedTick = $state(0);
	const runs = new SvelteMap<string, LiveRun>();
	const previousDurations = new SvelteMap<string, number | null>();

	let sseUnsub: (() => void) | null = null;
	let refreshTimer: ReturnType<typeof setTimeout> | undefined;
	let pollTimer: ReturnType<typeof setTimeout> | undefined;
	let seq = 0;

	const count = $derived(scans.length);
	const hasLive = $derived(count > 0);

	function schedulePoll() {
		clearTimeout(pollTimer);
		if (scans.length > 0) pollTimer = setTimeout(() => void load(), FALLBACK_POLL_MS);
	}

	async function load() {
		const pid = projectId;
		if (!pid) return;
		const mySeq = ++seq;
		try {
			const live = await scansApi.list(pid, {
				status: LIVE_STATUSES,
				size: LIVE_PAGE_SIZE,
				sort_by: 'started',
				sort_dir: 'desc'
			});
			if (mySeq !== seq || pid !== projectId) return;
			scans = live.items;
			hasFetched = true;
			void seedRuns(pid, mySeq);
		} catch (e) {
			console.error('[liveScans]', e);
		} finally {
			if (mySeq === seq) schedulePoll();
		}
	}

	async function seedRuns(pid: string, mySeq: number) {
		const missingRuns = scans.filter((sc) => sc.status === 'running' && !runs.has(sc.id));
		const missingPrev = scans.filter((sc) => !previousDurations.has(sc.id));
		await Promise.all([
			...missingRuns.map(async (sc) => {
				try {
					const activities = await scansApi.activities(sc.id, pid);
					if (mySeq !== seq || pid !== projectId || runs.has(sc.id)) return;
					runs.set(sc.id, runFromActivities(activities));
				} catch {}
			}),
			...missingPrev.map(async (sc) => {
				try {
					const prev = await scansApi.list(pid, {
						target_id: sc.target_id,
						status: ['completed'],
						size: 1,
						sort_by: 'started',
						sort_dir: 'desc'
					});
					if (mySeq !== seq || pid !== projectId) return;
					previousDurations.set(sc.id, prev.items[0]?.duration_seconds ?? null);
				} catch {}
			})
		]);
	}

	function scheduleRefresh() {
		clearTimeout(refreshTimer);
		refreshTimer = setTimeout(() => void load(), REFRESH_DEBOUNCE_MS);
	}

	function patch(scanId: string, update: (run: LiveRun) => Partial<LiveRun>) {
		const current = runs.get(scanId) ?? EMPTY_RUN;
		runs.set(scanId, { ...current, ...update(current) });
	}

	function applyCounts(scanId: string, counts: Record<string, number> | undefined) {
		const scan = scans.find((s) => s.id === scanId);
		if (!scan || !counts) return;
		for (const [key, column] of Object.entries(SCAN_COUNT_COLUMNS)) {
			const value = counts[key];
			if (typeof value === 'number') scan[column] = value;
		}
	}

	function onEvent(e: ScanEvent) {
		switch (e.kind) {
			case SCAN_EVENT_KIND.SCAN_STARTED:
				scheduleRefresh();
				break;
			case SCAN_EVENT_KIND.SCAN_COMPLETED:
			case SCAN_EVENT_KIND.SCAN_FAILED:
			case SCAN_EVENT_KIND.SCAN_CANCELLED:
				runs.delete(e.scan_id);
				previousDurations.delete(e.scan_id);
				completedTick++;
				scheduleRefresh();
				break;
			case SCAN_EVENT_KIND.STAGE_STARTED:
				patch(e.scan_id, () => ({
					stage: { name: e.stage ?? '', title: e.title ?? e.stage ?? '' },
					message: null,
					tool: null,
					commandId: null
				}));
				break;
			case SCAN_EVENT_KIND.STAGE_PROGRESS:
				patch(e.scan_id, () => ({ message: e.message ?? null }));
				break;
			case SCAN_EVENT_KIND.STAGE_COMPLETED: {
				const name = e.stage ?? '';
				patch(e.scan_id, (run) => ({
					stage: run.stage?.name === name ? null : run.stage,
					tool: null,
					commandId: null,
					done: run.done.includes(name) ? run.done : [...run.done, name],
					failed:
						e.status === 'failed' && !run.failed.includes(name) ? [...run.failed, name] : run.failed
				}));
				applyCounts(e.scan_id, e.counts);
				scheduleRefresh();
				break;
			}
			case SCAN_EVENT_KIND.COMMAND_STARTED:
				patch(e.scan_id, () => ({ tool: e.tool ?? null, commandId: e.command_id ?? null }));
				break;
			case SCAN_EVENT_KIND.COMMAND_FINISHED:
				patch(e.scan_id, (run) =>
					run.commandId === e.command_id ? { tool: null, commandId: null } : {}
				);
				break;
		}
	}

	function reset() {
		sseUnsub?.();
		sseUnsub = null;
		clearTimeout(refreshTimer);
		clearTimeout(pollTimer);
		seq++;
		projectId = undefined;
		scans = [];
		hasFetched = false;
		runs.clear();
		previousDurations.clear();
	}

	return {
		get scans() {
			return scans;
		},
		get hasFetched() {
			return hasFetched;
		},
		get count() {
			return count;
		},
		get hasLive() {
			return hasLive;
		},
		get completedTick() {
			return completedTick;
		},

		runFor(scanId: string): LiveRun | undefined {
			return runs.get(scanId);
		},

		isLive(scanId: string): boolean {
			return scans.some((s) => s.id === scanId);
		},

		previousDuration(scanId: string): number | null {
			return previousDurations.get(scanId) ?? null;
		},

		init(pid: string) {
			if (pid === projectId) {
				if (!hasFetched) void load();
				return;
			}
			reset();
			projectId = pid;
			sseUnsub = sseStore.on<ScanEvent>(SSEChannel.project(pid), SSEEventType.SCAN, onEvent);
			void load();
		},

		refresh() {
			scheduleRefresh();
		},

		async cancel(scan: ScanRead): Promise<boolean> {
			const pid = projectId;
			if (!pid) return false;
			try {
				await scansApi.cancel(scan.id, pid);
				scheduleRefresh();
				return true;
			} catch {
				return false;
			}
		},

		clear() {
			reset();
		}
	};
}

export const liveScans = createLiveScansStore();
