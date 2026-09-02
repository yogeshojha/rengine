import { SvelteMap } from 'svelte/reactivity';
import { scansApi } from '$lib/api/scans';
import { sseStore } from '$lib/stores/sse.svelte';
import { SCAN_EVENT_KIND, SSEChannel, SSEEventType, type ScanEvent } from '$lib/types/sse';
import { SCAN_STATUSES, type ScanRead, type ScanStats } from '$lib/types/scan';
import { isLiveStatus } from '$lib/utilities/scan-status';

const LIVE_STATUSES = SCAN_STATUSES.filter(isLiveStatus);
const REFRESH_DEBOUNCE_MS = 400;
const FALLBACK_POLL_MS = 30_000;
const LIVE_PAGE_SIZE = 25;

export interface LiveStage {
	stage: string;
	title: string;
	message: string | null;
}

function createLiveScansStore() {
	let projectId = $state<string | undefined>(undefined);
	let scans = $state<ScanRead[]>([]);
	let stats = $state<ScanStats | null>(null);
	let hasFetched = $state(false);
	let completedTick = $state(0);
	const stages = new SvelteMap<string, LiveStage>();

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
			const [live, s] = await Promise.all([
				scansApi.list(pid, {
					status: LIVE_STATUSES,
					size: LIVE_PAGE_SIZE,
					sort_by: 'started',
					sort_dir: 'desc'
				}),
				scansApi.stats(pid)
			]);
			if (mySeq !== seq || pid !== projectId) return;
			scans = live.items;
			stats = s;
			hasFetched = true;
			void seedStages(pid, mySeq);
		} catch (e) {
			console.error('[liveScans]', e);
		} finally {
			if (mySeq === seq) schedulePoll();
		}
	}

	async function seedStages(pid: string, mySeq: number) {
		const missing = scans.filter((sc) => sc.status === 'running' && !stages.has(sc.id));
		await Promise.all(
			missing.map(async (sc) => {
				try {
					const activities = await scansApi.activities(sc.id, pid);
					if (mySeq !== seq || pid !== projectId || stages.has(sc.id)) return;
					const running = activities.filter((a) => a.status === 'running').at(-1);
					if (running)
						stages.set(sc.id, { stage: running.name, title: running.title, message: null });
				} catch {}
			})
		);
	}

	function scheduleRefresh() {
		clearTimeout(refreshTimer);
		refreshTimer = setTimeout(() => void load(), REFRESH_DEBOUNCE_MS);
	}

	function onEvent(e: ScanEvent) {
		switch (e.kind) {
			case SCAN_EVENT_KIND.SCAN_STARTED:
				scheduleRefresh();
				break;
			case SCAN_EVENT_KIND.SCAN_COMPLETED:
			case SCAN_EVENT_KIND.SCAN_FAILED:
			case SCAN_EVENT_KIND.SCAN_CANCELLED:
				stages.delete(e.scan_id);
				completedTick++;
				scheduleRefresh();
				break;
			case SCAN_EVENT_KIND.STAGE_STARTED:
				stages.set(e.scan_id, {
					stage: e.stage ?? '',
					title: e.title ?? e.stage ?? '',
					message: null
				});
				break;
			case SCAN_EVENT_KIND.STAGE_PROGRESS: {
				const current = stages.get(e.scan_id);
				if (current) stages.set(e.scan_id, { ...current, message: e.message ?? null });
				break;
			}
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
		stats = null;
		hasFetched = false;
		stages.clear();
	}

	return {
		get scans() {
			return scans;
		},
		get stats() {
			return stats;
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

		stageFor(scanId: string): LiveStage | undefined {
			return stages.get(scanId);
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

		clear() {
			reset();
		}
	};
}

export const liveScans = createLiveScansStore();
