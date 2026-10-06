import { activityApi } from '$lib/api/activity';
import { ACTIVITY_PAGE_SIZE } from '$lib/config/activity';
import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { liveScans } from '$lib/stores/live-scans.svelte';
import type { ActivityLog } from '$lib/types/activity';
import { feedRows, groupByDay, unseenFailure } from '$lib/utilities/activity';

function readPinned(): boolean {
	try {
		return localStorage.getItem(STORAGE_KEYS.activityPinned) === '1';
	} catch {
		return false;
	}
}

function writeSeen(at: number): void {
	try {
		localStorage.setItem(STORAGE_KEYS.activitySeen, String(at));
	} catch {}
}

function readSeen(): number {
	try {
		const stored = Number(localStorage.getItem(STORAGE_KEYS.activitySeen));
		if (stored > 0) return stored;
	} catch {}
	const now = Date.now();
	writeSeen(now);
	return now;
}

function createActivityFeed() {
	let items = $state<ActivityLog[]>([]);
	let page = $state(1);
	let totalPages = $state(1);
	let loading = $state(false);
	let initialLoad = $state(true);
	let loadError = $state<string | null>(null);
	let tick = $state(0);
	const initialPinned = readPinned();
	let pinned = $state(initialPinned);
	let open = $state(initialPinned);
	let seenAt = $state(readSeen());
	let seq = 0;

	const rows = $derived(feedRows(items, (id) => liveScans.isLive(id)));
	const days = $derived.by(() => {
		void tick;
		return groupByDay(rows);
	});
	const failure = $derived(unseenFailure(rows, seenAt));
	const hasMore = $derived(page < totalPages);

	function markSeen() {
		seenAt = Date.now();
		writeSeen(seenAt);
	}

	return {
		get days() {
			return days;
		},
		get isEmpty() {
			return rows.length === 0;
		},
		get failure() {
			return failure;
		},
		get hasMore() {
			return hasMore;
		},
		get loading() {
			return loading;
		},
		get initialLoad() {
			return initialLoad;
		},
		get loadError() {
			return loadError;
		},
		get open() {
			return open;
		},
		get pinned() {
			return pinned;
		},
		get page() {
			return page;
		},
		get tick() {
			return tick;
		},

		setOpen(v: boolean) {
			open = v;
			if (v) markSeen();
			else if (pinned) this.setPinned(false);
		},
		setPinned(v: boolean) {
			pinned = v;
			if (v) {
				open = true;
				markSeen();
			}
			try {
				localStorage.setItem(STORAGE_KEYS.activityPinned, v ? '1' : '0');
			} catch {}
		},
		toggle() {
			this.setOpen(!open);
		},
		bumpTick() {
			tick++;
		},

		async load(projectId: string, p: number) {
			if (loading) return;
			loading = true;
			const my = ++seq;
			try {
				const res = await activityApi.list({ project_id: projectId }, p, ACTIVITY_PAGE_SIZE);
				if (my !== seq) return;
				if (p === 1) {
					items = res.items;
				} else {
					const seen = new Set(items.map((a) => a.id));
					items = [...items, ...res.items.filter((i) => !seen.has(i.id))];
				}
				totalPages = res.pages;
				page = p;
				loadError = null;
			} catch (e) {
				if (my !== seq) return;
				loadError = e instanceof Error ? e.message : 'Activity not loaded';
			} finally {
				if (my === seq) {
					loading = false;
					initialLoad = false;
				}
			}
		},

		ingest(d: ActivityLog) {
			if (items.some((a) => a.id === d.id)) return;
			items = [d, ...items];
			if (open) markSeen();
		},

		reset() {
			seq++;
			loading = false;
			items = [];
			page = 1;
			totalPages = 1;
			initialLoad = true;
			loadError = null;
		}
	};
}

export const activityFeed = createActivityFeed();
