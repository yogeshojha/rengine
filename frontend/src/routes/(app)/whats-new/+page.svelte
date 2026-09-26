<script lang="ts">
	import { errorMessage } from '$lib/utilities/errors';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteMap, SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import Check from '@lucide/svelte/icons/check';
	import Search from '@lucide/svelte/icons/search';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as Kbd from '$lib/components/ui/kbd';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SelectionActionBar from '$lib/components/selection-action-bar.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import WatchDialog from '$lib/components/bounty-hub/watch-dialog.svelte';
	import { RowSelection } from '$lib/components/scans/results/table/selection.svelte';
	import KindStrip from '$lib/components/whats-new/kind-strip.svelte';
	import VisualPairs from '$lib/components/whats-new/visual-pairs.svelte';
	import VisualCompareDialog from '$lib/components/whats-new/visual-compare-dialog.svelte';
	import DistanceFilter from '$lib/components/whats-new/distance-filter.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import ActivityGrid from '$lib/components/whats-new/activity-grid.svelte';
	import GroupCard from '$lib/components/whats-new/group-card.svelte';
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
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { goto } from '$app/navigation';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { secretsApi, servicesApi } from '$lib/api/scan-results';
	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import WebAssetDetailSheet from '$lib/components/scans/results/web-asset-detail-sheet.svelte';
	import VulnerabilityDetailSheet from '$lib/components/scans/results/vulnerability-detail-sheet.svelte';
	import ServiceDetailSheet from '$lib/components/scans/results/service-detail-sheet.svelte';
	import SecretDetailSheet from '$lib/components/scans/results/secrets/secret-detail-sheet.svelte';
	import { compileQuery, emptyQuery, exactToken } from '$lib/utilities/scan-insights';
	import { SURFACE } from '$lib/config/surface';
	import { ROUTES } from '$lib/config/routes';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import {
		compileServiceQuery,
		emptyServiceQuery,
		type ServiceRead
	} from '$lib/utilities/services';
	import type { SecretDetail } from '$lib/types/secret';
	import { Capability } from '$lib/config/capabilities';
	import { routeLabels } from '$lib/config/routes';
	import { SurfaceDimension } from '$lib/config/surface';
	import {
		BOUNTY_KINDS,
		GONE_KINDS,
		KIND_ORDER,
		NEW_KEYS,
		NEW_WINDOWS,
		NEW_TABS,
		VISUAL_KEYS,
		NewBasis,
		NewKind,
		NewSource,
		NewTab,
		ProgramRing,
		SOURCE_KINDS,
		SOURCE_OPTIONS,
		RING_LABELS,
		ROWS_SHOWN,
		SELECTABLE_KINDS,
		SINCE_KEY,
		SubjectKind,
		type NewKindKey,
		type NewSourceKey,
		type NewTabKey,
		type NewWindowKey
	} from '$lib/config/whats-new';
	import { runDescription, runStarted } from '$lib/utilities/rechecks';
	import { formatShortDate } from '$lib/utilities/dates';
	import { rowHref } from '$lib/utilities/whats-new';
	import type { NewFeed, NewItem, VisualFeed, VisualPair } from '$lib/types/whats-new';
	import type { SeedPick } from '$lib/types/recheck';

	const WINDOW_KEYS = new Set<string>(NEW_WINDOWS.map((w) => w.key));
	const KIND_KEYS = new Set<string>(KIND_ORDER);
	const SOURCE_KEYS = new Set<string>(SOURCE_OPTIONS.map((o) => o.key));
	const DAY_RE = /^\d{4}-\d{2}-\d{2}$/;
	const RING_LIBRARY = `ring:${ProgramRing.LIBRARY}`;
	const Q_DEBOUNCE_MS = 250;
	const GRID_LEVELS = [0, 0.3, 0.55, 0.8, 1];

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
	const kinds = new SvelteSet<string>(
		(initial.get('kinds') ?? '').split(',').filter((k) => KIND_KEYS.has(k))
	);
	let source = $state<NewSourceKey>(
		SOURCE_KEYS.has(initial.get('source') ?? '')
			? (initial.get('source') as NewSourceKey)
			: NewSource.ALL
	);
	let q = $state(initial.get('q') ?? '');
	let qApplied = $state(initial.get('q') ?? '');

	const TAB_KEYS = new Set<string>(NEW_TABS.map((t) => t.key));
	let tab = $state<NewTabKey>(
		TAB_KEYS.has(initial.get('tab') ?? '') ? (initial.get('tab') as NewTabKey) : NewTab.NEW
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

	let watchFor = $state<NewItem | null>(null);
	let launchFor = $state<string | null>(null);
	let removeFor = $state<NewItem | null>(null);
	let removing = $state(false);
	let addingAll = $state<string | null>(null);
	let lastChecked = $state(-1);
	let sheetSub = $state<SubdomainRead | null>(null);
	let sheetVuln = $state<VulnerabilityRead | null>(null);
	let sheetService = $state<ServiceRead | null>(null);
	let sheetSecret = $state<SecretDetail | null>(null);
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
	let pickedKinds = $derived(visibleKinds.filter((k) => kinds.has(k)));
	let wantedKinds = $derived<string[] | null>(
		pickedKinds.length ? pickedKinds : sourceOn === NewSource.ALL ? null : visibleKinds
	);
	let keys = $derived(NEW_KEYS.filter((k) => bounty || !k.bounty));
	let gridKinds = $derived<NewKindKey[]>(
		pickedKinds.length ? pickedKinds : visibleKinds.filter((k) => !GONE_KINDS.has(k))
	);

	const splitProgram = (v: string): [string, string] => {
		const i = v.indexOf(':');
		return i < 0 ? ['', ''] : [v.slice(0, i), v.slice(i + 1)];
	};

	let total = $derived(
		feed
			? visibleKinds.reduce((n, k) => (GONE_KINDS.has(k) ? n : n + (feed?.counts[k] ?? 0)), 0)
			: 0
	);
	let gone = $derived(
		feed
			? visibleKinds.reduce((n, k) => (GONE_KINDS.has(k) ? n + (feed?.counts[k] ?? 0) : n), 0)
			: 0
	);

	const stamp = (iso: string) => {
		const at = new Date(iso);
		return `${formatShortDate(at)}, ${at.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
	};
	const dayLabel = (d: string) =>
		new Date(`${d}T12:00:00Z`).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		});
	let periodLabel = $derived.by(() => {
		if (!feed) return '';
		if (feed.basis === NewBasis.DAYS && dayFrom) {
			return dayTo && dayTo !== dayFrom
				? `${dayLabel(dayFrom)} to ${dayLabel(dayTo)}`
				: dayLabel(dayFrom);
		}
		if (feed.basis === NewBasis.MARK) return `since caught up ${stamp(feed.since)}`;
		const w = NEW_WINDOWS.find((x) => x.key === feed?.window);
		return w
			? `in the last ${w.key === '24h' ? '24 hours' : w.key === '7d' ? '7 days' : '30 days'}`
			: '';
	});
	let headline = $derived.by(() => {
		if (!feed) return '';
		const what = total === 1 ? '1 new' : `${total.toLocaleString()} new`;
		const tail = gone ? ` · ${gone.toLocaleString()} gone` : '';
		return `${what} ${periodLabel}${tail}${fromNewChecks}${firstRuns}`;
	});
	let fromNewChecks = $derived.by(() => {
		const n = feed?.new_checks ?? 0;
		if (!n) return '';
		return n === 1
			? ' · 1 finding from new checks'
			: ` · ${n.toLocaleString()} findings from new checks`;
	});
	let firstRuns = $derived.by(() => {
		const n = feed?.first_runs ?? 0;
		if (!n) return '';
		return n === 1 ? ' · 1 first scan set a baseline' : ` · ${n} first scans set a baseline`;
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
		!!(targetId || program || qApplied || pickedKinds.length || sourceOn !== NewSource.ALL)
	);

	// ---------- rows in reading order ----------

	let rows = $derived.by<NewItem[]>(() => {
		const out: NewItem[] = [];
		for (const g of feed?.groups ?? []) {
			for (const s of g.sections) {
				const key = `${g.id}:${s.kind}`;
				const shown = expanded.has(key) ? s.items : s.items.slice(0, ROWS_SHOWN);
				out.push(...shown);
			}
		}
		return out;
	});
	let rowIndexOf = $derived(new Map(rows.map((r, i) => [r.id, i])));
	let cursorId = $derived(rows[cursor]?.id ?? null);

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

	// ---------- loading ----------

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams();
			if (tab !== NewTab.NEW) sp.set('tab', tab);
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
			if (pickedKinds.length) sp.set('kinds', pickedKinds.join(','));
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
			if (cursor >= rows.length) cursor = rows.length - 1;
		} catch (e) {
			if (my !== reqId) return;
			error = errorMessage(e, 'Feed not loaded');
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
			toast.error(errorMessage(e, 'Visual changes not loaded'));
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
		void kinds.size;
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
	function toggleKind(kind: NewKindKey) {
		if (kinds.has(kind)) kinds.delete(kind);
		else kinds.add(kind);
	}
	function setSource(next: NewSourceKey) {
		source = next;
		for (const k of [...kinds]) if (!SOURCE_KINDS[next].has(k)) kinds.delete(k);
	}
	function clearFilters() {
		source = NewSource.ALL;
		targetId = '';
		program = '';
		q = '';
		qApplied = '';
		kinds.clear();
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
			await load();
		} catch (e) {
			toast.error(errorMessage(e, 'Not marked'));
		} finally {
			catchingUp = false;
		}
	}

	function patch(id: string, fn: (item: NewItem) => void) {
		for (const g of feed?.groups ?? []) {
			for (const s of g.sections) {
				const item = s.items.find((i) => i.id === id);
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
			toast.error(errorMessage(e, 'Target not added'));
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
			toast.error(errorMessage(e, 'Host not updated'));
		} finally {
			for (const i of wanted) busy.delete(i.id);
		}
	}

	async function scanAssets(items: NewItem[]) {
		const picks: SeedPick[] = items
			.filter((i) => i.kind === NewKind.WEB_ASSET && i.scan_id)
			.map((i) => ({ value: i.value, scan_id: i.scan_id ?? undefined }));
		if (!picks.length || !projectId) return;
		for (const i of items) busy.add(i.id);
		try {
			const run = await rechecks.rescan(projectId, {
				selection: { dimension: SurfaceDimension.WEB_ASSETS, picks },
				dimension: ''
			});
			toast.success(runStarted(run, 'web asset', 'web assets'), {
				description: runDescription(run)
			});
			selection.clear();
		} catch (e) {
			toast.error(errorMessage(e, 'Rescan not started'));
		} finally {
			for (const i of items) busy.delete(i.id);
		}
	}

	function scan(item: NewItem) {
		if (item.kind === NewKind.WEB_ASSET) return void scanAssets([item]);
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
			toast.error(errorMessage(e, 'Target not removed'));
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

	// ---------- sheets ----------

	function closeSheet(open: boolean) {
		sheetOpen = open;
		if (!open) {
			sheetSub = null;
			sheetVuln = null;
			sheetService = null;
			sheetSecret = null;
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
		const rowId = item.id.slice(item.id.indexOf(':') + 1);
		try {
			sheetScan = scanId;
			if (item.kind === NewKind.WEB_ASSET || item.kind === NewKind.CERT_HOST) {
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
			} else if (item.kind === NewKind.FINDING) {
				sheetVuln = await vulnerabilitiesApi.detail(projectId, scanId, rowId);
			} else if (item.kind === NewKind.SERVICE) {
				const [ip, port] = item.value.split(/:(?=\d+$)/);
				const res = await servicesApi.search(
					projectId,
					scanId,
					compileServiceQuery(
						{ ...emptyServiceQuery(), search: `ip=${ip} port=${port}` },
						'port',
						1,
						0,
						5
					)
				);
				const hit = res.items.find((r) => r.ip === ip && String(r.port) === port) ?? null;
				if (!hit) {
					toast.error('Service not found in this scan');
					return;
				}
				sheetService = hit;
			} else if (item.kind === NewKind.SECRET) {
				sheetSecret = await secretsApi.detail(projectId, scanId, rowId);
			} else {
				const link = rowHref(item);
				if (link) void goto(link);
				return;
			}
			sheetOpen = true;
		} catch (e) {
			toast.error(errorMessage(e, 'Row not loaded'));
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
			toast.error(errorMessage(e, 'Row not loaded'));
		} finally {
			opening = null;
		}
	}

	// ---------- selection ----------

	function check(item: NewItem, shift: boolean) {
		const index = rowIndexOf.get(item.id) ?? -1;
		if (shift && lastChecked >= 0 && index >= 0 && lastChecked !== index) {
			const [lo, hi] = lastChecked < index ? [lastChecked, index] : [index, lastChecked];
			const on = !selection.has(item.id);
			for (let i = lo; i <= hi; i++) {
				const row = rows[i];
				if (!row || !SELECTABLE_KINDS.has(row.kind)) continue;
				if (selection.has(row.id) !== on) selection.toggle(row);
			}
		} else {
			selection.toggle(item);
		}
		lastChecked = index;
	}

	async function addAll(items: NewItem[]) {
		addingAll = items[0]?.id ?? null;
		try {
			await addTargets(items);
		} finally {
			addingAll = null;
		}
	}

	let picked = $derived(selection.rows());
	let pickedAddable = $derived(
		picked.filter((i) => i.kind === NewKind.SCOPE && i.importable && !i.target_exists)
	);
	let pickedHosts = $derived(picked.filter((i) => i.kind === NewKind.CERT_HOST));
	let pickedAssets = $derived(picked.filter((i) => i.kind === NewKind.WEB_ASSET));

	// ---------- keyboard ----------

	function scrollCursor() {
		document.querySelector(`[data-new-row="${cursor}"]`)?.scrollIntoView({ block: 'nearest' });
	}
	function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (watchFor || launchFor || removeFor || sheetOpen || compareOpen) return;
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
		if (tab === NewTab.VISUAL) {
			if (compareOpen) return;
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
		const row = rows[cursor] ?? null;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			cursor = Math.min(cursor + 1, rows.length - 1);
			scrollCursor();
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			cursor = Math.max(cursor - 1, 0);
			scrollCursor();
		} else if (e.key === 'x' && row) {
			e.preventDefault();
			selection.toggle(row);
		} else if (e.key === 'Enter' && row) {
			e.preventDefault();
			void openRow(row);
		} else if (e.key === 'a' && row) {
			void addTargets([row]);
		} else if (e.key === 's' && row) {
			scan(row);
		} else if (e.key === 'm' && row) {
			void muteHosts([row]);
		} else if (e.key === 'Escape') {
			if (selection.size) selection.clear();
			else cursor = -1;
		}
	}
</script>

<svelte:window onkeydown={onKey} />

<svelte:head><title>{routeLabels['whats-new']} · reNgine</title></svelte:head>

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="flex flex-col gap-0.5">
			<h1 class="text-xl font-semibold">{routeLabels['whats-new']}</h1>
			{#if feed}
				<p class="text-sm text-muted-foreground">
					{headline}
				</p>
			{:else}
				<Skeleton class="h-4 w-48" />
			{/if}
		</div>
		<div class="flex flex-wrap items-center gap-2">
			<ToggleGroup.Root
				type="single"
				value={dayFrom ? '' : range}
				onValueChange={(v) => v && setRange(v as NewWindowKey)}
				variant="outline"
				size="sm"
				aria-label="Period"
			>
				{#each NEW_WINDOWS as option (option.key)}
					<ToggleGroup.Item value={option.key} class="h-8 px-2.5 text-xs font-normal">
						{option.label}
					</ToggleGroup.Item>
				{/each}
			</ToggleGroup.Root>
			<LoadingButton
				size="sm"
				class="h-8"
				loading={catchingUp}
				loadingLabel="Marking"
				onclick={caughtUp}
				disabled={!feed}
			>
				<Check class="size-3.5" />
				Caught up
			</LoadingButton>
		</div>
	</div>

	<CountTabs
		tabs={NEW_TABS}
		value={tab}
		counts={feed ? { [NewTab.NEW]: total, [NewTab.VISUAL]: feed.visual } : null}
		onChange={(k) => (tab = k as NewTabKey)}
	/>

	<div
		class="sticky top-0 z-20 -mx-4 flex flex-wrap items-center gap-2 bg-background/95 px-4 py-2 backdrop-blur"
	>
		<div class="relative">
			<Search
				class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:ref={searchRef}
				bind:value={q}
				placeholder="Filter"
				class="h-8 w-56 pl-8 text-xs"
				aria-label="Filter"
				autocomplete="off"
				spellcheck={false}
			/>
		</div>
		{#if bounty && tab === NewTab.NEW}
			<ToggleGroup.Root
				type="single"
				value={source}
				onValueChange={(v) => v && setSource(v as NewSourceKey)}
				variant="outline"
				size="sm"
				aria-label="Source"
			>
				{#each SOURCE_OPTIONS as option (option.key)}
					<ToggleGroup.Item value={option.key} class="h-8 px-2.5 text-xs font-normal">
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
		{#if tab === NewTab.VISUAL && visual}
			<DistanceFilter
				distances={visualDistances}
				min={minDistance}
				onChange={(v) => (minDistance = v)}
			/>
		{/if}
		{#if tab === NewTab.VISUAL}
			<Button
				variant={silentOnly ? 'secondary' : 'outline'}
				size="sm"
				class="h-8 text-xs font-normal"
				aria-pressed={silentOnly}
				onclick={() => (silentOnly = !silentOnly)}
			>
				Silent redeploys{#if visual?.silent}
					<span class="text-muted-foreground tabular-nums">{visual.silent}</span>{/if}
			</Button>
		{/if}
		{#if bounty && sourceOn !== NewSource.TARGETS && tab === NewTab.NEW}
			<PickPopover
				label={RING_LABELS[ProgramRing.ENGAGED]}
				value={program}
				options={programOptions}
				heading={ringOptions}
				placeholder="Program"
				onChange={(v) => (program = v)}
			/>
		{/if}
		{#if filtered}
			<Button variant="ghost" size="sm" class="h-8 gap-1 text-xs" onclick={clearFilters}>
				<X class="size-3.5" /> Clear
			</Button>
		{/if}
		{#if dayFrom}
			<Button
				variant="secondary"
				size="sm"
				class="h-8 gap-1 text-xs"
				onclick={() => pickDays(null, null)}
			>
				{dayTo && dayTo !== dayFrom
					? `${dayLabel(dayFrom)} to ${dayLabel(dayTo)}`
					: dayLabel(dayFrom)}
				<X class="size-3.5" />
			</Button>
		{/if}
	</div>

	{#if tab === NewTab.VISUAL}
		{#if visual && !visualLoading && visualPairs.length === 0}
			<EmptyState
				icon={Sparkles}
				title={silentOnly
					? `No silent redeploys ${periodLabel}`
					: `No visual changes ${periodLabel}`}
				description="A host counts once both runs captured it and the screenshots differ."
				class="rounded-xl"
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
						Largest {visual.pairs.length} changes shown. Narrow the period or filter to see the rest.
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
	{:else if feed}
		{@const hasTiles = visibleKinds.some((k) => (feed?.counts[k] ?? 0) > 0 || kinds.has(k))}
		<div class="overflow-clip rounded-xl border bg-card">
			<KindStrip
				kinds={visibleKinds}
				counts={feed.counts}
				facts={feed.facts}
				selected={kinds}
				flat
				daily={feed.daily}
				onToggle={toggleKind}
			/>
			{#if feed.daily.length}
				<div
					class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 overflow-x-auto px-4 py-3 {hasTiles
						? 'border-t'
						: ''}"
				>
					<ActivityGrid
						days={feed.daily}
						kinds={gridKinds}
						from={dayFrom}
						to={dayTo}
						onPick={pickDays}
					/>
					<div class="flex items-center gap-3 text-2xs text-muted-foreground">
						<span>Last 13 weeks</span>
						<span class="flex items-center gap-1">
							Less
							{#each GRID_LEVELS as level (level)}
								<span
									class="size-3 rounded-[2px] {level ? '' : 'bg-muted/60'}"
									style={level ? `background: var(--series); opacity: ${level}` : ''}
								></span>
							{/each}
							More
						</span>
					</div>
				</div>
			{/if}
		</div>
	{:else if !error}
		<div class="flex flex-col gap-4">
			<Skeleton class="h-24 rounded-xl" />
			<Skeleton class="h-32 w-full rounded-xl lg:w-[22rem]" />
		</div>
	{/if}

	{#if tab === NewTab.VISUAL}{:else if error}
		<div class="flex flex-col items-center gap-3 rounded-xl border bg-card py-16">
			<p class="text-sm text-muted-foreground">{error}</p>
			<Button size="sm" variant="outline" onclick={() => load()}>Retry</Button>
		</div>
	{:else if feed && feed.groups.length === 0 && !loading}
		<EmptyState
			icon={Sparkles}
			title={emptyTitle}
			description={emptyDescription}
			class="rounded-xl"
		/>
	{:else if feed}
		<div class="flex flex-col gap-3 transition-opacity {loading ? 'opacity-60' : ''}">
			{#each feed.groups as group (group.id)}
				<GroupCard
					{group}
					rowIndex={(item) => rowIndexOf.get(item.id) ?? -1}
					{cursorId}
					isChecked={(id) => selection.has(id)}
					isBusy={(id) => busy.has(id)}
					{expanded}
					onExpand={(key) => expanded.add(key)}
					onCheck={check}
					onOpen={(item) => openRow(item)}
					onAddTargets={addAll}
					addingAll={!!addingAll &&
						group.sections.some((s) => s.items.some((i) => i.id === addingAll))}
					onAddTarget={(item) => addTargets([item])}
					onWatch={(item) => (watchFor = item)}
					onMute={(item) => muteHosts([item])}
					onScan={scan}
					onRemoveTarget={(item) => (removeFor = item)}
					onScanTarget={(id) => (launchFor = id)}
					onPick={(index) => (cursor = index)}
				/>
			{/each}
			{#if feed.truncated}
				<p class="py-2 text-center text-xs text-muted-foreground">
					Newest {feed.groups.length} groups shown. Narrow the period or filter to see the rest.
				</p>
			{/if}
		</div>
	{:else}
		<div class="flex flex-col gap-3">
			{#each { length: 3 } as _, i (i)}
				<Skeleton class="h-36 rounded-xl" />
			{/each}
		</div>
	{/if}

	{#if tab === NewTab.VISUAL}
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-2xs text-muted-foreground">
			{#each VISUAL_KEYS as k (k.key)}
				<span class="inline-flex items-center gap-1.5"><Kbd.Root>{k.key}</Kbd.Root>{k.does}</span>
			{/each}
		</div>
	{/if}
	{#if tab === NewTab.NEW}
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-2xs text-muted-foreground">
			{#each keys as k (k.key)}
				<span class="inline-flex items-center gap-1.5"><Kbd.Root>{k.key}</Kbd.Root>{k.does}</span>
			{/each}
		</div>
	{/if}
</div>

<SelectionActionBar selectedCount={selection.size} noun="row" onClear={() => selection.clear()}>
	{#if pickedAddable.length}
		<Button size="sm" class="h-7 text-xs" onclick={() => addTargets(pickedAddable)}>
			Add {pickedAddable.length === 1 ? 'target' : `${pickedAddable.length} targets`}
		</Button>
	{/if}
	{#if pickedAssets.length}
		<Button variant="ghost" size="sm" class="h-7 text-xs" onclick={() => scanAssets(pickedAssets)}>
			Scan {pickedAssets.length === 1 ? 'web asset' : `${pickedAssets.length} web assets`}
		</Button>
	{/if}
	{#if pickedHosts.length}
		<Button variant="ghost" size="sm" class="h-7 text-xs" onclick={() => muteHosts(pickedHosts)}>
			{pickedHosts.every((h) => h.muted) ? 'Unmute' : 'Mute'}
			{pickedHosts.length === 1 ? 'host' : `${pickedHosts.length} hosts`}
		</Button>
	{/if}
</SelectionActionBar>

{#if watchFor && projectId}
	{@const program = watchProgram()}
	{#if program}
		<WatchDialog
			{program}
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
	<VulnerabilityDetailSheet
		vuln={sheetVuln}
		{projectId}
		scanId={sheetScan}
		open={sheetOpen && sheetVuln !== null}
		onOpenChange={closeSheet}
		onFilter={(dsl) => scanTab(SurfaceDimension.VULNERABILITIES, dsl)}
		onHost={(dsl) => scanTab(SurfaceDimension.WEB_ASSETS, dsl)}
	/>
	<ServiceDetailSheet
		service={sheetService}
		open={sheetOpen && sheetService !== null}
		onOpenChange={closeSheet}
		onFilter={(dsl) => scanTab(SurfaceDimension.SERVICES, dsl)}
		onHosts={(dsl) => scanTab(SurfaceDimension.WEB_ASSETS, dsl)}
		onAddress={(dsl) => scanTab(SurfaceDimension.IPS, dsl)}
	/>
	<SecretDetailSheet
		scanId={sheetScan}
		row={sheetSecret}
		open={sheetOpen && sheetSecret !== null}
		onOpenChange={closeSheet}
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
