<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Globe from '@lucide/svelte/icons/globe';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	import * as Card from '$lib/components/ui/card';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';

	import QueryBar from './query-bar/query-bar.svelte';
	import FilterBar from './web-assets/filter-bar.svelte';
	import ListHeader from './table/list-header.svelte';
	import { withTarget } from './table/columns';
	import AssetRow from './web-assets/asset-row.svelte';
	import AssetGallery from './web-assets/asset-gallery.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import SelectionBar from './table/selection-bar.svelte';
	import { RowSelection } from './table/selection.svelte';
	import GroupList from './table/group-list.svelte';
	import WebAssetDetailSheet from './web-asset-detail-sheet.svelte';
	import HostStructureDialog from './web-assets/host-structure-dialog.svelte';
	import {
		WEB_ASSET_COLUMNS,
		WEB_ASSET_LEAD_COLUMNS,
		DEFAULT_VISIBLE_COLUMNS
	} from './web-assets/columns';

	import { subdomainsApi } from '$lib/api/subdomains';
	import { servicesOn } from '$lib/utilities/service-lookup';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { runDescription, runStarted, seedKindFor, selectionLabel } from '$lib/utilities/rechecks';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import { querySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import type { SeedPick, SeedSelection } from '$lib/types/recheck';
	import {
		appendToken,
		exactToken,
		activeFacetCount,
		emptyQuery,
		compileQuery,
		queryChips,
		STATUS_CLASS_TABS,
		WEB_ASSET_SORTS,
		type Facet,
		type WebAssetQuery,
		type SubdomainFacetSet
	} from '$lib/utilities/scan-insights';
	import type { QueryError, QueryGroups, QueryLeads } from '$lib/types/asset-query';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LiveRefresh } from '$lib/utilities/live-results';

	interface Props {
		scanId: string;
		projectWide?: boolean;
		targetType?: string;
		projectId: string;
		apex?: string;
		active?: boolean;
		revision?: number;
		query?: WebAssetQuery;
		onTab?: (tab: string, filter?: string) => void;
	}

	let {
		scanId,
		projectWide = false,
		targetType = '',
		projectId,
		apex = '',
		active = true,
		revision = 0,
		query = $bindable(emptyQuery()),
		onTab
	}: Props = $props();

	let ready = $derived(Boolean(projectId) && (projectWide || Boolean(scanId)));

	const DEFAULT_SORT = { key: 'status', dir: 1 as const };
	const EMPTY_FACETS: SubdomainFacetSet = {
		status: [],
		tech: [],
		service: [],
		source: [],
		cert: [],
		hygiene: []
	};
	const ROW_PAD: Record<string, string> = { compact: 'py-2', cozy: 'py-3' };

	function readPref<T>(key: string, fallback: T): T {
		try {
			const raw = localStorage.getItem(key);
			return raw ? (JSON.parse(raw) as T) : fallback;
		} catch {
			return fallback;
		}
	}
	function writePref(key: string, value: unknown) {
		try {
			localStorage.setItem(key, JSON.stringify(value));
		} catch {
			// ignore
		}
	}

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('sort')?.split(':') ?? [];
	let pendingAsset = initial.get('asset');

	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.webAssetsColumns, null));
	let view = $state<string>(initial.get('view') === 'gallery' ? 'gallery' : 'table');
	let density = $state<string>(readPref(STORAGE_KEYS.webAssetsDensity, 'cozy'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.webAssetsPageSize, RESULTS_PAGE_SIZE));
	let onlyShots = $state(true);
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('page') ?? 1) - 1));

	let items = $state<SubdomainRead[]>([]);
	let total = $state(0);
	let totalCapped = $state(false);
	let queryError = $state<QueryError | null>(null);
	let queryReady = $state(true);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let facets = $state<SubdomainFacetSet>(EMPTY_FACETS);
	let facetsLoaded = $state(false);
	let leadSet = $state<QueryLeads | null>(null);
	let groupBy = $state<string>(initial.get('group') ?? '');
	let groupSet = $state<QueryGroups | null>(null);
	let groupLoading = $state(false);
	let groupReq = 0;

	let selected = $state<SubdomainRead | null>(null);
	let drawerOpen = $state(false);
	let sheetFocus = $state<{ tab: string; pane?: string } | null>(null);
	let structureHost = $state<string | null>(null);
	let structureScanId = $state('');
	let cursor = $state(-1);
	let searchRef = $state<HTMLInputElement | null>(null);
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let pendingSelect: 'first' | 'last' | null = null;
	const selection = new RowSelection<SubdomainRead>();

	let scanTotal = $derived(facets.status.reduce((n, f) => n + f.count, 0));
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let selectedIndex = $derived(selected ? items.findIndex((s) => s.id === selected?.id) : -1);
	let visible = $derived(
		visiblePref ??
			(facets.service.length
				? DEFAULT_VISIBLE_COLUMNS
				: DEFAULT_VISIBLE_COLUMNS.filter((k) => k !== 'ports'))
	);
	let allColumns = $derived(withTarget(WEB_ASSET_COLUMNS, projectWide));
	let shownColumns = $derived(
		allColumns.filter((c) => visible.includes(c.key) || c.key === 'target')
	);
	let checkedCount = $derived(selection.countOn(items));
	let pickedCount = $derived(selection.size);
	let selectAllChecked = $derived<boolean | 'indeterminate'>(
		items.length > 0 && checkedCount === items.length
			? true
			: checkedCount > 0
				? 'indeterminate'
				: false
	);
	let filtered = $derived(activeFacetCount(query) > 0 || !!query.search);
	let chips = $derived(queryChips(query));
	let rowPad = $derived(ROW_PAD[density] ?? ROW_PAD.cozy);
	let statusTab = $derived(
		query.status.length === 0 ? 'all' : query.status.length === 1 ? query.status[0] : ''
	);
	let statusCounts = $derived.by(() => {
		if (!facetsLoaded) return null;
		const m: Record<string, number> = { all: scanTotal };
		for (const f of facets.status) m[f.value] = f.count;
		return m;
	});

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.webAssetsColumns, visiblePref);
	});
	$effect(() => writePref(STORAGE_KEYS.webAssetsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.webAssetsPageSize, pageSize));

	const initialSearch = initial.get('q');
	if (initialSearch) query = { ...query, search: initialSearch };

	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;
	let lastSig = '';
	let primed = false;

	function flushSearch() {
		if (timer) clearTimeout(timer);
		timer = null;
		void runSearch();
	}

	async function runSearch() {
		if (!queryReady) {
			syncLeads();
			return;
		}
		const q = view === 'gallery' && onlyShots ? { ...query, hasScreenshot: true } : query;
		const filter = compileQuery(q, sort.key, sort.dir, pageIndex * pageSize, pageSize);
		const sig = JSON.stringify({ ...filter, offset: 0 });
		if (sig !== lastSig && pageIndex !== 0 && !pendingSelect) {
			lastSig = sig;
			pageIndex = 0;
			return;
		}
		lastSig = sig;
		const my = ++reqId;
		loading = true;
		try {
			const res = await subdomainsApi.search(projectId, scanId, filter);
			if (my !== reqId) return;
			items = res.items;
			total = res.total;
			totalCapped = res.total_capped;
			queryError = res.error;
			errored = false;
			if (!res.error && filter.q) queryBar?.remember(filter.q);
			if (pendingSelect) {
				selected = pendingSelect === 'first' ? (items[0] ?? null) : (items.at(-1) ?? null);
				pendingSelect = null;
			} else if (pendingAsset) {
				const name = pendingAsset;
				pendingAsset = null;
				const hit = items.find((s) => s.name === name);
				if (hit) open(hit);
				else openHost(name);
			}
		} catch {
			if (my === reqId) {
				items = [];
				total = 0;
				totalCapped = false;
				errored = true;
			}
		} finally {
			if (my === reqId) {
				loading = false;
				syncLeads();
			}
		}
	}

	let leadFilter = $derived(
		compileQuery(
			view === 'gallery' && onlyShots
				? { ...query, search: '', hasScreenshot: true }
				: { ...query, search: '' },
			'name',
			1,
			0,
			1
		)
	);
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groupBy ? JSON.stringify(leadFilterWithQuery) + groupBy : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await subdomainsApi.leads(projectId, scanId, leadFilter);
			if (leadSig === sig) leadSet = res.computed ? res : null;
		} catch {
			if (leadSig === sig) leadSet = null;
			loadedLeadSig = '';
		}
	}

	function syncLeads() {
		if (!active || loading || !ready) return;
		if (leadSig === loadedLeadSig) return;
		void loadLeads();
	}

	async function loadGroups() {
		if (!groupBy || !ready) {
			groupSet = null;
			return;
		}
		const my = ++groupReq;
		groupLoading = true;
		try {
			const res = await subdomainsApi.groups(projectId, scanId, groupBy, leadFilterWithQuery);
			if (my === groupReq) groupSet = res;
		} catch {
			if (my === groupReq) groupSet = null;
		} finally {
			if (my === groupReq) groupLoading = false;
		}
	}

	async function loadFacets() {
		if (!ready) return;
		try {
			facets = await subdomainsApi.facets(projectId, scanId);
		} catch {
			facets = EMPTY_FACETS;
		} finally {
			facetsLoaded = true;
		}
	}

	async function refresh(quiet = false) {
		refreshing = !quiet;
		try {
			if (!quiet) loadedLeadSig = '';
			await Promise.all([runSearch(), loadFacets(), loadGroups()]);
		} finally {
			if (!quiet) refreshing = false;
		}
	}

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	const liveRefresh = new LiveRefresh(() => refresh(true));
	$effect(() => {
		liveRefresh.notify(revision, active);
	});
	onDestroy(() => liveRefresh.stop());

	$effect(() => {
		void JSON.stringify(query);
		void sort.key;
		void sort.dir;
		void pageIndex;
		void pageSize;
		void view;
		void onlyShots;
		void scanId;
		void projectId;
		void queryReady;
		if (!ready || !seen) return;
		if (timer) clearTimeout(timer);
		timer = setTimeout(runSearch, primed ? SEARCH_DEBOUNCE_MS : 0);
		primed = true;
		return () => {
			if (timer) clearTimeout(timer);
		};
	});

	$effect(() => {
		void scanId;
		void projectId;
		if (!seen) return;
		untrack(loadFacets);
	});

	$effect(() => {
		void active;
		untrack(syncLeads);
	});

	$effect(() => {
		void groupSig;
		if (!groupBy) {
			groupSet = null;
			return;
		}
		const handle = setTimeout(() => untrack(loadGroups), SEARCH_DEBOUNCE_MS);
		return () => clearTimeout(handle);
	});

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams(location.search);
			const set = (k: string, v: string | null) => (v ? sp.set(k, v) : sp.delete(k));
			set('q', query.search || null);
			set('view', view === 'gallery' ? 'gallery' : null);
			set('group', groupBy || null);
			set('page', pageIndex > 0 ? String(pageIndex + 1) : null);
			set(
				'sort',
				sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir
					? `${sort.key}:${sort.dir === 1 ? 'asc' : 'desc'}`
					: null
			);
			set('asset', drawerOpen && selected ? selected.name : null);
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, appPage.state);
		} catch {
			// ignore
		}
	}
	$effect(() => {
		void query.search;
		void view;
		void groupBy;
		void pageIndex;
		void sort.key;
		void sort.dir;
		void drawerOpen;
		void selected?.name;
		if (!active) return;
		untrack(syncUrl);
	});

	const EVIDENCE_TARGET: Record<string, { tab: string; pane?: string }> = {
		body: { tab: 'http', pane: 'response' },
		header: { tab: 'http', pane: 'headers' },
		redirect: { tab: 'http', pane: 'headers' },
		path: { tab: 'http', pane: 'response' }
	};

	function open(s: SubdomainRead) {
		selected = s;
		sheetFocus = null;
		drawerOpen = true;
	}
	function openEvidence(s: SubdomainRead, field: string) {
		selected = s;
		sheetFocus = EVIDENCE_TARGET[field] ?? { tab: 'overview' };
		drawerOpen = true;
	}
	async function openHost(name: string) {
		const hit = items.find((s) => s.name === name);
		if (hit) return open(hit);
		try {
			const res = await subdomainsApi.search(
				projectId,
				scanId,
				compileQuery({ ...emptyQuery(), search: exactToken('host', name) }, 'name', 1, 0, 5)
			);
			const exact = res.items.find((s) => s.name === name);
			if (exact) open(exact);
			else toast.error('Web asset not found in this scan');
		} catch {
			toast.error('Web asset not loaded');
		}
	}
	function step(dir: -1 | 1) {
		const next = selectedIndex + dir;
		if (next >= 0 && next < items.length) {
			selected = items[next];
			return;
		}
		if (dir === 1 && pageIndex < pageCount - 1) {
			pendingSelect = 'first';
			pageIndex += 1;
		} else if (dir === -1 && pageIndex > 0) {
			pendingSelect = 'last';
			pageIndex -= 1;
		}
	}
	function toggleSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: 1 };
		pageIndex = 0;
	}
	function pickOf(s: SubdomainRead): SeedPick {
		return { value: s.name, scan_id: s.scan_id };
	}
	function toggleCheck(id: string) {
		const row = items.find((s) => s.id === id);
		if (row) selection.toggle(row, pickOf(row));
	}
	function toggleSelectAll() {
		selection.toggleAll(items, pickOf);
	}
	function toggleCol(key: string) {
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: WebAssetQuery) {
		query = q;
		pageIndex = 0;
	}
	function setStatusTab(key: string) {
		setQuery({ ...query, status: key === 'all' ? [] : [key] });
	}
	function statusCountClass(key: string, n: number): string {
		if (n === 0) return 'text-muted-foreground/50';
		if (key === '5xx') return 'text-destructive';
		return 'text-muted-foreground';
	}
	function drillGroup(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		groupBy = '';
	}
	function applyDsl(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		drawerOpen = false;
	}
	function showServices(host: string, port: number) {
		drawerOpen = false;
		syncUrl();
		onTab?.('services', `${exactToken('host', host)} port:${port}`);
	}
	function showVulns(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.('vulnerabilities', filter);
	}
	function hostsWithTitle(title: string): Promise<string[]> {
		return subdomainsApi
			.search(
				projectId,
				scanId,
				compileQuery({ ...emptyQuery(), search: exactToken('title', title) }, 'name', 1, 0, 50)
			)
			.then((r) => r.items.map((i) => i.name));
	}
	let rescanBusy = $state(false);

	$effect(() => {
		if (!active || !projectId) return;
		void rechecks.loadSchema();
		if (projectWide || !scanId) return;
		untrack(() => rechecks.load(scanId, projectId));
	});

	function selectionOf(picks: SeedPick[]): SeedSelection {
		return { dimension: SurfaceDimension.WEB_ASSETS, picks };
	}

	function queryLabel(): string {
		return selectionLabel(
			query.search,
			chips.map((c) => c.label)
		);
	}

	function querySelection(): SeedSelection {
		const {
			limit: _l,
			offset: _o,
			sort: _s,
			order: _d,
			...filter
		} = compileQuery(query, 'name', 1, 0, 1);
		return {
			dimension: SurfaceDimension.WEB_ASSETS,
			query: { filter, scan_ids: scanId ? [scanId] : [] }
		};
	}

	async function rescan(sel: SeedSelection) {
		if (rescanBusy) return;
		rescanBusy = true;
		try {
			const run = await rechecks.rescan(projectId, { selection: sel, dimension: '' });
			selection.clear();
			toast.success(runStarted(run, 'web asset', 'web assets'), {
				description: runDescription(run)
			});
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Rescan not started');
		} finally {
			rescanBusy = false;
		}
	}

	function rescanSelection() {
		const picks = selection.picks();
		if (picks.length) return void rescan(selectionOf(picks));
		const row = cursor >= 0 ? items[cursor] : null;
		if (row) void rescan(selectionOf([pickOf(row)]));
	}

	function rescanAllMatching() {
		void rescan(querySelection());
	}

	function scrollCursor() {
		document.querySelector(`[data-row-index="${cursor}"]`)?.scrollIntoView({ block: 'nearest' });
	}
	function onKey(e: KeyboardEvent) {
		if (!active || e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		const typing =
			!!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
		if (e.key === '/' && !typing) {
			e.preventDefault();
			searchRef?.focus();
			return;
		}
		if (typing || drawerOpen || view !== 'table' || !items.length) return;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			cursor = Math.min(cursor + 1, items.length - 1);
			scrollCursor();
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			cursor = Math.max(cursor - 1, 0);
			scrollCursor();
		} else if (e.key === 'Enter' && cursor >= 0 && items[cursor]) {
			open(items[cursor]);
		} else if (e.key === 'r') {
			e.preventDefault();
			rescanSelection();
		} else if (e.key === 'Escape') {
			cursor = -1;
		}
	}

	let rescanOptionsFor = $state<SeedSelection | null>(null);

	function openRescanOptions() {
		const picks = selection.picks();
		if (picks.length) rescanOptionsFor = selectionOf(picks);
	}

	function openRescanAllOptions() {
		rescanOptionsFor = querySelection();
	}
