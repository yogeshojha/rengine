<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Network from '@lucide/svelte/icons/network';
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
	import type { SeedPick, SeedSelection } from '$lib/types/recheck';
	import GroupList from './table/group-list.svelte';
	import { GroupedView, ResultsTable } from './table/results-state.svelte';
	import { pageParam, parsePageIndex, parseSort, sortParam, type SortKey } from './table/sort';
	import FilterBar from './ips/filter-bar.svelte';
	import IpRow from './ips/ip-row.svelte';
	import IpDetailSheet from './ip-detail-sheet.svelte';
	import { IP_COLUMNS, IP_LEAD_COLUMNS, DEFAULT_VISIBLE_IP_COLUMNS } from './ips/columns';

	import { ipsApi } from '$lib/api/scan-results';
	import { servicesOn } from '$lib/utilities/service-lookup';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { seedKindFor, selectionLabel } from '$lib/utilities/rechecks';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { startRescan } from '$lib/utilities/rechecks';
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { ipQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import {
		appendToken,
		filterToken,
		type Facet,
		type IpGroupRead
	} from '$lib/utilities/scan-insights';
	import {
		compileIpQuery,
		emptyIpQuery,
		ipActiveFacetCount,
		ipQueryChips,
		EMPTY_IP_FACETS,
		IP_EXPOSURE_TABS,
		IP_SORTS,
		type IpFacetSet,
		type IpQuery
	} from '$lib/utilities/ip-groups';
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
		query?: IpQuery;
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
			...emptyIpQuery(),
			search: appPage.url.searchParams.get('ip_q') ?? ''
		})
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const SVC = SURFACE[SurfaceDimension.SERVICES];

	const IP = SURFACE[SurfaceDimension.IPS];

	let ready = $derived(Boolean(projectId) && (projectWide || Boolean(scanId)));

	const DEFAULT_SORT: SortKey = { key: 'hosts', dir: -1 };

	const initial = appPage.url.searchParams;
	let pendingIp = initial.get('ip');

	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.ipsColumns, null));
	const table = new ResultsTable<IpGroupRead, IpFacetSet>({
		facets: EMPTY_IP_FACETS,
		sort: parseSort(initial.get('ip_sort'), DEFAULT_SORT),
		pageIndex: parsePageIndex(initial.get('ip_page')),
		pageSizeKey: STORAGE_KEYS.ipsPageSize,
		densityKey: STORAGE_KEYS.ipsDensity
	});
	const groups = new GroupedView(
		initial.get('ip_group') ?? '',
		(by) => ipsApi.groups(projectId, scanId, by, leadFilterWithQuery),
		() => ready
	);

	let selected = $state<IpGroupRead | null>(null);
	let drawerOpen = $state(false);
	let cursor = $state(-1);
	let searchRef = $state<HTMLInputElement | null>(null);
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let pendingSelect: 'first' | 'last' | null = null;
	const checkedIps = new SvelteSet<string>();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let scanTotal = $derived(table.facets.exposure.reduce((n, f) => n + f.count, 0));
	let selectedIndex = $derived(selected ? table.items.findIndex((g) => g.ip === selected?.ip) : -1);
	let visible = $derived(
		visiblePref ??
			DEFAULT_VISIBLE_IP_COLUMNS.filter((k) => k !== 'ports' || table.facets.port.length > 0)
	);
	let allColumns = $derived(withTarget(IP_COLUMNS, projectWide));
	let shownColumns = $derived(
		allColumns.filter((c) => visible.includes(c.key) || c.key === 'target')
	);
	let checkedCount = $derived(table.items.filter((g) => checkedIps.has(g.ip)).length);
	let selectAllChecked = $derived(selectAllState(checkedCount, table.items.length));
	let filtered = $derived(ipActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(ipQueryChips(query, table.facets));
	let rowPad = $derived(rowPadding(table.density));
	let term = $derived(query.search.trim().includes(':') ? '' : query.search.trim());
	let exposureTab = $derived(
		query.exposure.length === 0 ? 'all' : query.exposure.length === 1 ? query.exposure[0] : ''
	);
	let exposureCounts = $derived.by(() => {
		if (!table.facetsLoaded) return null;
		const m: Record<string, number> = { all: scanTotal };
		for (const f of table.facets.exposure) m[f.value] = f.count;
		return m;
	});

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.ipsColumns, visiblePref);
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
		const filter = compileIpQuery(
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
			const res = await ipsApi.search(projectId, scanId, filter);
			if (!current()) return;
			table.accept(res);
			if (!res.error && filter.q) queryBar?.remember(filter.q);
			if (pendingSelect) {
				selected =
					pendingSelect === 'first' ? (table.items[0] ?? null) : (table.items.at(-1) ?? null);
				pendingSelect = null;
			} else if (pendingIp) {
				const ip = pendingIp;
				pendingIp = null;
				const hit = table.items.find((g) => g.ip === ip);
				if (hit) open(hit);
				else openIp(ip);
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
		compileIpQuery(query, table.sort.key, table.sort.dir, 0, 1) as unknown as Record<
			string,
			unknown
		>
	);
	let leadFilter = $derived(compileIpQuery({ ...query, search: '' }, 'ip', 1, 0, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groups.by ? JSON.stringify(leadFilterWithQuery) + groups.by : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await ipsApi.leads(projectId, scanId, leadFilter);
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
			table.facets = await ipsApi.facets(projectId, scanId);
			onScanTotal?.(table.facets.exposure.reduce((n, f) => n + f.count, 0));
			table.facetsLoaded = true;
		} catch {
			if (!table.facetsLoaded) table.facets = EMPTY_IP_FACETS;
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
			set('ip_q', query.search || null);
			set('ip_group', groups.by || null);
			set('ip_page', pageParam(table.pageIndex));
			set('ip_sort', sortParam(table.sort, DEFAULT_SORT));
			set('ip', drawerOpen && selected ? selected.ip : null);
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
		void drawerOpen;
		void selected?.ip;
		if (!seen || !active) return;
		untrack(syncUrl);
	});

	function open(g: IpGroupRead) {
		selected = g;
		drawerOpen = true;
	}
	async function openIp(ip: string) {
		const hit = table.items.find((g) => g.ip === ip);
		if (hit) return open(hit);
		try {
			const res = await ipsApi.search(
				projectId,
				scanId,
				compileIpQuery({ ...emptyIpQuery(), search: filterToken('ip', ip) }, 'ip', 1, 0, 5)
			);
			const exact = res.items.find((g) => g.ip === ip);
			if (exact) open(exact);
			else toast.error('Address not found in this scan');
		} catch {
			toast.error('Address not loaded');
		}
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
	function toggleCheck(ip: string) {
		if (checkedIps.has(ip)) checkedIps.delete(ip);
		else checkedIps.add(ip);
	}
	function toggleSelectAll() {
		if (checkedCount === table.items.length) checkedIps.clear();
		else for (const g of table.items) checkedIps.add(g.ip);
	}
	function toggleCol(key: string) {
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: IpQuery) {
		query = q;
		table.pageIndex = 0;
	}
	function setExposureTab(key: string) {
		setQuery({ ...query, exposure: key === 'all' ? [] : [key] });
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
	function showServices(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.(SVC.tab, filter);
	}
	function scrollCursor() {
		document.querySelector(`[data-ip-row-index="${cursor}"]`)?.scrollIntoView({ block: 'nearest' });
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

	function pickOf(ip: string): SeedPick {
		return scanId ? { value: ip, scan_id: scanId } : { value: ip };
	}

	function pickedSelection(): SeedSelection {
		return { dimension: SurfaceDimension.IPS, picks: [...checkedIps].map(pickOf) };
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
		} = compileIpQuery(query, 'ip', 1, 0, 1);
		return {
			dimension: SurfaceDimension.IPS,
			query: { filter, scan_ids: scanId ? [scanId] : [] }
		};
	}

	async function run(sel: SeedSelection) {
		if (rescanBusy) return;
		rescanBusy = true;
		const ok = await startRescan(projectId, sel, 'address', 'addresses');
		if (ok) checkedIps.clear();
		rescanBusy = false;
	}

	async function rescanSelection() {
		if (checkedIps.size) await run(pickedSelection());
	}

	async function rescanAllMatching() {
		await run(querySelection());
	}

	let rescanOptionsFor = $state<SeedSelection | null>(null);

	function openRescanOptions() {
		if (checkedIps.size) rescanOptionsFor = pickedSelection();
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
		store={ipQuerySchema}
		recentsKey={SURFACE[SurfaceDimension.IPS].recentsKey}
		hint="is:sensitive not cdn:yes"
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
			tabs={IP_EXPOSURE_TABS}
			value={exposureTab}
			counts={exposureCounts}
			onChange={setExposureTab}
		/>
	</div>

	<FilterBar
		{query}
		facets={table.facets}
		onQuery={setQuery}
		dimensions={ipQuerySchema.schema.group_dimensions}
		columns={IP_COLUMNS}
		{visible}
		onToggleColumn={toggleCol}
		density={table.density}
		onDensity={(d) => (table.density = d)}
		sorts={IP_SORTS}
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
				onclick={() => setQuery({ ...emptyIpQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if !groups.by}
		<SelectionBar
			noun={IP.noun}
			nounPlural={IP.nounPlural}
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
				lead={IP_LEAD_COLUMNS}
				columns={shownColumns}
				density={table.density}
				selectable
			/>
		</ScrollArea>
	{:else if table.errored}
		<EmptyState
			icon={TriangleAlert}
			title="Addresses not loaded"
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
			dimensions={ipQuerySchema.schema.group_dimensions}
			noun={ipQuerySchema.schema.noun}
			nounPlural={ipQuerySchema.schema.noun_plural}
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
				title="No addresses match"
				description="Widen the search or remove a filter."
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button size="sm" variant="outline" class="gap-2" onclick={() => setQuery(emptyIpQuery())}>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			</EmptyState>
		{:else}
			<EmptyState
				icon={Network}
				title="No addresses in this scan"
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{/if}
	{:else}
		<ListHeader
			sticky
			top={barH}
			follow={scrollRef}
			lead={IP_LEAD_COLUMNS}
			columns={shownColumns}
			{selectAllChecked}
			selectAllLabel="Select all addresses on this page"
			onSelectAll={toggleSelectAll}
			sortKey={table.sort.key}
			sortDir={table.sort.dir}
			onSort={toggleSort}
		/>
		<ScrollArea orientation="horizontal" bind:ref={scrollRef}>
			<div class="divide-y divide-border/50 transition-opacity {table.loading ? 'opacity-60' : ''}">
				{#each table.items as g, i (g.ip)}
					<IpRow
						group={g}
						index={i}
						{term}
						columns={shownColumns}
						checked={checkedIps.has(g.ip)}
						onCheck={toggleCheck}
						selected={drawerOpen && selected?.ip === g.ip}
						focused={cursor === i}
						pad={rowPad}
						onOpen={open}
						onFilter={applyDsl}
						onHosts={showHosts}
						onServices={showServices}
						loadServices={(ip) => servicesOn(projectId, scanId, 'ip', ip)}
						recheck={rechecks.latest(scanId, g.ip)}
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
			noun={IP.noun}
			plural={IP.nounPlural}
			onPage={(p) => (table.pageIndex = p)}
			onPageSize={(s) => table.setPageSize(s)}
		/>
	{/if}
</Card.Root>

<RowSelectionBar
	count={checkedIps.size}
	dimension={SurfaceDimension.IPS}
	{projectId}
	{scanId}
	copy={[{ label: 'addresses', values: () => [...checkedIps] }]}
	ids={() => [...checkedIps]}
	{exportFilters}
	onDeleted={() => {
		checkedIps.clear();
		void refresh();
	}}
	onClear={() => checkedIps.clear()}
>
	{#snippet actions()}
		<RescanAction
			count={checkedIps.size}
			dimension={SurfaceDimension.IPS}
			busy={rescanBusy}
			onRescan={rescanSelection}
		/>
		<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={openRescanOptions}>
			<Settings2 class="h-3.5 w-3.5 text-muted-foreground" />
			Options
		</Button>
	{/snippet}
</RowSelectionBar>

<IpDetailSheet
	group={selected}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={selectedIndex}
	pageOffset={table.pageIndex * table.pageSize}
	total={table.total}
	onStep={step}
	onFilter={applyDsl}
	onHosts={showHosts}
	onServices={showServices}
/>

<LaunchDialog
	open={rescanOptionsFor !== null}
	rescan={rescanOptionsFor
		? {
				selection: rescanOptionsFor,
				dimension: SurfaceDimension.IPS,
				targetType,
				seedKind: seedKindFor(rechecks.schema, SurfaceDimension.IPS),
				assets: rescanOptionsFor.picks?.map((pick) => pick.value) ?? [],
				queryLabel: rescanOptionsFor.query ? queryLabel() : undefined
			}
		: null}
	onClose={() => {
		rescanOptionsFor = null;
		checkedIps.clear();
	}}
/>
