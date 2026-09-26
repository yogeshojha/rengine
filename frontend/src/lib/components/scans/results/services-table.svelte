<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Plug from '@lucide/svelte/icons/plug';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Settings2 from '@lucide/svelte/icons/settings-2';

	import * as Card from '$lib/components/ui/card';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';

	import QueryBar from './query-bar/query-bar.svelte';
	import ListHeader from './table/list-header.svelte';
	import { rowPadding, selectAllState, withTarget } from './table/columns';
	import { readPref, writePref } from '$lib/utilities/storage';
	import ResultsPagination from './table/results-pagination.svelte';
	import SelectionBar from './table/selection-bar.svelte';
	import RowSelectionBar from './table/row-selection-bar.svelte';
	import RescanAction from './table/rescan-action.svelte';
	import { hostPort } from '$lib/utilities/net';
	import { RowSelection } from './table/selection.svelte';
	import type { SeedPick, SeedSelection } from '$lib/types/recheck';
	import GroupList from './table/group-list.svelte';
	import { GroupedView, ResultsTable } from './table/results-state.svelte';
	import { pageParam, parsePageIndex, parseSort, sortParam, type SortKey } from './table/sort';
	import FilterBar from './services/filter-bar.svelte';
	import ServiceRow from './services/service-row.svelte';
	import ServiceDetailSheet from './service-detail-sheet.svelte';
	import {
		SERVICE_COLUMNS,
		SERVICE_LEAD_COLUMNS,
		DEFAULT_VISIBLE_SERVICE_COLUMNS
	} from './services/columns';

	import { servicesApi } from '$lib/api/scan-results';
	import { serviceQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { appendToken, type Facet } from '$lib/utilities/scan-insights';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { seedKindFor, selectionLabel } from '$lib/utilities/rechecks';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { startRescan } from '$lib/utilities/rechecks';
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import {
		compileServiceQuery,
		emptyServiceQuery,
		serviceActiveFacetCount,
		serviceQueryChips,
		EMPTY_SERVICE_FACETS,
		SERVICE_CLASS_TABS,
		SERVICE_SORTS,
		type ServiceFacetSet,
		type ServiceQuery,
		type ServiceRead as Service
	} from '$lib/utilities/services';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LiveRefresh } from '$lib/utilities/live-results';

	interface Props {
		scanId: string;
		projectWide?: boolean;
		targetType?: string;
		projectId: string;
		active?: boolean;
		revision?: number;
		onTab?: (tab: ResultTab, filter?: string) => void;
		onScanTotal?: (total: number) => void;
		query?: ServiceQuery;
	}

	let {
		scanId,
		projectWide = false,
		targetType = '',
		projectId,
		active = true,
		revision = 0,
		onTab,
		onScanTotal,
		query = $bindable({
			...emptyServiceQuery(),
			search: appPage.url.searchParams.get('svc_q') ?? ''
		})
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const IP = SURFACE[SurfaceDimension.IPS];

	const SVC = SURFACE[SurfaceDimension.SERVICES];

	let ready = $derived(Boolean(projectId) && (projectWide || Boolean(scanId)));

	const DEFAULT_SORT: SortKey = { key: 'exposure', dir: -1 };

	const initial = appPage.url.searchParams;

	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.servicesColumns, null));
	const table = new ResultsTable<Service, ServiceFacetSet>({
		facets: EMPTY_SERVICE_FACETS,
		sort: parseSort(initial.get('svc_sort'), DEFAULT_SORT),
		pageIndex: parsePageIndex(initial.get('svc_page')),
		pageSizeKey: STORAGE_KEYS.servicesPageSize,
		densityKey: STORAGE_KEYS.servicesDensity
	});
	const groups = new GroupedView(
		initial.get('svc_group') ?? '',
		(by) => servicesApi.groups(projectId, scanId, by, leadFilterWithQuery),
		() => ready
	);

	let selected = $state<Service | null>(null);
	let drawerOpen = $state(false);
	let cursor = $state(-1);
	let searchRef = $state<HTMLInputElement | null>(null);
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let pendingSelect: 'first' | 'last' | null = null;
	const selection = new RowSelection<Service>();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let scanTotal = $derived(table.facets['class'].reduce((n, f) => n + f.count, 0));
	let selectedIndex = $derived(selected ? table.items.findIndex((s) => s.id === selected?.id) : -1);
	let visible = $derived(visiblePref ?? DEFAULT_VISIBLE_SERVICE_COLUMNS);
	let allColumns = $derived(withTarget(SERVICE_COLUMNS, projectWide));
	let shownColumns = $derived(
		allColumns.filter((c) => visible.includes(c.key) || c.key === 'target')
	);
	let checkedCount = $derived(selection.countOn(table.items));
	let pickedCount = $derived(selection.size);
	let selectAllChecked = $derived(selectAllState(checkedCount, table.items.length));
	let filtered = $derived(serviceActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(serviceQueryChips(query, table.facets));
	let rowPad = $derived(rowPadding(table.density));
	let term = $derived(query.search.trim().includes(':') ? '' : query.search.trim());
	let classTab = $derived(
		query.classes.length === 0 ? 'all' : query.classes.length === 1 ? query.classes[0] : ''
	);
	let classCounts = $derived.by(() => {
		if (!table.facetsLoaded) return null;
		const m: Record<string, number> = { all: scanTotal };
		for (const f of table.facets['class']) m[f.value] = f.count;
		return m;
	});

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.servicesColumns, visiblePref);
	});

	let timer: ReturnType<typeof setTimeout> | null = null;
	let lastSig = '';
	let primed = false;

	function flushSearch() {
		if (timer) clearTimeout(timer);
		timer = null;
		void runSearch();
	}

	async function runSearch() {
		if (!table.queryReady) {
			syncLeads();
			return;
		}
		const filter = compileServiceQuery(
			query,
			table.sort.key,
			table.sort.dir,
			table.pageIndex * table.pageSize,
			table.pageSize
		);
		const sig = JSON.stringify({ ...filter, offset: 0 });
		if (sig !== lastSig && table.pageIndex !== 0 && !pendingSelect) {
			lastSig = sig;
			table.pageIndex = 0;
			return;
		}
		lastSig = sig;
		const current = table.searchRequest.begin();
		table.loading = true;
		try {
			const res = await servicesApi.search(projectId, scanId, filter);
			if (!current()) return;
			table.accept(res);
			if (!res.error && filter.q) queryBar?.remember(filter.q);
			if (pendingSelect) {
				selected =
					pendingSelect === 'first' ? (table.items[0] ?? null) : (table.items.at(-1) ?? null);
				pendingSelect = null;
			}
		} catch {
			if (current()) table.fail();
		} finally {
			if (current()) {
				table.loading = false;
				syncLeads();
			}
		}
	}

	let exportFilters = $derived(
		compileServiceQuery(query, table.sort.key, table.sort.dir, 0, 1) as unknown as Record<
			string,
			unknown
		>
	);
	let leadFilter = $derived(compileServiceQuery({ ...query, search: '' }, 'port', 1, 0, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groups.by ? JSON.stringify(leadFilterWithQuery) + groups.by : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await servicesApi.leads(projectId, scanId, leadFilter);
			if (leadSig === sig) table.leadSet = res.computed ? res : null;
		} catch {
			if (leadSig === sig) table.leadSet = null;
			loadedLeadSig = '';
		}
	}

	function syncLeads() {
		if (!active || table.loading || !ready) return;
		if (leadSig === loadedLeadSig) return;
		void loadLeads();
	}

	async function loadFacets() {
		if (!ready) return;
		try {
			table.facets = await servicesApi.facets(projectId, scanId);
			onScanTotal?.(table.facets['class'].reduce((n, f) => n + f.count, 0));
			table.facetsLoaded = true;
		} catch {
			if (!table.facetsLoaded) table.facets = EMPTY_SERVICE_FACETS;
		}
	}

	async function refresh(quiet = false) {
		table.refreshing = !quiet;
		try {
			if (!quiet) loadedLeadSig = '';
			await Promise.all([runSearch(), loadFacets(), groups.reload()]);
		} finally {
			if (!quiet) table.refreshing = false;
		}
	}

	const liveRefresh = new LiveRefresh(() => refresh(true));
	$effect(() => {
		liveRefresh.notify(revision, active);
	});
	onDestroy(() => liveRefresh.stop());

	$effect(() => {
		void JSON.stringify(query);
		void table.sort.key;
		void table.sort.dir;
		void table.pageIndex;
		void table.pageSize;
		void scanId;
		void projectId;
		void table.queryReady;
		if (!seen || !ready) return;
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
		return groups.schedule();
	});

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams(location.search);
			const set = (k: string, v: string | null) => (v ? sp.set(k, v) : sp.delete(k));
			set('svc_q', query.search || null);
			set('svc_group', groups.by || null);
			set('svc_page', pageParam(table.pageIndex));
			set('svc_sort', sortParam(table.sort, DEFAULT_SORT));
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, appPage.state);
		} catch {
			// ignore
		}
	}
	$effect(() => {
		void query.search;
		void groups.by;
		void table.pageIndex;
		void table.sort.key;
		void table.sort.dir;
		if (!seen || !active) return;
		untrack(syncUrl);
	});

	function open(s: Service) {
		selected = s;
		drawerOpen = true;
	}
	function step(dir: -1 | 1) {
		const next = selectedIndex + dir;
		if (next >= 0 && next < table.items.length) {
			selected = table.items[next];
			return;
		}
		if (dir === 1 && table.pageIndex < table.pageCount - 1) {
			pendingSelect = 'first';
			table.pageIndex += 1;
		} else if (dir === -1 && table.pageIndex > 0) {
			pendingSelect = 'last';
			table.pageIndex -= 1;
		}
	}
	function toggleSort(key: string) {
		table.toggleSort(key);
	}
	function toggleCheck(id: string) {
		const row = table.items.find((s) => s.id === id);
		if (row) selection.toggle(row);
	}
	function toggleSelectAll() {
		selection.toggleAll(table.items);
	}
	function toggleCol(key: string) {
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: ServiceQuery) {
		query = q;
		table.pageIndex = 0;
	}
	function setClassTab(key: string) {
		setQuery({ ...query, classes: key === 'all' ? [] : [key] });
	}
	function drillGroup(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		groups.by = '';
	}
	function applyDsl(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		drawerOpen = false;
	}
	function showHosts(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.(WEB.tab, filter);
	}
	function showAddress(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.(IP.tab, filter);
	}
	function scrollCursor() {
		document
			.querySelector(`[data-service-row-index="${cursor}"]`)
			?.scrollIntoView({ block: 'nearest' });
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
		if (typing || drawerOpen || !table.items.length) return;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			cursor = Math.min(cursor + 1, table.items.length - 1);
			scrollCursor();
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			cursor = Math.max(cursor - 1, 0);
			scrollCursor();
		} else if (e.key === 'Enter' && cursor >= 0 && table.items[cursor]) {
			open(table.items[cursor]);
		} else if (e.key === 'Escape') {
			cursor = -1;
		}
	}

	let rescanBusy = $state(false);

	$effect(() => {
		if (!active || !projectId) return;
		void rechecks.loadSchema();
		if (projectWide || !scanId) return;
		untrack(() => rechecks.load(scanId, projectId));
	});

	function pickOf(s: Service): SeedPick {
		return { value: s.ip, scan_id: s.scan_id ?? scanId };
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
		} = compileServiceQuery(query, 'ip', 1, 0, 1);
		return {
			dimension: SurfaceDimension.SERVICES,
			query: { filter, scan_ids: scanId ? [scanId] : [] }
		};
	}

	async function run(sel: SeedSelection) {
		if (rescanBusy) return;
		rescanBusy = true;
		const ok = await startRescan(projectId, sel, 'address', 'addresses');
		if (ok) selection.clear();
		rescanBusy = false;
	}

	async function rescanSelection() {
		const picks = selection.rows().map(pickOf);
		if (picks.length) await run({ dimension: SurfaceDimension.SERVICES, picks });
	}

	async function rescanAllMatching() {
		await run(querySelection());
	}

	let rescanOptionsFor = $state<SeedSelection | null>(null);

	function openRescanOptions() {
		const picks = selection.rows().map(pickOf);
		if (picks.length) rescanOptionsFor = { dimension: SurfaceDimension.SERVICES, picks };
	}

	function openRescanAllOptions() {
		rescanOptionsFor = querySelection();
	}

	let barH = $state(0);
	let scrollRef = $state<HTMLElement | null>(null);
