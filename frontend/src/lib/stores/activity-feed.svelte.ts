import { activityApi } from '$lib/api/activity';
import {
	clusterEvents,
	groupByDay,
	type ActivityLevel,
	type ActivityLog
} from '$lib/types/activity';
import Activity from '@lucide/svelte/icons/activity';
import Crosshair from '@lucide/svelte/icons/crosshair';
import FolderKanban from '@lucide/svelte/icons/folder-kanban';
import Globe from '@lucide/svelte/icons/globe';
import Radar from '@lucide/svelte/icons/radar';
import RadioTower from '@lucide/svelte/icons/radio-tower';
import Server from '@lucide/svelte/icons/server';
import Waypoints from '@lucide/svelte/icons/waypoints';
import { SvelteMap, SvelteSet } from 'svelte/reactivity';
import type { IconComponent } from '$lib/config/icons';

export function getActivityIcon(eventType: string): IconComponent {
	const s = eventType.toLowerCase();
	if (/whois/.test(s)) return Globe;
	if (/dns/.test(s)) return Waypoints;
	if (/bgp|ripe|asn|prefix/.test(s)) return RadioTower;
	if (/scan|recon|nuclei|task/.test(s)) return Radar;
	if (/target/.test(s)) return Crosshair;
	if (/project/.test(s)) return FolderKanban;
	if (/system|user|config|login|logout/.test(s)) return Server;
	return Activity;
}

const STARTED_RE = /\.(started|queued|querying|pending|running)\b|querying/;
const TERMINAL_RE = /\.(completed|complete|finished|done|succeeded|success|failed|error)\b/;

function isStarted(eventType: string): boolean {
	return STARTED_RE.test(eventType.toLowerCase());
}
function isTerminal(eventType: string): boolean {
	return TERMINAL_RE.test(eventType.toLowerCase());
}

export type ActivityFilter = 'all' | 'scan' | 'enrichment' | 'alert' | 'system';
export type ActivityScopeMode = 'current' | 'project';

export const FILTERS: ActivityFilter[] = ['all', 'scan', 'enrichment', 'alert', 'system'];
export const FILTER_LABELS: Record<ActivityFilter, string> = {
	all: 'All',
	scan: 'Scans',
	enrichment: 'Enrichment',
	alert: 'Alerts',
	system: 'System'
};

export const LEVEL_DOT: Record<ActivityLevel, string> = {
	success: 'bg-foreground',
	info: 'bg-muted-foreground/50',
	warning: 'bg-warning',
	error: 'bg-destructive'
};

export function categorize(t: string): ActivityFilter {
	const s = t.toLowerCase();
	if (/scan|recon|nuclei|task/.test(s)) return 'scan';
	if (/enrich|whois|dns|bgp|geoip|ssl/.test(s)) return 'enrichment';
	if (/alert|vuln|critical/.test(s)) return 'alert';
	return 'system';
}