</script>

<svelte:window onkeydown={onKey} />

<div class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2">
	<QueryBar
		bind:this={queryBar}
		bind:ref={searchRef}
		store={querySchema}
		recentsKey={STORAGE_KEYS.webAssetsRecentQueries}
		hint="status:>=500 is:live"
		value={query.search}
		facets={facets as unknown as Record<string, Facet[]>}
		busy={loading && !!query.search}
		{leadSet}
		total={errored ? null : total}
		capped={totalCapped}
		serverError={queryError}
		onReady={(value) => (queryReady = value)}
		onChange={(v) => setQuery({ ...query, search: v })}
		onSubmit={flushSearch}
	/>
</div>

<Card.Root class="gap-0 overflow-hidden rounded-t-none border-t-0 py-0">
	<div class="border-b px-2">
		<CountTabs
			tabs={STATUS_CLASS_TABS}
			value={statusTab}
			counts={statusCounts}
			countClass={statusCountClass}
			onChange={setStatusTab}
		/>
	</div>

	<FilterBar
		{query}
		{facets}
		onQuery={setQuery}
		{view}
		onView={(v) => {
			view = v;
			pageIndex = 0;
			if (v === 'gallery') groupBy = '';
		}}
		columns={WEB_ASSET_COLUMNS}
		{visible}
		onToggleColumn={toggleCol}
		{density}
		onDensity={(d) => (density = d)}
		{onlyShots}
		onOnlyShots={(v) => {
			onlyShots = v;
			pageIndex = 0;
		}}
		sorts={WEB_ASSET_SORTS}
		sortKey={sort.key}
		sortDir={sort.dir}
		onSort={toggleSort}
		{refreshing}
		onRefresh={refresh}
		{groupBy}
		onGroupBy={(key) => (groupBy = key)}
	/>

	{#if chips.length > 0}
		<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
			{#each chips as chip (chip.id)}
				<Badge variant="outline" class="gap-1 bg-background font-normal">
					{chip.label}
					<Tooltip.Root>
						<Tooltip.Trigger
							class="rounded-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							onclick={() => setQuery(chip.remove(query))}
							aria-label="Remove filter {chip.label}"
						>
							<X class="h-3 w-3" />
							<span class="sr-only">Remove filter {chip.label}</span>
						</Tooltip.Trigger>
						<Tooltip.Content>Remove filter {chip.label}</Tooltip.Content>
					</Tooltip.Root>
				</Badge>
			{/each}
			<button
				class="ml-1 rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				onclick={() => setQuery({ ...emptyQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if !groupBy}
		<SelectionBar
			count={pickedCount}
			noun="web asset"
			nounPlural="web assets"
			{total}
			{totalCapped}
			maxAssets={rechecks.schema?.max_assets ?? 0}
			queryActive={Boolean(query.search.trim()) || chips.length > 0}
			busy={rescanBusy}
			onRescan={rescanSelection}
			onOptions={openRescanOptions}
			onRescanAll={rescanAllMatching}
			onRescanAllOptions={openRescanAllOptions}
			onClear={() => selection.clear()}
		/>
	{/if}

	{#if loading && items.length === 0 && !groupBy}
		<div class="divide-y divide-border/50">
			{#each Array(8) as _, i (i)}
				<div class="flex items-center gap-3 px-4 py-3">
					<Skeleton class="h-9 flex-1" />
					<Skeleton class="h-5 w-12" />
					<Skeleton class="hidden h-6 w-56 sm:block" />
					<Skeleton class="hidden h-5 w-36 sm:block" />
				</div>
			{/each}
		</div>
	{:else if errored}
		<EmptyState
			icon={TriangleAlert}
			title="Web assets not loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" class="gap-2" onclick={() => refresh()}>
				<RefreshCw class="h-4 w-4" /> Retry
			</Button>
		</EmptyState>
	{:else if groupBy}
		<GroupList
			set={groupSet}
			dimensions={querySchema.schema.group_dimensions}
			noun={querySchema.schema.noun}
			nounPlural={querySchema.schema.noun_plural}
			loading={groupLoading}
			onPick={drillGroup}
		/>
	{:else if items.length === 0}
		{#if queryError}
			<EmptyState
				icon={SearchX}
				title="Query did not run"
				description={queryError.message}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if filtered || (view === 'gallery' && onlyShots)}
			<EmptyState
				icon={SearchX}
				title="No web assets match"
				description="Widen the search or remove a filter."
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button size="sm" variant="outline" class="gap-2" onclick={() => setQuery(emptyQuery())}>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			</EmptyState>
		{:else}
			<EmptyState
				icon={Globe}
				title="No web assets in this scan"
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{/if}
	{:else if view === 'gallery'}
		<AssetGallery
			{items}
			{loading}
			selectedId={drawerOpen ? (selected?.id ?? null) : null}
			onOpen={open}
		/>
	{:else}
		<ScrollArea orientation="horizontal">
			<ListHeader
				lead={WEB_ASSET_LEAD_COLUMNS}
				columns={shownColumns}
				{selectAllChecked}
				selectAllLabel="Select all web assets on this page"
				onSelectAll={toggleSelectAll}
				sortKey={sort.key}
				sortDir={sort.dir}
				onSort={toggleSort}
			/>
			<div class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}">
				{#each items as s, i (s.id)}
					<AssetRow
						sub={s}
						index={i}
						{apex}
						columns={shownColumns}
						checked={selection.has(s.id)}
						onCheck={toggleCheck}
						selected={drawerOpen && selected?.id === s.id}
						focused={cursor === i}
						pad={rowPad}
						onOpen={open}
						onHost={openHost}
						onFilter={applyDsl}
						onEvidence={openEvidence}
						{hostsWithTitle}
						loadServices={(host) => servicesOn(projectId, scanId, 'host', host)}
						onServices={onTab ? showServices : undefined}
						onVulns={onTab ? showVulns : undefined}
						onStructure={(sub) => {
							structureScanId = sub.scan_id;
							structureHost = sub.name;
						}}
						recheck={rechecks.latest(scanId, s.name)}
						onRescan={(sub) => rescan(selectionOf([pickOf(sub)]))}
						onRescanOptions={(sub) => (rescanOptionsFor = selectionOf([pickOf(sub)]))}
					/>
				{/each}
			</div>
		</ScrollArea>
	{/if}

	{#if !errored && total > 0 && !groupBy}
		<ResultsPagination
			{total}
			capped={totalCapped}
			page={pageIndex}
			{pageSize}
			selectedCount={pickedCount}
			onClearSelection={() => selection.clear()}
			onPage={(p) => (pageIndex = p)}
			onPageSize={(s) => {
				pageSize = s;
				pageIndex = 0;
			}}
		/>
	{/if}
</Card.Root>

<WebAssetDetailSheet
	sub={selected}
	open={drawerOpen}
	focus={sheetFocus}
	onOpenChange={(o) => (drawerOpen = o)}
	{projectId}
	scanId={selected?.scan_id || scanId}
	index={selectedIndex}
	pageOffset={pageIndex * pageSize}
	{total}
	onStep={step}
	onFilter={applyDsl}
	onPivot={openHost}
	onOpenEndpoints={onTab ? (h) => onTab('endpoints', exactToken('host', h)) : undefined}
/>

<HostStructureDialog
	host={structureHost}
	open={structureHost !== null}
	onOpenChange={(o) => {
		if (!o) structureHost = null;
	}}
	{projectId}
	scanId={structureScanId || scanId}
	onOpenEndpoints={onTab ? (h) => onTab('endpoints', exactToken('host', h)) : undefined}
/>

<LaunchDialog
	open={rescanOptionsFor !== null}
	rescan={rescanOptionsFor
		? {
				selection: rescanOptionsFor,
				dimension: SurfaceDimension.WEB_ASSETS,
				targetType,
				seedKind: seedKindFor(rechecks.schema, SurfaceDimension.WEB_ASSETS),
				assets: rescanOptionsFor.picks?.map((pick) => pick.value) ?? [],
				queryLabel: rescanOptionsFor.query ? queryLabel() : undefined
			}
		: null}
	onClose={() => {
		rescanOptionsFor = null;
		selection.clear();
	}}
/>