</script>

<svelte:window onkeydown={onKey} />

<div
	class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2"
	bind:clientHeight={barH}
>
	<QueryBar
		bind:this={queryBar}
		bind:ref={searchRef}
		store={serviceQuerySchema}
		recentsKey={SURFACE[SurfaceDimension.SERVICES].recentsKey}
		hint="class:database not is:cdn"
		value={query.search}
		facets={table.facets as unknown as Record<string, Facet[]>}
		busy={table.loading && !!query.search}
		leadSet={table.leadSet}
		total={table.errored ? null : table.total}
		capped={table.totalCapped}
		serverError={table.queryError}
		onReady={(value) => (table.queryReady = value)}
		onChange={(v) => setQuery({ ...query, search: v })}
		onSubmit={flushSearch}
	/>
</div>

<Card.Root class="gap-0 overflow-clip rounded-t-none border-t-0 py-0">
	<div class="border-b px-2">
		<CountTabs
			tabs={SERVICE_CLASS_TABS}
			value={classTab}
			counts={classCounts}
			onChange={setClassTab}
		/>
	</div>

	<FilterBar
		{query}
		facets={table.facets}
		onQuery={setQuery}
		dimensions={serviceQuerySchema.schema.group_dimensions}
		columns={SERVICE_COLUMNS}
		{visible}
		onToggleColumn={toggleCol}
		density={table.density}
		onDensity={(d) => (table.density = d)}
		sorts={SERVICE_SORTS}
		sortKey={table.sort.key}
		sortDir={table.sort.dir}
		onSort={toggleSort}
		refreshing={table.refreshing}
		{projectId}
		{scanId}
		{exportFilters}
		onRefresh={refresh}
		groupBy={groups.by}
		onGroupBy={(key) => (groups.by = key)}
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
				onclick={() => setQuery({ ...emptyServiceQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if !groups.by}
		<SelectionBar
			noun={SVC.noun}
			nounPlural={SVC.nounPlural}
			total={table.total}
			totalCapped={table.totalCapped}
			maxAssets={rechecks.schema?.max_assets ?? 0}
			queryActive={Boolean(query.search.trim()) || chips.length > 0}
			query={queryLabel()}
			busy={rescanBusy}
			onRescanAll={rescanAllMatching}
			onRescanAllOptions={openRescanAllOptions}
		/>
	{/if}

	{#if table.loading && table.items.length === 0 && !groups.by}
		<ScrollArea orientation="horizontal">
			<TableSkeleton
				lead={SERVICE_LEAD_COLUMNS}
				columns={shownColumns}
				density={table.density}
				selectable
			/>
		</ScrollArea>
	{:else if table.errored}
		<EmptyState
			icon={TriangleAlert}
			title="Services not loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" class="gap-2" onclick={() => refresh()}>
				<RefreshCw class="h-4 w-4" /> Retry
			</Button>
		</EmptyState>
	{:else if groups.by}
		<GroupList
			set={groups.value}
			failed={groups.failed}
			onRetry={groups.reload}
			dimensions={serviceQuerySchema.schema.group_dimensions}
			noun={serviceQuerySchema.schema.noun}
			nounPlural={serviceQuerySchema.schema.noun_plural}
			loading={groups.loading}
			onPick={drillGroup}
		/>
	{:else if table.items.length === 0}
		{#if table.queryError}
			<EmptyState
				icon={SearchX}
				title="Query did not run"
				description={table.queryError.message}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if filtered}
			<EmptyState
				icon={SearchX}
				title="No services match"
				description="Widen the search or remove a filter."
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button
					size="sm"
					variant="outline"
					class="gap-2"
					onclick={() => setQuery(emptyServiceQuery())}
				>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			</EmptyState>
		{:else}
			<EmptyState
				icon={Plug}
				title="No services in this scan"
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{/if}
	{:else}
		<ListHeader
			sticky
			top={barH}
			follow={scrollRef}
			lead={SERVICE_LEAD_COLUMNS}
			columns={shownColumns}
			{selectAllChecked}
			selectAllLabel="Select all services on this page"
			onSelectAll={toggleSelectAll}
			sortKey={table.sort.key}
			sortDir={table.sort.dir}
			onSort={toggleSort}
		/>
		<ScrollArea orientation="horizontal" bind:ref={scrollRef}>
			<div class="divide-y divide-border/50 transition-opacity {table.loading ? 'opacity-60' : ''}">
				{#each table.items as s, i (s.id)}
					<ServiceRow
						service={s}
						index={i}
						{term}
						columns={shownColumns}
						checked={selection.has(s.id)}
						onCheck={toggleCheck}
						selected={drawerOpen && selected?.id === s.id}
						focused={cursor === i}
						pad={rowPad}
						onOpen={open}
						onFilter={applyDsl}
						onHosts={showHosts}
						onAddress={showAddress}
						recheck={rechecks.latest(scanId, s.ip)}
					/>
				{/each}
			</div>
		</ScrollArea>
	{/if}

	{#if !table.errored && table.total > 0 && !groups.by}
		<ResultsPagination
			total={table.total}
			capped={table.totalCapped}
			page={table.pageIndex}
			pageSize={table.pageSize}
			noun={SVC.noun}
			plural={SVC.nounPlural}
			onPage={(p) => (table.pageIndex = p)}
			onPageSize={(s) => table.setPageSize(s)}
		/>
	{/if}
</Card.Root>

<RowSelectionBar
	count={pickedCount}
	dimension={SurfaceDimension.SERVICES}
	{projectId}
	{scanId}
	copy={[
		{ label: 'endpoints', values: () => selection.rows().map((s) => hostPort(s.ip, s.port)) },
		{ label: 'addresses', values: () => [...new Set(selection.rows().map((s) => s.ip))] }
	]}
	ids={() => selection.ids()}
	{exportFilters}
	onDeleted={() => {
		selection.clear();
		void refresh();
	}}
	onClear={() => selection.clear()}
>
	{#snippet actions()}
		<RescanAction
			count={pickedCount}
			dimension={SurfaceDimension.SERVICES}
			busy={rescanBusy}
			onRescan={rescanSelection}
		/>
		<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={openRescanOptions}>
			<Settings2 class="h-3.5 w-3.5 text-muted-foreground" />
			Options
		</Button>
	{/snippet}
</RowSelectionBar>

<ServiceDetailSheet
	service={selected}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={selectedIndex}
	pageOffset={table.pageIndex * table.pageSize}
	total={table.total}
	onStep={step}
	onFilter={applyDsl}
	onHosts={showHosts}
	onAddress={showAddress}
/>

<LaunchDialog
	open={rescanOptionsFor !== null}
	rescan={rescanOptionsFor
		? {
				selection: rescanOptionsFor,
				dimension: SurfaceDimension.SERVICES,
				targetType,
				seedKind: seedKindFor(rechecks.schema, SurfaceDimension.SERVICES),
				assets: rescanOptionsFor.picks?.map((pick) => pick.value) ?? [],
				queryLabel: rescanOptionsFor.query ? queryLabel() : undefined
			}
		: null}
	onClose={() => {
		rescanOptionsFor = null;
		selection.clear();
	}}
/>
