<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Network from '@lucide/svelte/icons/network';
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
	import ListHeader from './table/list-header.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import GroupList from './table/group-list.svelte';
	import FilterBar from './ips/filter-bar.svelte';
	import IpRow from './ips/ip-row.svelte';
	import IpDetailSheet from './ip-detail-sheet.svelte';
	import { IP_COLUMNS, IP_LEAD_COLUMNS, DEFAULT_VISIBLE_IP_COLUMNS } from './ips/columns';

	import { ipsApi } from '$lib/api/scan-results';
	import { servicesOn } from '$lib/utilities/service-lookup';
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
	import type { QueryError, QueryGroups, QueryLeads } from '$lib/types/asset-query';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';

	interface Props {
		scanId: string;
		projectId: string;
		active?: boolean;
		onTab?: (tab: string, filter?: string) => void;
		onScanTotal?: (total: number) => void;
		query?: IpQuery;
	}

	let {
		scanId,
		projectId,
		active = true,
		onTab,
		onScanTotal,
		query = $bindable(emptyIpQuery())
	}: Props = $props();

	const DEFAULT_SORT = { key: 'hosts', dir: -1 as const };
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
			// storage is a convenience
		}
	}

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('ip_sort')?.split(':') ?? [];
	let pendingIp = initial.get('ip');

	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.ipsColumns, null));
	let density = $state<string>(readPref(STORAGE_KEYS.ipsDensity, 'cozy'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.ipsPageSize, RESULTS_PAGE_SIZE));
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('ip_page') ?? 1) - 1));

	let items = $state<IpGroupRead[]>([]);
	let total = $state(0);
	let totalCapped = $state(false);
	let queryError = $state<QueryError | null>(null);
	let queryReady = $state(true);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let facets = $state<IpFacetSet>(EMPTY_IP_FACETS);
	let facetsLoaded = $state(false);
	let leadSet = $state<QueryLeads | null>(null);
	let groupBy = $state<string>(initial.get('ip_group') ?? '');
	let groupSet = $state<QueryGroups | null>(null);
	let groupLoading = $state(false);
	let groupReq = 0;

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

	let scanTotal = $derived(facets.exposure.reduce((n, f) => n + f.count, 0));
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let selectedIndex = $derived(selected ? items.findIndex((g) => g.ip === selected?.ip) : -1);
	let visible = $derived(
		visiblePref ?? DEFAULT_VISIBLE_IP_COLUMNS.filter((k) => k !== 'ports' || facets.port.length > 0)
	);
	let shownColumns = $derived(IP_COLUMNS.filter((c) => visible.includes(c.key)));
	let checkedCount = $derived(items.filter((g) => checkedIps.has(g.ip)).length);
	let selectAllChecked = $derived<boolean | 'indeterminate'>(
		items.length > 0 && checkedCount === items.length
			? true
			: checkedCount > 0
				? 'indeterminate'
				: false
	);
	let filtered = $derived(ipActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(ipQueryChips(query, facets));
	let rowPad = $derived(ROW_PAD[density] ?? ROW_PAD.cozy);
	let term = $derived(query.search.trim().includes(':') ? '' : query.search.trim());
	let exposureTab = $derived(
		query.exposure.length === 0 ? 'all' : query.exposure.length === 1 ? query.exposure[0] : ''
	);
	let exposureCounts = $derived.by(() => {
		if (!facetsLoaded) return null;
		const m: Record<string, number> = { all: scanTotal };
		for (const f of facets.exposure) m[f.value] = f.count;
		return m;
	});

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.ipsColumns, visiblePref);
	});
	$effect(() => writePref(STORAGE_KEYS.ipsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.ipsPageSize, pageSize));
	$effect(() => {
		const ips = new Set(items.map((g) => g.ip));
		for (const ip of checkedIps) if (!ips.has(ip)) checkedIps.delete(ip);
	});

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
		const filter = compileIpQuery(query, sort.key, sort.dir, pageIndex * pageSize, pageSize);
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
			const res = await ipsApi.search(projectId, scanId, filter);
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
			} else if (pendingIp) {
				const ip = pendingIp;
				pendingIp = null;
				const hit = items.find((g) => g.ip === ip);
				if (hit) open(hit);
				else openIp(ip);
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

	let leadFilter = $derived(compileIpQuery({ ...query, search: '' }, 'ip', 1, 0, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groupBy ? JSON.stringify(leadFilterWithQuery) + groupBy : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await ipsApi.leads(projectId, scanId, leadFilter);
			if (leadSig === sig) leadSet = res.computed ? res : null;
		} catch {
			if (leadSig === sig) leadSet = null;
			loadedLeadSig = '';
		}
	}

	function syncLeads() {
		if (!active || loading || !scanId || !projectId) return;
		if (leadSig === loadedLeadSig) return;
		void loadLeads();
	}

	async function loadGroups() {
		if (!groupBy || !scanId || !projectId) {
			groupSet = null;
			return;
		}
		const my = ++groupReq;
		groupLoading = true;
		try {
			const res = await ipsApi.groups(projectId, scanId, groupBy, leadFilterWithQuery);
			if (my === groupReq) groupSet = res;
		} catch {
			if (my === groupReq) groupSet = null;
		} finally {
			if (my === groupReq) groupLoading = false;
		}
	}

	async function loadFacets() {
		if (!scanId || !projectId) return;
		try {
			facets = await ipsApi.facets(projectId, scanId);
			// only a successful response may restate the tab count; a failed one is not zero
			onScanTotal?.(facets.exposure.reduce((n, f) => n + f.count, 0));
		} catch {
			facets = EMPTY_IP_FACETS;
		} finally {
			facetsLoaded = true;
		}
	}

	async function refresh() {
		refreshing = true;
		try {
			loadedLeadSig = '';
			await Promise.all([runSearch(), loadFacets(), loadGroups()]);
		} finally {
			refreshing = false;
		}
	}

	$effect(() => {
		void JSON.stringify(query);
		void sort.key;
		void sort.dir;
		void pageIndex;
		void pageSize;
		void scanId;
		void projectId;
		void queryReady;
		if (!seen) return;
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
			set('ip_q', query.search || null);
			set('ip_group', groupBy || null);
			set('ip_page', pageIndex > 0 ? String(pageIndex + 1) : null);
			set(
				'ip_sort',
				sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir
					? `${sort.key}:${sort.dir === 1 ? 'asc' : 'desc'}`
					: null
			);
			set('ip', drawerOpen && selected ? selected.ip : null);
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, appPage.state);
		} catch {
			// URL state is best-effort
		}
	}
	$effect(() => {
		void query.search;
		void groupBy;
		void pageIndex;
		void sort.key;
		void sort.dir;
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
		const hit = items.find((g) => g.ip === ip);
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
			toast.error('Could not load address');
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
	function toggleCheck(ip: string) {
		if (checkedIps.has(ip)) checkedIps.delete(ip);
		else checkedIps.add(ip);
	}
	function toggleSelectAll() {
		if (checkedCount === items.length) checkedIps.clear();
		else for (const g of items) checkedIps.add(g.ip);
	}
	function toggleCol(key: string) {
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: IpQuery) {
		query = q;
		pageIndex = 0;
	}
	function setExposureTab(key: string) {
		setQuery({ ...query, exposure: key === 'all' ? [] : [key] });
	}
	function drillGroup(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		groupBy = '';
	}
	function applyDsl(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		drawerOpen = false;
	}
	function showHosts(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.('web-assets', filter);
	}
	function showServices(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.('services', filter);
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
		if (typing || drawerOpen || !items.length) return;
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
		} else if (e.key === 'Escape') {
			cursor = -1;
		}
	}
</script>

<svelte:window onkeydown={onKey} />

<div class="z-10 md:sticky md:top-[var(--scan-tabs-h,0px)]">
	<QueryBar
		bind:this={queryBar}
		bind:ref={searchRef}
		store={ipQuerySchema}
		recentsKey={STORAGE_KEYS.ipsRecentQueries}
		hint="is:sensitive not cdn:yes"
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
			tabs={IP_EXPOSURE_TABS}
			value={exposureTab}
			counts={exposureCounts}
			onChange={setExposureTab}
		/>
	</div>

	<FilterBar
		{query}
		{facets}
		onQuery={setQuery}
		dimensions={ipQuerySchema.schema.group_dimensions}
		columns={IP_COLUMNS}
		{visible}
		onToggleColumn={toggleCol}
		{density}
		onDensity={(d) => (density = d)}
		sorts={IP_SORTS}
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
				onclick={() => setQuery({ ...emptyIpQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if loading && items.length === 0 && !groupBy}
		<div class="divide-y divide-border/50">
			{#each Array(8) as _, i (i)}
				<div class="flex items-center gap-3 px-4 py-3">
					<Skeleton class="h-9 flex-1" />
					<Skeleton class="hidden h-5 w-40 sm:block" />
					<Skeleton class="hidden h-6 w-44 sm:block" />
					<Skeleton class="hidden h-5 w-24 sm:block" />
				</div>
			{/each}
		</div>
	{:else if errored}
		<EmptyState
			icon={TriangleAlert}
			title="Addresses could not be loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" class="gap-2" onclick={refresh}>
				<RefreshCw class="h-4 w-4" /> Retry
			</Button>
		</EmptyState>
	{:else if groupBy}
		<GroupList
			set={groupSet}
			dimensions={ipQuerySchema.schema.group_dimensions}
			noun={ipQuerySchema.schema.noun}
			nounPlural={ipQuerySchema.schema.noun_plural}
			loading={groupLoading}
			onPick={drillGroup}
		/>
	{:else if items.length === 0}
		{#if queryError}
			<EmptyState
				icon={SearchX}
				title="That query could not run"
				description={queryError.message}
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
				title="No addresses yet"
				description="Addresses appear once hostnames resolve or ports are discovered."
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{/if}
	{:else}
		<ScrollArea orientation="horizontal">
			<ListHeader
				lead={IP_LEAD_COLUMNS}
				columns={shownColumns}
				{selectAllChecked}
				selectAllLabel="Select all addresses on this page"
				onSelectAll={toggleSelectAll}
				sortKey={sort.key}
				sortDir={sort.dir}
				onSort={toggleSort}
			/>
			<div class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}">
				{#each items as g, i (g.ip)}
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
			noun="address"
			plural="addresses"
			selectedCount={checkedCount}
			onClearSelection={() => checkedIps.clear()}
			onPage={(p) => (pageIndex = p)}
			onPageSize={(s) => {
				pageSize = s;
				pageIndex = 0;
			}}
		/>
	{/if}
</Card.Root>

<IpDetailSheet
	group={selected}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={selectedIndex}
	pageOffset={pageIndex * pageSize}
	{total}
	onStep={step}
	onFilter={applyDsl}
	onHosts={showHosts}
	onServices={showServices}
/>
