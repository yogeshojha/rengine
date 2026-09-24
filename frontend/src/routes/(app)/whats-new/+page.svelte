<script lang="ts">
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteMap, SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import Check from '@lucide/svelte/icons/check';
	import Keyboard from '@lucide/svelte/icons/keyboard';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Search from '@lucide/svelte/icons/search';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Empty from '$lib/components/ui/empty';
	import { Input } from '$lib/components/ui/input';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SelectionActionBar from '$lib/components/selection-action-bar.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import CompareSheet from '$lib/components/scans/history/compare-sheet.svelte';
	import WatchDialog from '$lib/components/bounty-hub/watch-dialog.svelte';
	import { RowSelection } from '$lib/components/scans/results/table/selection.svelte';
	import NewStrip from '$lib/components/whats-new/new-strip.svelte';
	import EventRow from '$lib/components/whats-new/event-row.svelte';
	import VisualPairs from '$lib/components/whats-new/visual-pairs.svelte';
	import VisualCompareDialog from '$lib/components/whats-new/visual-compare-dialog.svelte';
	import DistanceFilter from '$lib/components/whats-new/distance-filter.svelte';
	import PickPopover, { type PickOption } from '$lib/components/whats-new/pick-popover.svelte';
	import { whatsNewApi } from '$lib/api/whats-new';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import { watchesApi } from '$lib/api/watches';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { watchesStore } from '$lib/stores/watches.svelte';
	import { whatsNewStore } from '$lib/stores/whats-new.svelte';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import WebAssetDetailSheet from '$lib/components/scans/results/web-asset-detail-sheet.svelte';
	import { compileQuery, emptyQuery, exactToken } from '$lib/utilities/scan-insights';
	import { SURFACE } from '$lib/config/surface';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import { Capability } from '$lib/config/capabilities';
	import { SurfaceDimension } from '$lib/config/surface';
	import {
		BOUNTY_KINDS,
		GONE_KINDS,
		KIND_ORDER,
		NEW_KEYS,
		NEW_TABS,
		NEW_WINDOWS,
		NewBasis,
		NewKind,
		NewSource,
		NewTab,
		ProgramRing,
		RING_LABELS,
		SELECTABLE_KINDS,
		SIGNAL_LABELS,
		SINCE_KEY,
		SOURCE_KINDS,
		SOURCE_OPTIONS,
		Signal,
		SubjectKind,
		VISUAL_KEYS,
		type NewKindKey,
		type NewSourceKey,
		type NewTabKey,
		type NewWindowKey,
		type SignalKey
	} from '$lib/config/whats-new';
	import { formatShortDate } from '$lib/utilities/dates';
	import { rowHref } from '$lib/utilities/whats-new';
	import type { NewFeed, NewGroup, NewItem, VisualFeed, VisualPair } from '$lib/types/whats-new';

	const WINDOW_KEYS = new Set<string>(NEW_WINDOWS.map((w) => w.key));
	const SOURCE_KEYS = new Set<string>(SOURCE_OPTIONS.map((o) => o.key));
	const TAB_KEYS = new Set<string>(NEW_TABS.map((t) => t.key));
	const SIGNAL_KEYS = new Set<string>([...Object.values(Signal), ...KIND_ORDER]);
	const DAY_RE = /^\d{4}-\d{2}-\d{2}$/;
	const RING_LIBRARY = `ring:${ProgramRing.LIBRARY}`;
	const Q_DEBOUNCE_MS = 250;

	const initial = page.url.searchParams;
	let range = $state<NewWindowKey>(
		WINDOW_KEYS.has(initial.get('window') ?? '')
			? (initial.get('window') as NewWindowKey)
			: SINCE_KEY
	);
	let dayFrom = $state<string | null>(
		DAY_RE.test(initial.get('day') ?? '') ? initial.get('day') : null
	);
	let dayTo = $state<string | null>(
		DAY_RE.test(initial.get('day_to') ?? '') ? initial.get('day_to') : null
	);
	let targetId = $state(initial.get('target') ?? '');
	let program = $state(
		initial.get('ring') === ProgramRing.LIBRARY
			? RING_LIBRARY
			: initial.get('handle') && initial.get('platform')
				? `${initial.get('platform')}:${initial.get('handle')}`
				: ''
	);
	let signal = $state<SignalKey | null>(
		SIGNAL_KEYS.has(initial.get('signal') ?? '') ? (initial.get('signal') as SignalKey) : null
	);
	let source = $state<NewSourceKey>(
		SOURCE_KEYS.has(initial.get('source') ?? '')
			? (initial.get('source') as NewSourceKey)
			: NewSource.ALL
	);
	let q = $state(initial.get('q') ?? '');
	let qApplied = $state(initial.get('q') ?? '');
	let tab = $state<NewTabKey>(
		TAB_KEYS.has(initial.get('tab') ?? '') ? (initial.get('tab') as NewTabKey) : NewTab.TIMELINE
	);

	let visual = $state<VisualFeed | null>(null);
	let visualLoading = $state(false);
	let silentOnly = $state(false);
	let minDistance = $state(1);
	let visualCursor = $state(-1);
	let compareIndex = $state(-1);
	let compareOpen = $state(false);
	let visualReq = 0;
	let feed = $state<NewFeed | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let reqId = 0;

	let cursor = $state(-1);
	const expanded = new SvelteSet<string>();
	const selection = new RowSelection<NewItem>();
	const busy = new SvelteSet<string>();
	let searchRef = $state<HTMLInputElement | null>(null);
	let shortcutsOpen = $state(false);
	let runCompare = $state<{ current: string; baseline: string } | null>(null);

	let watchFor = $state<NewItem | null>(null);
	let launchFor = $state<string | null>(null);
	let removeFor = $state<NewItem | null>(null);
	let removing = $state(false);
	let addingAll = $state<string | null>(null);
	let lastChecked = $state<string | null>(null);
	let sheetSub = $state<SubdomainRead | null>(null);
	let sheetScan = $state('');
	let sheetOpen = $state(false);
	let opening = $state<string | null>(null);
	let catchingUp = $state(false);

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let projectSlug = $derived(projectsStore.activeProject?.slug ?? '');
	let bounty = $derived(capabilitiesStore.has(Capability.BOUNTY_PROGRAMS));
	let sourceOn = $derived(bounty ? source : NewSource.ALL);
	let visibleKinds = $derived(
		KIND_ORDER.filter((k) => (bounty || !BOUNTY_KINDS.has(k)) && SOURCE_KINDS[sourceOn].has(k))
	);
	let wantedKinds = $derived<string[] | null>(sourceOn === NewSource.ALL ? null : visibleKinds);
	let gridKinds = $derived<NewKindKey[]>(visibleKinds.filter((k) => !GONE_KINDS.has(k)));

	const splitProgram = (v: string): [string, string] => {
		const i = v.indexOf(':');
		return i < 0 ? ['', ''] : [v.slice(0, i), v.slice(i + 1)];
	};

	let total = $derived(
		feed
			? visibleKinds.reduce((n, k) => (GONE_KINDS.has(k) ? n : n + (feed?.counts[k] ?? 0)), 0)
			: 0
	);

	const dayLabel = (d: string) =>
		new Date(`${d}T12:00:00Z`).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		});
	const WINDOW_WORDS: Record<string, string> = {
		'24h': '24 hours',
		'7d': '7 days',
		'30d': '30 days'
	};
	let sinceLabel = $derived.by(() => {
		if (!feed) return '';
		if (feed.basis === NewBasis.DAYS && dayFrom) {
			return dayTo && dayTo !== dayFrom
				? `${dayLabel(dayFrom)} to ${dayLabel(dayTo)}`
				: dayLabel(dayFrom);
		}
		const at = new Date(feed.since);
		return `${formatShortDate(at)} ${at.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
	});
	let periodLabel = $derived.by(() => {
		if (!feed) return '';
		if (feed.basis === NewBasis.DAYS) return `on ${sinceLabel}`;
		if (feed.basis === NewBasis.MARK) return 'since caught up';
		return feed.window ? `in the last ${WINDOW_WORDS[feed.window] ?? feed.window}` : '';
	});
	let emptyTitle = $derived(feed ? `Nothing new ${periodLabel}` : '');
	let emptyDescription = $derived(
		feed?.first_runs
			? feed.first_runs === 1
				? 'One first scan set a baseline. New rows appear from the next run of that target.'
				: `${feed.first_runs} first scans set a baseline. New rows appear from the next run of each target.`
			: undefined
	);
	let filtered = $derived(
		!!(targetId || program || qApplied || signal || sourceOn !== NewSource.ALL || dayFrom)
	);

	// ---------- timeline ----------

	interface Entry {
		id: string;
		group: NewGroup;
	}

	function passes(g: NewGroup): boolean {
		if (!signal) return true;
		if (signal === Signal.CRITICAL || signal === Signal.HIGH) {
			return (g.severities[signal] ?? 0) > 0;
		}
		return (g.counts[signal] ?? 0) > 0;
	}
	const dayKey = (iso: string) => new Date(iso).toDateString();
	function dayHeading(iso: string): string {
		const at = new Date(iso);
		const today = new Date();
		const yesterday = new Date(today.getTime() - 86_400_000);
		if (at.toDateString() === today.toDateString()) return 'Today';
		if (at.toDateString() === yesterday.toDateString()) return 'Yesterday';
		return at.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
	}

	let entries = $derived.by<Entry[]>(() => {
		const out: Entry[] = [];
		for (const g of feed?.groups ?? []) {
			if (!passes(g)) continue;
			out.push({ id: g.id, group: g });
		}
		return out;
	});
	let days = $derived.by(() => {
		const out: { key: string; label: string; rows: { entry: Entry; index: number }[] }[] = [];
		entries.forEach((entry, index) => {
			const key = dayKey(entry.group.at);
			let day = out[out.length - 1];
			if (!day || day.key !== key) {
				day = { key, label: dayHeading(entry.group.at), rows: [] };
				out.push(day);
			}
			day.rows.push({ entry, index });
		});
		return out;
	});
	let markedAt = $derived(feed?.marked_at ? new Date(feed.marked_at).getTime() : null);
	let markIndex = $derived(
		markedAt === null ? -1 : entries.findIndex((e) => new Date(e.group.at).getTime() <= markedAt)
	);
	let markLabel = $derived.by(() => {
		if (!feed?.marked_at) return '';
		const at = new Date(feed.marked_at);
		return `${formatShortDate(at)}, ${at.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
	});

	let rowCount = $derived(tab === NewTab.TIMELINE ? entries.length : 0);
	let briefItems = $derived(entries.flatMap((e) => e.group.sections.flatMap((s) => s.items)));

	// ---------- pickers ----------

	let targetOptions = $derived.by<PickOption[]>(() => {
		const seen = new SvelteMap<string, PickOption>();
		for (const t of targetsStore.targets) {
			seen.set(t.id, { value: t.id, label: t.target_value, mono: true });
		}
		for (const g of feed?.groups ?? []) {
			const s = g.subject;
			if (s.kind === SubjectKind.RUN && s.target_id && !seen.has(s.target_id)) {
				seen.set(s.target_id, { value: s.target_id, label: s.label, mono: true });
			}
		}
		return [...seen.values()].sort((a, b) => a.label.localeCompare(b.label));
	});
	let programOptions = $derived.by<PickOption[]>(() => {
		const seen = new SvelteMap<string, PickOption>();
		for (const w of watchesStore.watches) {
			seen.set(`${w.platform}:${w.handle}`, {
				value: `${w.platform}:${w.handle}`,
				label: w.program_name,
				hint: 'Watched'
			});
		}
		for (const g of feed?.groups ?? []) {
			const s = g.subject;
			const key = `${s.platform}:${s.handle}`;
			if (s.kind === SubjectKind.PROGRAM && s.handle && !seen.has(key)) {
				seen.set(key, {
					value: key,
					label: s.label,
					hint: bountyVocabulary.label(s.platform ?? '')
				});
			}
		}
		return [...seen.values()].sort((a, b) => a.label.localeCompare(b.label));
	});
	const ringOptions: PickOption[] = [
		{ value: '', label: RING_LABELS[ProgramRing.ENGAGED] },
		{ value: RING_LIBRARY, label: RING_LABELS[ProgramRing.LIBRARY] }
	];
	let targetLabel = $derived(targetOptions.find((o) => o.value === targetId)?.label ?? '');
	let programLabel = $derived(
		program === RING_LIBRARY
			? RING_LABELS[ProgramRing.LIBRARY]
			: (programOptions.find((o) => o.value === program)?.label ?? splitProgram(program)[1])
	);

	let chips = $derived.by(() => {
		const out: { key: string; label: string; remove: () => void }[] = [];
		if (dayFrom) {
			out.push({
				key: 'day',
				label:
					dayTo && dayTo !== dayFrom
						? `${dayLabel(dayFrom)} to ${dayLabel(dayTo)}`
						: dayLabel(dayFrom),
				remove: () => pickDays(null, null)
			});
		}
		if (signal) {
			out.push({ key: 'signal', label: SIGNAL_LABELS[signal], remove: () => (signal = null) });
		}
		if (targetId) {
			out.push({ key: 'target', label: targetLabel || 'Target', remove: () => (targetId = '') });
		}
		if (program) out.push({ key: 'program', label: programLabel, remove: () => (program = '') });
		if (qApplied) {
			out.push({
				key: 'q',
				label: `"${qApplied}"`,
				remove: () => {
					q = '';
					qApplied = '';
				}
			});
		}
		return out;
	});

	// ---------- loading ----------

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams();
			if (tab !== NewTab.TIMELINE) sp.set('tab', tab);
			if (range !== SINCE_KEY) sp.set('window', range);
			if (dayFrom) sp.set('day', dayFrom);
			if (dayTo) sp.set('day_to', dayTo);
			if (targetId) sp.set('target', targetId);
			if (program === RING_LIBRARY) sp.set('ring', ProgramRing.LIBRARY);
			else if (program) {
				const [platform, handle] = splitProgram(program);
				sp.set('platform', platform);
				sp.set('handle', handle);
			}
			if (bounty && source !== NewSource.ALL) sp.set('source', source);
			if (signal) sp.set('signal', signal);
			if (qApplied) sp.set('q', qApplied);
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, page.state);
		} catch {
			// ignore
		}
	}

	async function load(silent = false) {
		if (!projectId) return;
		const my = ++reqId;
		if (!silent) loading = true;
		error = null;
		const [platform, handle] = program === RING_LIBRARY ? ['', ''] : splitProgram(program);
		try {
			const res = await whatsNewApi.feed(projectId, {
				window: dayFrom ? undefined : range === SINCE_KEY ? undefined : range,
				day: dayFrom ?? undefined,
				day_to: dayTo ?? undefined,
				target_id: targetId || undefined,
				platform: platform || undefined,
				handle: handle || undefined,
				kinds: wantedKinds ? wantedKinds.join(',') : undefined,
				ring: program === RING_LIBRARY ? ProgramRing.LIBRARY : undefined,
				q: qApplied || undefined
			});
			if (my !== reqId) return;
			feed = res;
			if (
				range === SINCE_KEY &&
				res.basis === NewBasis.WINDOW &&
				WINDOW_KEYS.has(res.window ?? '')
			) {
				range = res.window as NewWindowKey;
			}
			if (cursor >= rowCount) cursor = rowCount - 1;
		} catch (e) {
			if (my !== reqId) return;
			error = e instanceof Error ? e.message : 'Feed not loaded';
		} finally {
			if (my === reqId) loading = false;
		}
	}

	async function loadVisual(silent = false) {
		if (!projectId) return;
		const my = ++visualReq;
		if (!silent) visualLoading = true;
		try {
			const res = await whatsNewApi.visual(projectId, {
				window: dayFrom ? undefined : range === SINCE_KEY ? undefined : range,
				day: dayFrom ?? undefined,
				day_to: dayTo ?? undefined,
				target_id: targetId || undefined,
				q: qApplied || undefined
			});
			if (my !== visualReq) return;
			visual = res;
		} catch (e) {
			if (my !== visualReq) return;
			toast.error(e instanceof Error ? e.message : 'Visual changes not loaded');
		} finally {
			if (my === visualReq) visualLoading = false;
		}
	}

	let visualPairs = $derived(
		(visual?.pairs ?? []).filter((p) => (!silentOnly || p.silent) && p.distance >= minDistance)
	);
	let visualDistances = $derived((visual?.pairs ?? []).map((p) => p.distance));

	function openCompare(index: number) {
		compareIndex = index;
		visualCursor = index;
		compareOpen = true;
	}
	function stepCompare(dir: -1 | 1) {
		const next = compareIndex + dir;
		if (next < 0 || next >= visualPairs.length) return;
		compareIndex = next;
		visualCursor = next;
	}
	function scrollVisualCursor() {
		document
			.querySelector(`[data-visual-card="${visualCursor}"]`)
			?.scrollIntoView({ block: 'nearest' });
	}

	let loadedFor = '';
	$effect(() => {
		const id = projectId;
		void range;
		void dayFrom;
		void dayTo;
		void targetId;
		void program;
		void qApplied;
		void source;
		const onVisual = tab === NewTab.VISUAL;
		untrack(() => {
			if (id && loadedFor !== id) {
				loadedFor = id;
				feed = null;
				visual = null;
				selection.clear();
				expanded.clear();
				cursor = -1;
			}
			syncUrl();
			void load();
			if (onVisual) void loadVisual();
		});
	});

	$effect(() => {
		void tab;
		void signal;
		untrack(() => {
			syncUrl();
			cursor = -1;
		});
	});

	$effect(() => {
		const id = projectId;
		const slug = projectSlug;
		if (!id) return;
		untrack(() => {
			if (slug) void targetsStore.fetchAll(slug);
			if (bounty) {
				void bountyVocabulary.load();
				if (watchesStore.fetchedProjectId !== id) void watchesStore.fetch(id);
			}
		});
	});

	$effect(() => {
		const value = q.trim();
		const timer = setTimeout(() => {
			if (value !== qApplied) qApplied = value;
		}, Q_DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	$effect(() => {
		if (liveScans.completedTick > 0) {
			untrack(() => {
				void load(true);
				if (tab === NewTab.VISUAL) void loadVisual(true);
				if (projectId) void whatsNewStore.fetch(projectId, true);
			});
		}
	});

	function setRange(next: NewWindowKey) {
		dayFrom = null;
		dayTo = null;
		range = next;
	}
	function pickDays(from: string | null, to: string | null) {
		dayFrom = from;
		dayTo = to;
	}
	function setSource(next: NewSourceKey) {
		source = next;
		if (
			signal &&
			!SOURCE_KINDS[next].has(signal as string) &&
			KIND_ORDER.includes(signal as NewKindKey)
		) {
			signal = null;
		}
	}
	function setTab(next: NewTabKey) {
		tab = next;
		if (next === NewTab.VISUAL && !visual) void loadVisual();
	}
	function clearFilters() {
		source = NewSource.ALL;
		targetId = '';
		program = '';
		q = '';
		qApplied = '';
		signal = null;
		dayFrom = null;
		dayTo = null;
	}
	function toggle(key: string) {
		if (expanded.has(key)) expanded.delete(key);
		else expanded.add(key);
	}

	// ---------- actions ----------

	async function caughtUp() {
		if (!projectId) return;
		catchingUp = true;
		try {
			await whatsNewStore.caughtUp(projectId);
			dayFrom = null;
			dayTo = null;
			range = SINCE_KEY;
			selection.clear();
			expanded.clear();
			await load();
			toast.success('Marked as caught up');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Not marked');
		} finally {
			catchingUp = false;
		}
	}

	function patch(id: string, fn: (item: NewItem) => void) {
		for (const g of feed?.groups ?? []) {
			for (const section of g.sections) {
				const item = section.items.find((i) => i.id === id);
				if (item) fn(item);
			}
		}
	}

	async function addTargets(items: NewItem[]) {
		const wanted = items.filter((i) => i.importable && i.scope_id && !i.target_exists && i.handle);
		if (!wanted.length || !projectId) return;
		const byProgram = new SvelteMap<string, NewItem[]>();
		for (const i of wanted) {
			const key = `${i.platform}:${i.handle}`;
			byProgram.set(key, [...(byProgram.get(key) ?? []), i]);
		}
		for (const i of wanted) busy.add(i.id);
		let created = 0;
		try {
			for (const [key, group] of byProgram) {
				const [platform, handle] = splitProgram(key);
				const result = await bountyProgramsApi.importScopes(
					handle,
					projectId,
					group.map((i) => i.scope_id ?? ''),
					false,
					true,
					'',
					[platform],
					platform
				);
				created += result.created.length;
				for (const i of group) patch(i.id, (row) => (row.target_exists = true));
			}
			toast.success(created === 1 ? 'Target added' : `${created} targets added`);
			selection.clear();
			void load(true);
			void whatsNewStore.fetch(projectId, true);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Target not added');
		} finally {
			for (const i of wanted) busy.delete(i.id);
		}
	}

	async function muteHosts(items: NewItem[]) {
		const wanted = items.filter((i) => i.kind === NewKind.CERT_HOST && i.watch_id && i.host_id);
		if (!wanted.length || !projectId) return;
		for (const i of wanted) busy.add(i.id);
		try {
			for (const i of wanted) {
				const host = await watchesApi.muteHost(i.watch_id ?? '', i.host_id ?? '', projectId);
				patch(i.id, (row) => (row.muted = host.state === 'muted'));
			}
			const first = wanted[0];
			toast.success(
				wanted.length === 1
					? first.muted
						? 'Host muted'
						: 'Alerts resumed'
					: `${wanted.length} hosts updated`
			);
			selection.clear();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Host not updated');
		} finally {
			for (const i of wanted) busy.delete(i.id);
		}
	}

	function scan(item: NewItem) {
		if (item.target_id) launchFor = item.target_id;
	}

	async function removeTarget() {
		const item = removeFor;
		if (!item?.target_id) return;
		removing = true;
		try {
			await targetsApi.delete(item.target_id);
			toast.success('Target removed');
			removeFor = null;
			void load(true);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Target not removed');
		} finally {
			removing = false;
		}
	}

	function watchProgram() {
		const item = watchFor;
		if (!item?.handle) return null;
		return {
			name: item.program_name ?? item.handle,
			handle: item.handle,
			platform: item.platform ?? '',
			platform_label: bountyVocabulary.label(item.platform ?? '')
		};
	}

	async function addAll(key: string, items: NewItem[]) {
		addingAll = key;
		try {
			await addTargets(items);
		} finally {
			addingAll = null;
		}
	}

	// ---------- sheets ----------

	function closeSheet(open: boolean) {
		sheetOpen = open;
		if (!open) {
			sheetSub = null;
		}
	}

	function scanTab(dimension: SurfaceDimension, dsl: string) {
		const spec = SURFACE[dimension];
		closeSheet(false);
		void goto(ROUTES.scanTab(sheetScan, spec.tab, { [spec.queryParam]: dsl }));
	}

	async function openRow(item: NewItem) {
		const scanId = item.scan_id;
		if (!scanId || !projectId) {
			const link = rowHref(item);
			if (link) void goto(link);
			return;
		}
		if (opening) return;
		opening = item.id;
		try {
			sheetScan = scanId;
			if (item.kind === NewKind.CERT_HOST) {
				const res = await subdomainsApi.search(
					projectId,
					scanId,
					compileQuery({ ...emptyQuery(), search: exactToken('host', item.value) }, 'name', 1, 0, 5)
				);
				const hit = res.items.find((s) => s.name === item.value) ?? null;
				if (!hit) {
					toast.error('Web asset not found in this scan');
					return;
				}
				sheetSub = hit;
			} else {
				const link = rowHref(item);
				if (link) void goto(link);
				return;
			}
			sheetOpen = true;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Row not loaded');
		} finally {
			opening = null;
		}
	}

	async function openPair(pair: VisualPair) {
		if (!projectId || opening) return;
		opening = pair.id;
		try {
			sheetScan = pair.scan_id;
			const res = await subdomainsApi.search(
				projectId,
				pair.scan_id,
				compileQuery({ ...emptyQuery(), search: exactToken('host', pair.host) }, 'name', 1, 0, 5)
			);
			const hit = res.items.find((s) => s.name === pair.host) ?? null;
			if (!hit) {
				toast.error('Web asset not found in this scan');
				return;
			}
			sheetSub = hit;
			sheetOpen = true;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Row not loaded');
		} finally {
			opening = null;
		}
	}

	// ---------- selection ----------

	function check(item: NewItem, shift: boolean) {
		const ids = briefItems.map((i) => i.id);
		const index = ids.indexOf(item.id);
		const last = lastChecked ? ids.indexOf(lastChecked) : -1;
		if (shift && last >= 0 && index >= 0 && last !== index) {
			const [lo, hi] = last < index ? [last, index] : [index, last];
			const on = !selection.has(item.id);
			for (let i = lo; i <= hi; i++) {
				const row = briefItems[i];
				if (!row || !SELECTABLE_KINDS.has(row.kind)) continue;
				if (selection.has(row.id) !== on) selection.toggle(row);
			}
		} else {
			selection.toggle(item);
		}
		lastChecked = item.id;
	}

	let picked = $derived(selection.rows());
	let pickedAddable = $derived(
		picked.filter((i) => i.kind === NewKind.SCOPE && i.importable && !i.target_exists)
	);
	let pickedHosts = $derived(picked.filter((i) => i.kind === NewKind.CERT_HOST));

	// ---------- keyboard ----------

	function scrollCursor() {
		document.querySelector(`[data-event-row="${cursor}"]`)?.scrollIntoView({ block: 'nearest' });
	}

	function eventHref(g: NewGroup): string {
		const s = g.subject;
		if (g.scan_id) return ROUTES.scan(g.scan_id);
		if (s.kind === SubjectKind.PROGRAM && s.handle) {
			return ROUTES.bountyHub(s.handle, s.platform ?? undefined);
		}
		if (s.kind === SubjectKind.TARGETS) return ROUTES.targets;
		return ROUTES.bountyHubTab('updates');
	}

	function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (watchFor || launchFor || removeFor || sheetOpen || compareOpen || runCompare) return;
		const t = e.target as HTMLElement | null;
		const typing =
			!!t &&
			(t.tagName === 'INPUT' ||
				t.tagName === 'TEXTAREA' ||
				t.isContentEditable ||
				!!t.closest('[role=listbox], [role=menu], [role=combobox], [role=dialog]'));
		if (e.key === '/' && !typing) {
			e.preventDefault();
			searchRef?.focus();
			return;
		}
		if (typing) {
			if (e.key === 'Escape') (t as HTMLElement).blur();
			return;
		}
		if (e.key === '?') {
			shortcutsOpen = true;
			return;
		}
		const tabIndex = ['1', '2'].indexOf(e.key);
		if (tabIndex >= 0 && NEW_TABS[tabIndex]) {
			setTab(NEW_TABS[tabIndex].key);
			return;
		}
		if (tab === NewTab.VISUAL) {
			const n = visualPairs.length;
			if (e.key === 'j' || e.key === 'ArrowDown' || e.key === 'ArrowRight') {
				e.preventDefault();
				visualCursor = Math.min(visualCursor + 1, n - 1);
				scrollVisualCursor();
			} else if (e.key === 'k' || e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
				e.preventDefault();
				visualCursor = Math.max(visualCursor - 1, 0);
				scrollVisualCursor();
			} else if (e.key === 'Enter' && visualCursor >= 0 && visualCursor < n) {
				e.preventDefault();
				openCompare(visualCursor);
			} else if (e.key === 's' && visualPairs[visualCursor]) {
				launchFor = visualPairs[visualCursor].target_id;
			} else if (e.key === 'Escape') {
				visualCursor = -1;
			}
			return;
		}
		const entry = entries[cursor] ?? null;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			cursor = Math.min(cursor + 1, rowCount - 1);
			scrollCursor();
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			cursor = Math.max(cursor - 1, 0);
			scrollCursor();
		} else if (e.key === 'o' && entry) {
			toggle(entry.id);
		} else if (e.key === 'Enter' && entry) {
			e.preventDefault();
			void goto(eventHref(entry.group));
		} else if (e.key === 's' && entry?.group.subject.target_id && entry.group.scan_id) {
			launchFor = entry.group.subject.target_id;
		} else if (e.key === 'Escape') {
			if (selection.size) selection.clear();
			else if (entry && expanded.has(entry.id)) expanded.delete(entry.id);
			else cursor = -1;
		}
	}
</script>

<svelte:head><title>{routeLabels['whats-new']} · reNgine</title></svelte:head>

<svelte:window onkeydown={onKey} />

<div class="flex flex-col gap-4">
	<h1 class="sr-only">{routeLabels['whats-new']}</h1>

	<Card.Root class="gap-0 overflow-hidden py-0">
		<NewStrip
			{feed}
			kinds={visibleKinds}
			since={sinceLabel}
			active={signal}
			{gridKinds}
			from={dayFrom}
			to={dayTo}
			onSignal={(s) => (signal = s)}
			onPick={pickDays}
		/>

		<div class="flex flex-wrap items-center justify-between gap-2 border-b px-2">
			<CountTabs
				tabs={NEW_TABS}
				value={tab}
				counts={feed
					? {
							[NewTab.TIMELINE]: total,
							[NewTab.VISUAL]: feed.visual
						}
					: null}
				onChange={(k) => setTab(k as NewTabKey)}
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
			<div class="relative min-w-[200px] flex-1 sm:max-w-xs">
				<Search
					class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
				/>
				<Input
					bind:ref={searchRef}
					bind:value={q}
					placeholder="Filter"
					class="h-9 pl-8"
					aria-label="Filter"
					autocomplete="off"
					spellcheck={false}
				/>
			</div>
			{#if bounty && tab !== NewTab.VISUAL}
				<ToggleGroup.Root
					type="single"
					value={source}
					onValueChange={(v) => v && setSource(v as NewSourceKey)}
					variant="outline"
					aria-label="Source"
				>
					{#each SOURCE_OPTIONS as option (option.key)}
						<ToggleGroup.Item value={option.key} class="h-9 px-3 text-xs font-normal">
							{option.label}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			{/if}
			<PickPopover
				label="All targets"
				value={targetId}
				options={targetOptions}
				heading={[{ value: '', label: 'All targets' }]}
				placeholder="Target"
				onChange={(v) => (targetId = v)}
			/>
			{#if bounty && sourceOn !== NewSource.TARGETS && tab !== NewTab.VISUAL}
				<PickPopover
					label={RING_LABELS[ProgramRing.ENGAGED]}
					value={program}
					options={programOptions}
					heading={ringOptions}
					placeholder="Program"
					onChange={(v) => (program = v)}
				/>
			{/if}
			{#if tab === NewTab.VISUAL && visual}
				<DistanceFilter
					distances={visualDistances}
					min={minDistance}
					onChange={(v) => (minDistance = v)}
				/>
				<Button
					variant={silentOnly ? 'secondary' : 'outline'}
					class="h-9 text-xs font-normal"
					aria-pressed={silentOnly}
					onclick={() => (silentOnly = !silentOnly)}
				>
					Silent redeploys{#if visual.silent}
						<span class="text-muted-foreground tabular-nums">{visual.silent}</span>{/if}
				</Button>
			{/if}
			<div class="flex flex-wrap items-center gap-2 lg:ml-auto">
				<ToggleGroup.Root
					type="single"
					value={dayFrom ? '' : range}
					onValueChange={(v) => v && setRange(v as NewWindowKey)}
					variant="outline"
					aria-label="Period"
				>
					{#each NEW_WINDOWS as option (option.key)}
						<ToggleGroup.Item value={option.key} class="h-9 px-3 text-xs font-normal">
							{option.label}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
				<Hint text="Keyboard shortcuts">
					{#snippet child(props)}
						<Button
							{...props}
							variant="outline"
							size="icon"
							class="hidden size-9 sm:inline-flex"
							aria-label="Keyboard shortcuts"
							onclick={() => (shortcutsOpen = true)}
						>
							<Keyboard class="size-4" />
						</Button>
					{/snippet}
				</Hint>
				<LoadingButton
					class="h-9 gap-2"
					loading={catchingUp}
					loadingLabel="Marking"
					onclick={caughtUp}
					disabled={!feed}
				>
					<Check class="size-4" />
					Caught up
				</LoadingButton>
			</div>
		</div>

		{#if chips.length > 0}
			<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
				{#each chips as chip (chip.key)}
					<Badge variant="outline" class="gap-1 bg-background font-normal">
						{chip.label}
						<button
							type="button"
							class="rounded-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							onclick={chip.remove}
							aria-label="Remove filter {chip.label}"
						>
							<X class="size-3" />
						</button>
					</Badge>
				{/each}
				{#if filtered}
					<button
						type="button"
						class="ml-auto text-xs text-muted-foreground hover:text-foreground"
						onclick={clearFilters}
					>
						Clear all
					</button>
				{/if}
			</div>
		{/if}

		{#if tab === NewTab.VISUAL}
			<div class="p-4">
				{#if visual && !visualLoading && visualPairs.length === 0}
					<EmptyState
						icon={Sparkles}
						title={silentOnly
							? `No silent redeploys ${periodLabel}`
							: `No visual changes ${periodLabel}`}
						description="A web asset counts once both runs captured it and the screenshots differ."
					/>
				{:else if visual}
					<div class="transition-opacity {visualLoading ? 'opacity-60' : ''}">
						<VisualPairs
							pairs={visualPairs}
							cursor={visualCursor}
							onOpen={openPair}
							onCompare={openCompare}
							onScan={(pair) => (launchFor = pair.target_id)}
							onPick={(i) => (visualCursor = i)}
						/>
						{#if visual.truncated}
							<p class="py-3 text-center text-xs text-muted-foreground">
								Largest {visual.pairs.length} changes shown.
							</p>
						{/if}
					</div>
				{:else}
					<div class="grid grid-cols-[repeat(auto-fill,minmax(21rem,1fr))] gap-3">
						{#each { length: 6 } as _, i (i)}
							<Skeleton class="h-52 rounded-xl" />
						{/each}
					</div>
				{/if}
			</div>
		{:else if error}
			<Empty.Root class="py-16">
				<Empty.Header>
					<Empty.Media class="size-12 rounded-2xl bg-destructive/10">
						<TriangleAlert class="size-6 text-destructive" />
					</Empty.Media>
					<Empty.Title>What's new not loaded</Empty.Title>
					<Empty.Description class="max-w-md">{error}</Empty.Description>
				</Empty.Header>
				<Empty.Content>
					<Button variant="outline" class="gap-2" onclick={() => load()}>
						<RefreshCw class="size-4" /> Retry
					</Button>
				</Empty.Content>
			</Empty.Root>
		{:else if !feed}
			<div class="flex flex-col" aria-busy="true">
				<div class="border-b bg-muted/20 px-4 py-2"><Skeleton class="h-3 w-40" /></div>
				{#each { length: 8 } as _, i (i)}
					<div class="flex items-center gap-3 border-b border-border/60 px-4 py-3">
						<Skeleton class="size-3.5" />
						<div class="flex flex-1 flex-col gap-1.5">
							<Skeleton class="h-3.5 w-1/3" />
							<Skeleton class="h-3 w-1/4" />
						</div>
						<Skeleton class="hidden h-6 w-24 sm:block" />
						<Skeleton class="h-4 w-10" />
						<Skeleton class="h-7 w-20" />
					</div>
				{/each}
			</div>
		{:else if entries.length === 0}
			<EmptyState icon={Sparkles} title={emptyTitle} description={emptyDescription} />
		{:else}
			<div class="flex flex-col pb-2 transition-opacity {loading ? 'opacity-60' : ''}">
				{#each days as day (day.key)}
					<h2
						class="sticky top-0 z-10 border-b bg-card/95 px-4 py-2 text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase backdrop-blur"
					>
						{day.label}
					</h2>
					<ol>
						{#each day.rows as { entry, index } (entry.id)}
							{#if index === markIndex}
								<li
									class="grid grid-cols-[3rem_1rem_minmax(0,1fr)] items-center gap-x-3 px-4 py-1.5"
								>
									<span></span>
									<span class="flex justify-center"
										><span class="h-4 border-l border-dashed border-muted-foreground/60"
										></span></span
									>
									<span class="flex items-center gap-2 text-2xs text-muted-foreground">
										<span class="h-px flex-1 border-t border-dashed border-muted-foreground/40"
										></span>
										Caught up {markLabel}
										<span class="h-px flex-1 border-t border-dashed border-muted-foreground/40"
										></span>
									</span>
								</li>
							{/if}
							<EventRow
								group={entry.group}
								{index}
								cursor={cursor === index}
								unseen={markedAt === null || new Date(entry.group.at).getTime() > markedAt}
								expanded={expanded.has(entry.id)}
								isChecked={(id) => selection.has(id)}
								isBusy={(id) => busy.has(id)}
								addingAll={addingAll === entry.id}
								onToggle={() => toggle(entry.id)}
								onPick={(i) => (cursor = i)}
								onCompare={(current, baseline) => (runCompare = { current, baseline })}
								onAddTargets={(items) => addAll(entry.id, items)}
								onOpen={(item) => openRow(item)}
								onCheck={check}
								onAddTarget={(item) => addTargets([item])}
								onWatch={(item) => (watchFor = item)}
								onMute={(item) => muteHosts([item])}
								onScan={scan}
								onRemoveTarget={(item) => (removeFor = item)}
							/>
						{/each}
					</ol>
				{/each}
				{#if feed.truncated}
					<p class="px-4 py-3 text-xs text-muted-foreground">
						Newest {feed.groups.length} events shown.
					</p>
				{/if}
			</div>
		{/if}
	</Card.Root>
</div>

<SelectionActionBar selectedCount={selection.size} noun="row" onClear={() => selection.clear()}>
	{#if pickedAddable.length}
		<Button size="sm" class="h-7 text-xs" onclick={() => addTargets(pickedAddable)}>
			Add {pickedAddable.length === 1 ? 'target' : `${pickedAddable.length} targets`}
		</Button>
	{/if}
	{#if pickedHosts.length}
		<Button variant="ghost" size="sm" class="h-7 text-xs" onclick={() => muteHosts(pickedHosts)}>
			{pickedHosts.every((h) => h.muted) ? 'Unmute' : 'Mute'}
			{pickedHosts.length === 1 ? 'host' : `${pickedHosts.length} hosts`}
		</Button>
	{/if}
</SelectionActionBar>

<Dialog.Root bind:open={shortcutsOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header><Dialog.Title>Keyboard shortcuts</Dialog.Title></Dialog.Header>
		<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
			{#each tab === NewTab.VISUAL ? VISUAL_KEYS : NEW_KEYS as [k, label] (k)}
				<dt><Kbd>{k}</Kbd></dt>
				<dd class="text-muted-foreground">{label}</dd>
			{/each}
		</dl>
	</Dialog.Content>
</Dialog.Root>

{#if watchFor && projectId}
	{@const watched = watchProgram()}
	{#if watched}
		<WatchDialog
			program={watched}
			{projectId}
			open={true}
			onOpenChange={(v) => {
				if (!v) watchFor = null;
			}}
			onSaved={(watch) => {
				watchesStore.upsert(watch);
				watchFor = null;
				toast.success('Watch started');
				void load(true);
			}}
		/>
	{/if}
{/if}

{#if launchFor}
	<LaunchDialog
		open={true}
		targetId={launchFor}
		onClose={() => {
			launchFor = null;
			void load(true);
		}}
	/>
{/if}

<CompareSheet
	{projectId}
	current={runCompare?.current ?? null}
	baseline={runCompare?.baseline ?? null}
	onClose={() => (runCompare = null)}
/>

<VisualCompareDialog
	pairs={visualPairs}
	index={compareIndex}
	open={compareOpen}
	onOpenChange={(v) => (compareOpen = v)}
	onStep={stepCompare}
	onOpenHost={(pair) => {
		compareOpen = false;
		void openPair(pair);
	}}
/>

{#if projectId}
	<WebAssetDetailSheet
		sub={sheetSub}
		open={sheetOpen && sheetSub !== null}
		onOpenChange={closeSheet}
		{projectId}
		scanId={sheetScan}
		onFilter={(dsl) => scanTab(SurfaceDimension.WEB_ASSETS, dsl)}
	/>
{/if}

<ConfirmDialog
	open={removeFor !== null}
	title="Remove {removeFor?.target_value ?? removeFor?.value ?? 'target'}"
	description="Target {removeFor?.target_value ?? ''} and its scans are removed."
	confirmLabel="Remove"
	loadingLabel="Removing"
	destructive
	loading={removing}
	onOpenChange={(v) => {
		if (!v) removeFor = null;
	}}
	onConfirm={removeTarget}
/>
