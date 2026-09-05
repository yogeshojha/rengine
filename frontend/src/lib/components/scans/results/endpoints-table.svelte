<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Waypoints from '@lucide/svelte/icons/waypoints';
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
	import FilterBar from './endpoints/filter-bar.svelte';
	import EndpointRow from './endpoints/endpoint-row.svelte';
	import TreeRail from './endpoints/tree-rail.svelte';
	import PathBreadcrumb from './endpoints/path-breadcrumb.svelte';
	import CoverageStrip from './endpoints/coverage-strip.svelte';
	import EndpointDetailSheet from './endpoint-detail-sheet.svelte';
	import {
		ENDPOINT_COLUMNS,
		ENDPOINT_LEAD_COLUMNS,
		DEFAULT_VISIBLE_ENDPOINT_COLUMNS
	} from './endpoints/columns';

	import { endpointsApi } from '$lib/api/scan-results';
	import { endpointQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { appendToken, type Facet } from '$lib/utilities/scan-insights';
	import {
		compileEndpointQuery,
		emptyEndpointQuery,
		endpointActiveFacetCount,
		endpointQueryChips,
		EMPTY_ENDPOINT_FACETS,
		ENDPOINT_CLASS_TABS,
		ENDPOINT_SORTS,
		type EndpointCoverageRead,
		type EndpointFacetSet,
		type EndpointQuery,
		type EndpointRead as Endpoint,
		type EndpointSummary,
		type EndpointTree,
		type TreeNode
	} from '$lib/utilities/endpoints';
	import type { QueryError, QueryGroups, QueryLeads } from '$lib/types/asset-query';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';

	interface Props {
		scanId: string;
		projectId: string;
		active?: boolean;
		onTab?: (tab: string, filter?: string) => void;
		onScanTotal?: (total: number) => void;
		query?: EndpointQuery;
	}

	let {
		scanId,
		projectId,
		active = true,
		onTab,
		onScanTotal,
		query = $bindable({
			...emptyEndpointQuery(),
			search: appPage.url.searchParams.get('ep_q') ?? '',
			host: appPage.url.searchParams.get('ep_host') ?? '',
			dir: appPage.url.searchParams.get('ep_dir') ?? ''
		})
	}: Props = $props();

	const DEFAULT_SORT = { key: 'relevance', dir: -1 as const };
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
	const initialSort = initial.get('ep_sort')?.split(':') ?? [];

	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.endpointsColumns, null));
	let density = $state<string>(readPref(STORAGE_KEYS.endpointsDensity, 'cozy'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.endpointsPageSize, RESULTS_PAGE_SIZE));
	let view = $state<string>(initial.get('ep_view') ?? readPref(STORAGE_KEYS.endpointsView, 'tree'));
	let treeMode = $state<string>(readPref(STORAGE_KEYS.endpointsTreeMode, 'host'));
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('ep_page') ?? 1) - 1));

	let items = $state<Endpoint[]>([]);
	let total = $state(0);
	let totalCapped = $state(false);
	let queryError = $state<QueryError | null>(null);
	let queryReady = $state(true);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let facets = $state<EndpointFacetSet>(EMPTY_ENDPOINT_FACETS);
	let facetsLoaded = $state(false);
	let leadSet = $state<QueryLeads | null>(null);
	let groupBy = $state<string>(initial.get('ep_group') ?? '');
	let groupSet = $state<QueryGroups | null>(null);
	let groupLoading = $state(false);
	let groupReq = 0;
	let tree = $state<EndpointTree | null>(null);
	let treeLoading = $state(false);
	let treeReq = 0;
	let coverage = $state<EndpointCoverageRead[]>([]);
	let summary = $state<EndpointSummary | null>(null);

	let selected = $state<Endpoint | null>(null);
	let drawerOpen = $state(false);
	let cursor = $state(-1);
	let searchRef = $state<HTMLInputElement | null>(null);
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let pendingSelect: 'first' | 'last' | null = null;

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let scanTotal = $derived(facets.total);
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let selectedIndex = $derived(selected ? items.findIndex((e) => e.id === selected?.id) : -1);
	let visible = $derived(visiblePref ?? DEFAULT_VISIBLE_ENDPOINT_COLUMNS);
	let shownColumns = $derived(ENDPOINT_COLUMNS.filter((c) => visible.includes(c.key)));
	let filtered = $derived(endpointActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(endpointQueryChips(query));
	let rowPad = $derived(ROW_PAD[density] ?? ROW_PAD.cozy);
	let term = $derived(query.search.trim().includes(':') ? '' : query.search.trim());
	let classTab = $derived(query.endpointClass || 'all');
	// mirrors endpoint_tree.py: a node key is (host or '') + path
	let selectedKey = $derived(query.host || query.dir ? `${query.host}${query.dir || '/'}` : '');
	let classCounts = $derived.by(() => {
		if (!facetsLoaded) return null;
		const m: Record<string, number> = { all: scanTotal };
		for (const f of facets.endpoint_class) m[f.value] = f.count;
		return m;
	});

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.endpointsColumns, visiblePref);
	});
	$effect(() => writePref(STORAGE_KEYS.endpointsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.endpointsPageSize, pageSize));
	$effect(() => writePref(STORAGE_KEYS.endpointsView, view));
	$effect(() => writePref(STORAGE_KEYS.endpointsTreeMode, treeMode));

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
		const filter = compileEndpointQuery(query, sort.key, sort.dir, pageIndex + 1, pageSize);
		const sig = JSON.stringify({ ...filter, page: 1 });
		if (sig !== lastSig && pageIndex !== 0 && !pendingSelect) {
			lastSig = sig;
			pageIndex = 0;
			return;
		}
		lastSig = sig;
		const my = ++reqId;
		loading = true;
		try {
			const res = await endpointsApi.search(projectId, scanId, filter);
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

	// the tree answers the same query, minus the directory it is used to pick
	let treeFilter = $derived(compileEndpointQuery({ ...query, dir: '', host: '' }, 'path', 1, 1, 1));
	let treeSig = $derived(JSON.stringify(treeFilter) + treeMode);
	let loadedTreeSig = '';

	async function loadTree() {
		if (!scanId || !projectId) return;
		const my = ++treeReq;
		const sig = treeSig;
		loadedTreeSig = sig;
		treeLoading = true;
		try {
			const res = await endpointsApi.tree(projectId, scanId, treeMode, treeFilter);
			if (my === treeReq) tree = res;
		} catch {
			if (my === treeReq) {
				tree = null;
				loadedTreeSig = '';
			}
		} finally {
			if (my === treeReq) treeLoading = false;
		}
	}

	let leadFilter = $derived(compileEndpointQuery({ ...query, search: '' }, 'path', 1, 1, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groupBy ? JSON.stringify(leadFilterWithQuery) + groupBy : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await endpointsApi.leads(projectId, scanId, leadFilter);
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
			const res = await endpointsApi.groups(projectId, scanId, groupBy, leadFilterWithQuery);
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
			facets = await endpointsApi.facets(projectId, scanId);
			// only a successful response may restate the tab count; a failed one is not zero
			onScanTotal?.(facets.total);
		} catch {
			facets = EMPTY_ENDPOINT_FACETS;
		} finally {
			facetsLoaded = true;
		}
	}

	async function loadAccount() {
		if (!scanId || !projectId) return;
		try {
			const [c, s] = await Promise.all([
				endpointsApi.coverage(projectId, scanId),
				endpointsApi.summary(projectId, scanId)
			]);
			coverage = c;
			summary = s;
		} catch {
			coverage = [];
			summary = null;
		}
	}

	async function refresh() {
		refreshing = true;
		try {
			loadedLeadSig = '';
			loadedTreeSig = '';
			await Promise.all([runSearch(), loadFacets(), loadGroups(), loadTree(), loadAccount()]);
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
		untrack(loadAccount);
	});

	$effect(() => {
		void treeSig;
		if (!seen || view !== 'tree') return;
		if (treeSig === loadedTreeSig) return;
		const handle = setTimeout(() => untrack(loadTree), SEARCH_DEBOUNCE_MS);
		return () => clearTimeout(handle);
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
			set('ep_q', query.search || null);
			set('ep_host', query.host || null);
			set('ep_dir', query.dir || null);
			set('ep_group', groupBy || null);
			set('ep_view', view === 'tree' ? null : view);
			set('ep_page', pageIndex > 0 ? String(pageIndex + 1) : null);
			set(
				'ep_sort',
				sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir
					? `${sort.key}:${sort.dir === 1 ? 'asc' : 'desc'}`
					: null
			);
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, appPage.state);
		} catch {
			// URL state is best-effort
		}
	}
	$effect(() => {
		void query.search;
		void query.host;
		void query.dir;
		void groupBy;
		void pageIndex;
		void view;
		void sort.key;
		void sort.dir;
		if (!seen || !active) return;
		untrack(syncUrl);
	});

	function open(e: Endpoint) {
		selected = e;
		drawerOpen = true;
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
	function toggleCol(key: string) {
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: EndpointQuery) {
		query = q;
		pageIndex = 0;
	}
	function setClassTab(key: string) {
		setQuery({ ...query, endpointClass: key === 'all' ? '' : key });
	}
	function drillGroup(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		groupBy = '';
	}
	function applyDsl(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		drawerOpen = false;
	}
	function pickNode(node: TreeNode | null) {
		if (!node) {
			setQuery({ ...query, host: '', dir: '', subtree: true });
			return;
		}
		if (node.kind === 'host') {
			setQuery({ ...query, host: node.host ?? '', dir: '', subtree: true });
			return;
		}
		setQuery({ ...query, host: node.host ?? '', dir: node.path, subtree: true });
	}
	function pickCrumb(host: string, path: string) {
		setQuery({ ...query, host, dir: path === '/' ? '' : path, subtree: true });
	}
	function showHost(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.('web-assets', filter);
	}
	function scrollCursor() {
		document
			.querySelector(`[data-endpoint-row-index="${cursor}"]`)
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

<div class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2">
	<QueryBar
		bind:this={queryBar}
		bind:ref={searchRef}
		store={endpointQuerySchema}
		recentsKey={STORAGE_KEYS.endpointsRecentQueries}
		hint="is:param and is:live"
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
			tabs={ENDPOINT_CLASS_TABS}
			value={classTab}
			counts={classCounts}
			onChange={setClassTab}
		/>
	</div>

	<CoverageStrip {coverage} {summary} />

	<FilterBar
		{query}
		{facets}
		onQuery={setQuery}
		dimensions={endpointQuerySchema.schema.group_dimensions}
		columns={ENDPOINT_COLUMNS}
		{visible}
		onToggleColumn={toggleCol}
		{density}
		onDensity={(d) => (density = d)}
		sorts={ENDPOINT_SORTS}
		sortKey={sort.key}
		sortDir={sort.dir}
		onSort={toggleSort}
		{refreshing}
		onRefresh={refresh}
		{groupBy}
		onGroupBy={(key) => (groupBy = key)}
		{view}
		onView={(v) => (view = v)}
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
				onclick={() => setQuery({ ...emptyEndpointQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	<div class="flex min-h-0 {view === 'tree' ? 'md:flex-row' : ''} flex-col">
		{#if view === 'tree'}
			<aside class="w-full shrink-0 border-b md:h-[42rem] md:w-80 md:border-r md:border-b-0">
				<TreeRail
					{tree}
					loading={treeLoading}
					mode={treeMode}
					selected={selectedKey}
					onSelect={pickNode}
					onMode={(m) => (treeMode = m)}
				/>
			</aside>
		{/if}

		<div class="flex min-w-0 flex-1 flex-col">
			{#if view === 'tree' && (query.host || query.dir)}
				<div class="flex items-center gap-2 border-b bg-muted/10 px-4 py-2">
					<PathBreadcrumb host={query.host} path={query.dir} onSelect={pickCrumb} />
					<Button
						variant="ghost"
						size="sm"
						class="ml-auto h-6 px-1.5 text-xs font-normal text-muted-foreground"
						onclick={() => setQuery({ ...query, subtree: !query.subtree })}
					>
						{query.subtree ? 'Including subfolders' : 'This folder only'}
					</Button>
				</div>
			{/if}

			{#if loading && items.length === 0 && !groupBy}
				<div class="divide-y divide-border/50">
					{#each Array(8) as _, i (i)}
						<div class="flex items-center gap-3 px-4 py-3">
							<Skeleton class="h-9 flex-1" />
							<Skeleton class="hidden h-5 w-40 sm:block" />
							<Skeleton class="hidden h-6 w-44 sm:block" />
						</div>
					{/each}
				</div>
			{:else if errored}
				<EmptyState
					icon={TriangleAlert}
					title="Endpoints could not be loaded"
					class="rounded-none border-0 bg-transparent py-16"
				>
					<Button variant="outline" class="gap-2" onclick={refresh}>
						<RefreshCw class="h-4 w-4" /> Retry
					</Button>
				</EmptyState>
			{:else if groupBy}
				<GroupList
					set={groupSet}
					dimensions={endpointQuerySchema.schema.group_dimensions}
					noun={endpointQuerySchema.schema.noun}
					nounPlural={endpointQuerySchema.schema.noun_plural}
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
						title="No endpoints match"
						description="Widen the search or remove a filter."
						class="rounded-none border-0 bg-transparent py-16"
					>
						<Button
							size="sm"
							variant="outline"
							class="gap-2"
							onclick={() => setQuery(emptyEndpointQuery())}
						>
							<X class="h-4 w-4" /> Clear filters
						</Button>
					</EmptyState>
				{:else}
					<EmptyState
						icon={Waypoints}
						title="No endpoints yet"
						description="Endpoints appear once URL discovery has run on this scan."
						class="rounded-none border-0 bg-transparent py-16"
					/>
				{/if}
			{:else}
				<ScrollArea orientation="horizontal">
					<ListHeader
						lead={ENDPOINT_LEAD_COLUMNS}
						columns={shownColumns}
						sortKey={sort.key}
						sortDir={sort.dir}
						onSort={toggleSort}
					/>
					<div class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}">
						{#each items as e, i (e.id)}
							<div data-endpoint-row-index={i}>
								<EndpointRow
									endpoint={e}
									{term}
									columns={visible}
									active={drawerOpen && selected?.id === e.id}
									focused={cursor === i}
									pad={rowPad}
									onOpen={open}
									onFilter={applyDsl}
								/>
							</div>
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
					noun="endpoint"
					plural="endpoints"
					onPage={(p) => (pageIndex = p)}
					onPageSize={(s) => {
						pageSize = s;
						pageIndex = 0;
					}}
				/>
			{/if}
		</div>
	</div>
</Card.Root>

<EndpointDetailSheet
	endpoint={selected}
	{projectId}
	{scanId}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={selectedIndex}
	pageOffset={pageIndex * pageSize}
	{total}
	onStep={step}
	onFilter={applyDsl}
	onHost={showHost}
/>