function createActivityFeed() {
	let items = $state<ActivityLog[]>([]);
	let page = $state(1);
	let totalPages = $state(1);
	let loading = $state(false);
	let initialLoad = $state(true);
	let freshIds = $state<Set<string>>(new Set());
	let newCount = $state(0);
	let tick = $state(0);

	let open = $state(false);
	let filter = $state<ActivityFilter>('all');
	let errorsOnly = $state(false);
	let search = $state('');
	let scopeMode = $state<ActivityScopeMode>('project');
	let targetId = $state<string | undefined>(undefined);

	const scoped = $derived(
		scopeMode === 'project' || !targetId ? items : items.filter((a) => a.target_id === targetId)
	);
	const filtered = $derived.by(() => {
		let r = scoped;
		if (filter !== 'all') r = r.filter((a) => categorize(a.event_type) === filter);
		if (errorsOnly) r = r.filter((a) => a.level === 'error');
		const q = search.trim().toLowerCase();
		if (q) {
			r = r.filter(
				(a) => a.title.toLowerCase().includes(q) || (a.description ?? '').toLowerCase().includes(q)
			);
		}
		return r;
	});
	const days = $derived(groupByDay(clusterEvents(filtered)));
	const hasMore = $derived(page < totalPages);
	const latest = $derived(items[0] ?? null);
	const isLive = $derived(freshIds.size > 0);

	const runningIds = $derived.by(() => {
		const latestTerminal = new SvelteMap<string, number>();
		for (const a of items) {
			if (isTerminal(a.event_type)) {
				const key = a.target_id ?? a.id;
				const t = new Date(a.timestamp).getTime();
				if (t > (latestTerminal.get(key) ?? 0)) latestTerminal.set(key, t);
			}
		}
		const running = new SvelteSet<string>();
		for (const a of items) {
			if (!isStarted(a.event_type)) continue;
			const key = a.target_id ?? a.id;
			const t = new Date(a.timestamp).getTime();
			if ((latestTerminal.get(key) ?? 0) < t) running.add(a.id);
		}
		return running;
	});
	const runningCount = $derived.by(() => {
		const targets = new SvelteSet<string>();
		for (const a of items) {
			if (runningIds.has(a.id)) targets.add(a.target_id ?? a.id);
		}
		return targets.size;
	});

	const counts = $derived.by(() => {
		const c: Record<ActivityFilter, number> = {
			all: scoped.length,
			scan: 0,
			enrichment: 0,
			alert: 0,
			system: 0
		};
		for (const a of scoped) c[categorize(a.event_type)]++;
		return c;
	});

	return {
		get items() {
			return items;
		},
		get days() {
			return days;
		},
		get filtered() {
			return filtered;
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
		get freshIds() {
			return freshIds;
		},
		get newCount() {
			return newCount;
		},
		get tick() {
			return tick;
		},
		get open() {
			return open;
		},
		get filter() {
			return filter;
		},
		get scopeMode() {
			return scopeMode;
		},
		get targetId() {
			return targetId;
		},
		get latest() {
			return latest;
		},
		get isLive() {
			return isLive;
		},
		get counts() {
			return counts;
		},
		get errorsOnly() {
			return errorsOnly;
		},
		get search() {
			return search;
		},
		get runningIds() {
			return runningIds;
		},
		get runningCount() {
			return runningCount;
		},

		toggleErrorsOnly() {
			errorsOnly = !errorsOnly;
		},
		setSearch(q: string) {
			search = q;
		},

		setOpen(v: boolean) {
			open = v;
			if (v) newCount = 0;
		},
		toggle() {
			this.setOpen(!open);
		},
		setFilter(f: ActivityFilter) {
			filter = f;
		},
		setScopeMode(s: ActivityScopeMode) {
			scopeMode = s;
		},
		setTargetId(id: string | undefined) {
			targetId = id;
			scopeMode = id ? 'current' : 'project';
			filter = 'all';
		},
		bumpTick() {
			tick++;
		},

		async load(projectId: string, p: number) {
			if (loading) return;
			loading = true;
			try {
				const res = await activityApi.list({ project_id: projectId }, p, 50);
				if (p === 1) {
					items = res.items;
				} else {
					const seen = new Set(items.map((a) => a.id));
					items = [...items, ...res.items.filter((i) => !seen.has(i.id))];
				}
				totalPages = res.pages;
				page = p;
			} catch (e) {
				console.error('[activityFeed]', e);
			} finally {
				loading = false;
				initialLoad = false;
			}
		},
		get page() {
			return page;
		},

		ingest(d: ActivityLog) {
			if (items.some((a) => a.id === d.id)) return;
			freshIds = new Set([...freshIds, d.id]);
			items = [d, ...items];
			if (!open) newCount++;
			setTimeout(() => {
				freshIds = new Set([...freshIds].filter((id) => id !== d.id));
			}, 5000);
		},

		reset() {
			items = [];
			page = 1;
			totalPages = 1;
			initialLoad = true;
			newCount = 0;
			freshIds = new Set();
		}
	};
}

export const activityFeed = createActivityFeed();
