<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import History from '@lucide/svelte/icons/history';

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
	import Outline from './endpoints/outline.svelte';
	import CoverageStrip from './endpoints/coverage-strip.svelte';
	import EndpointDetailSheet from './endpoint-detail-sheet.svelte';
	import {
		ENDPOINT_COLUMNS,
		ENDPOINT_LEAD_COLUMNS,
		DEFAULT_VISIBLE_ENDPOINT_COLUMNS,
		DEFAULT_VISIBLE_OUTLINE_COLUMNS,
		OUTLINE_HIDDEN_COLUMNS
	} from './endpoints/columns';

	import { endpointsApi } from '$lib/api/scan-results';
	import { endpointQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { STATIC_CLASSES } from '$lib/config/endpoints';
	import { appendToken, exactToken, type Facet } from '$lib/utilities/scan-insights';
	import {
		compileEndpointQuery,
		emptyEndpointQuery,
		endpointActiveFacetCount,
		endpointQueryChips,
		highlightTerms,
		locationTokens,
		EMPTY_ENDPOINT_FACETS,
		ENDPOINT_CLASS_TABS,
		ENDPOINT_SORTS,
		type EndpointCoverageRead,
		type EndpointFacetSet,
		type EndpointFilter,
		type EndpointQuery,
		type EndpointRead as Endpoint,
		type EndpointSummary,
		type EndpointTree,
		type HostPage,
		type GonePage,
		type TreeNode
	} from '$lib/utilities/endpoints';
	import type { Crumb } from './endpoints/outline-context';
	import type { QueryError, QueryGroups, QueryLeads } from '$lib/types/asset-query';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { formatShortDate } from '$lib/utilities/dates';

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
	const VIEWS = ['outline', 'list'];
	const DEFAULT_HIDE_STATIC: Record<string, boolean> = { outline: true, list: false };

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
	function normalizeView(raw: string | null | undefined): string {
		return raw && VIEWS.includes(raw) ? raw : 'outline';
	}

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('ep_sort')?.split(':') ?? [];

	let listColumnsPref = $state<string[] | null>(readPref(STORAGE_KEYS.endpointsColumns, null));
	let outlineColumnsPref = $state<string[] | null>(
		readPref(STORAGE_KEYS.endpointsOutlineColumns, null)
	);
	let density = $state<string>(readPref(STORAGE_KEYS.endpointsDensity, 'cozy'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.endpointsPageSize, RESULTS_PAGE_SIZE));
	let view = $state<string>(
		normalizeView(initial.get('ep_view') ?? readPref(STORAGE_KEYS.endpointsView, 'outline'))
	);
	let treeMode = $state<string>(readPref(STORAGE_KEYS.endpointsTreeMode, 'host'));
	let hideStaticPref = $state<Record<string, boolean>>(
		readPref(STORAGE_KEYS.endpointsHideStatic, DEFAULT_HIDE_STATIC)
	);
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
	let hosts = $state<HostPage | null>(null);
	let hostPage = $state(1);
	let treeLoading = $state(false);
	let treeReq = 0;
	let outline = $state<ReturnType<typeof Outline> | null>(null);
	let expandedCount = $state(0);
	let goneLens = $state(false);
	let gonePage = $state<GonePage | null>(null);
	let goneLoading = $state(false);
	let goneIndex = $state(0);
	let goneReq = 0;
	let selectedScanId = $state('');
	let headEl = $state<HTMLElement | null>(null);
	let crumbs = $state<Crumb[]>([]);
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

	let isOutline = $derived(view === 'outline');
	let hideStatic = $derived(hideStaticPref[view] ?? DEFAULT_HIDE_STATIC[view] ?? false);
	let scanTotal = $derived(facets.total);
	let staticTotal = $derived(facets.static_total);
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let selectedIndex = $derived(selected ? items.findIndex((e) => e.id === selected?.id) : -1);
	let columnOptions = $derived(
		isOutline
			? ENDPOINT_COLUMNS.filter((c) => !OUTLINE_HIDDEN_COLUMNS.has(c.key))
			: ENDPOINT_COLUMNS
	);
	let visible = $derived(
		isOutline
			? (outlineColumnsPref ?? DEFAULT_VISIBLE_OUTLINE_COLUMNS)
			: (listColumnsPref ?? DEFAULT_VISIBLE_ENDPOINT_COLUMNS)
	);
	let shownColumns = $derived(columnOptions.filter((c) => visible.includes(c.key)));
	let filtered = $derived(endpointActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(endpointQueryChips(query));
	let rowPad = $derived(ROW_PAD[density] ?? ROW_PAD.cozy);
	let known = $derived((name: string) => endpointQuerySchema.byName.has(name));
	let terms = $derived(highlightTerms(query.search, known));
	let classTab = $derived(query.endpointClass || 'all');
	let classTabs = $derived(
		hideStatic ? ENDPOINT_CLASS_TABS.filter((t) => !STATIC_CLASSES.has(t.key)) : ENDPOINT_CLASS_TABS
	);
	let classCounts = $derived.by(() => {
		if (!facetsLoaded) return null;
		const m: Record<string, number> = { all: hideStatic ? scanTotal - staticTotal : scanTotal };
		for (const f of facets.endpoint_class) m[f.value] = f.count;
		return m;
	});

	$effect(() => {
		if (listColumnsPref) writePref(STORAGE_KEYS.endpointsColumns, listColumnsPref);
	});
	$effect(() => {
		if (outlineColumnsPref) writePref(STORAGE_KEYS.endpointsOutlineColumns, outlineColumnsPref);
	});
	$effect(() => writePref(STORAGE_KEYS.endpointsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.endpointsPageSize, pageSize));
	$effect(() => writePref(STORAGE_KEYS.endpointsView, view));
	$effect(() => writePref(STORAGE_KEYS.endpointsTreeMode, treeMode));
	$effect(() => writePref(STORAGE_KEYS.endpointsHideStatic, hideStaticPref));

	function compiled(
		q: EndpointQuery,
		sortKey: string,
		dir: 1 | -1,
		pageNo: number,
		size: number
	): EndpointFilter {
		return { ...compileEndpointQuery(q, sortKey, dir, pageNo, size), hide_static: hideStatic };
	}

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
		const filter = compiled(query, sort.key, sort.dir, pageIndex + 1, pageSize);
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

	// the outline answers the whole query: what it shows is exactly what the list would
	let treeFilter = $derived(compiled(query, sort.key, sort.dir, 1, 1));
	let treeSig = $derived(JSON.stringify(treeFilter) + treeMode);
	let hostsSig = $derived(treeSig + '|' + hostPage);
	let loadedTreeSig = '';

	async function loadTree() {
		if (!scanId || !projectId) return;
		const my = ++treeReq;
		const merged = treeMode === 'merged';
		loadedTreeSig = merged ? treeSig : hostsSig;
		treeLoading = true;
		try {
			if (merged) {
				const res = await endpointsApi.tree(projectId, scanId, treeMode, treeFilter);
				if (my === treeReq) {
					tree = res;
					hosts = null;
				}
			} else {
				const res = await endpointsApi.treeHosts(projectId, scanId, {
					...treeFilter,
					page: hostPage,
					size: RESULTS_PAGE_SIZE
				});
				if (my === treeReq) {
					hosts = res;
					tree = null;
				}
			}
		} catch {
			if (my === treeReq) {
				tree = null;
				hosts = null;
				loadedTreeSig = '';
			}
		} finally {
			if (my === treeReq) treeLoading = false;
		}
	}

	// a new query starts the host list over at page one
	$effect(() => {
		void treeSig;
		untrack(() => (hostPage = 1));
	});

	let leadFilter = $derived(compiled({ ...query, search: '' }, 'path', 1, 1, 1));
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
			await Promise.all([
				runSearch(),
				loadFacets(),
				loadGroups(),
				isOutline ? loadTree() : Promise.resolve(),
				loadAccount()
			]);
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
		void hideStatic;
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
		void hostsSig;
		if (!seen || !isOutline) return;
		const sig = treeMode === 'merged' ? treeSig : hostsSig;
		if (sig === loadedTreeSig) return;
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
			set('ep_view', view === 'outline' ? null : view);
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
		selectedScanId = scanId;
		selected = e;
		drawerOpen = true;
	}
	async function verifyBranch(node: TreeNode) {
		if (!node.host) return;
		const where = node.kind === 'host' ? node.host : `${node.path} on ${node.host}`;
		try {
			const res = await endpointsApi.verify(projectId, scanId, {
				host: node.host,
				dir_path: node.kind === 'host' ? null : node.path,
				limit: 500
			});
			if (!res.accepted) {
				toast.error(
					res.unverified
						? 'The worker did not accept the job.'
						: `Nothing under ${where} is unchecked.`
				);
				return;
			}
			toast.success(
				`Verifying ${res.queued.toLocaleString()} ${res.queued === 1 ? 'endpoint' : 'endpoints'} under ${where}. Refresh to see the results.`
			);
		} catch {
			toast.error('Verification could not be queued.');
		}
	}
	function reveal(e: Endpoint) {
		drawerOpen = false;
		goneLens = false;
		view = 'outline';
		treeMode = 'host';
		setQuery({ ...query, search: locationTokens(e.host, e.path) });
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
		const next = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
		if (isOutline) outlineColumnsPref = next;
		else listColumnsPref = next;
	}
	let goneFilter = $derived(compiled(query, sort.key, sort.dir, goneIndex + 1, pageSize));
	let goneSig = $derived(JSON.stringify(goneFilter));
	let loadedGoneSig = '';

	async function loadGone() {
		if (!scanId || !projectId) return;
		const my = ++goneReq;
		loadedGoneSig = goneSig;
		goneLoading = true;
		try {
			const res = await endpointsApi.gone(projectId, scanId, goneFilter);
			if (my === goneReq) gonePage = res;
		} catch {
			if (my === goneReq) {
				gonePage = null;
				loadedGoneSig = '';
			}
		} finally {
			if (my === goneReq) goneLoading = false;
		}
	}

	$effect(() => {
		void goneSig;
		if (!seen || !goneLens) return;
		if (goneSig === loadedGoneSig) return;
		const handle = setTimeout(() => untrack(loadGone), SEARCH_DEBOUNCE_MS);
		return () => clearTimeout(handle);
	});

	$effect(() => {
		void query;
		void sort.key;
		untrack(() => (goneIndex = 0));
	});

	function openGone(e: Endpoint) {
		selectedScanId = gonePage?.previous_scan_id ?? scanId;
		selected = e;
		drawerOpen = true;
	}

	function setHideStatic(value: boolean) {
		hideStaticPref = { ...hideStaticPref, [view]: value };
		pageIndex = 0;
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
	function showInList(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		view = 'list';
	}
	function pivotHost(host: string) {
		setQuery({ ...query, search: appendToken(query.search, exactToken('host', host)) });
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
		if (isOutline || typing || drawerOpen || !items.length) return;
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

<div
	class="relative z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2"
	bind:this={headEl}
>
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
	{#if isOutline && !goneLens && crumbs.length}
		<div
			class="absolute inset-x-0 top-full flex h-8 items-center gap-1 overflow-hidden border-x border-b bg-card/95 px-4 text-xs shadow-sm backdrop-blur"
		>
			{#each crumbs as crumb, i (crumb.key)}
				{#if i > 0}<span class="text-muted-foreground/60">›</span>{/if}
				<button
					type="button"
					class="max-w-64 truncate font-mono text-muted-foreground hover:text-foreground hover:underline"
					onclick={() => outline?.jumpTo(crumb.key)}
				>
					{crumb.name}
				</button>
			{/each}
		</div>
	{/if}
</div>

{#snippet emptyStates()}
	{#if queryError}
		<EmptyState
			icon={SearchX}
			title="That query could not run"
			description={queryError.message}
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{:else if filtered || (hideStatic && scanTotal > 0)}
		<EmptyState
			icon={SearchX}
			title="No endpoints match"
			description={hideStatic && !filtered
				? 'Every endpoint on this scan is a static file. Show static files to see them.'
				: 'Widen the search or remove a filter.'}
			class="rounded-none border-0 bg-transparent py-16"
		>
			{#if filtered}
				<Button
					size="sm"
					variant="outline"
					class="gap-2"
					onclick={() => setQuery(emptyEndpointQuery())}
				>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			{:else}
				<Button size="sm" variant="outline" onclick={() => setHideStatic(false)}>
					Show static files
				</Button>
			{/if}
		</EmptyState>
	{:else}
		<EmptyState
			icon={Waypoints}
			title="No endpoints yet"
			description="Endpoints appear once URL discovery has run on this scan."
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{/if}
{/snippet}

{#snippet retryState()}
	<EmptyState
		icon={TriangleAlert}
		title="Endpoints could not be loaded"
		class="rounded-none border-0 bg-transparent py-16"
	>
		<Button variant="outline" class="gap-2" onclick={refresh}>
			<RefreshCw class="h-4 w-4" /> Retry
		</Button>
	</EmptyState>
{/snippet}

<Card.Root class="gap-0 overflow-hidden rounded-t-none border-t-0 py-0">
	<div class="border-b px-2">
		<CountTabs tabs={classTabs} value={classTab} counts={classCounts} onChange={setClassTab} />
	</div>

	<CoverageStrip
		{coverage}
		{summary}
		hidden={hideStatic ? staticTotal : 0}
		onShowStatic={() => setHideStatic(false)}
		onShowNew={() => setQuery({ ...query, newOnly: true })}
		onShowGone={() => (goneLens = true)}
	/>

	<FilterBar
		{query}
		{facets}
		onQuery={setQuery}
		dimensions={endpointQuerySchema.schema.group_dimensions}
		columns={columnOptions}
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
		onView={(v) => (view = normalizeView(v))}
		{hideStatic}
		onHideStatic={setHideStatic}
		{treeMode}
		onTreeMode={(m) => (treeMode = m)}
		{expandedCount}
		onCollapseAll={() => outline?.collapseAll()}
		goneCount={summary?.gone ?? 0}
		{goneLens}
		onGoneLens={(on) => (goneLens = on)}
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

	{#if goneLens}
		<div
			class="flex flex-wrap items-center gap-2 border-b bg-muted/10 px-4 py-2 text-xs text-muted-foreground"
		>
			<History class="size-3.5 shrink-0" />
			{#if gonePage}
				<span>
					{gonePage.total.toLocaleString()}
					{gonePage.total === 1 ? 'endpoint' : 'endpoints'} from the scan on
					{gonePage.previous_scan_at
						? formatShortDate(gonePage.previous_scan_at)
						: 'the previous run'}
					{gonePage.total === 1 ? 'was' : 'were'} not found in this scan. Filters and the query apply
					to them too.
				</span>
			{:else}
				<span>Comparing with the previous scan of this target…</span>
			{/if}
			<button
				type="button"
				class="ml-auto rounded-sm text-foreground hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				onclick={() => (goneLens = false)}
			>
				Back to this scan
			</button>
		</div>
		{#if goneLoading && !gonePage}
			<div class="divide-y divide-border/50">
				{#each Array(5) as _, i (i)}
					<div class="flex items-center gap-3 px-4 py-3">
						<Skeleton class="h-9 flex-1" />
						<Skeleton class="hidden h-5 w-40 sm:block" />
					</div>
				{/each}
			</div>
		{:else if gonePage && gonePage.items.length === 0}
			<EmptyState
				icon={History}
				title="Nothing retired"
				description="Every endpoint the previous scan recorded is still present under the current filters."
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if gonePage}
			<ScrollArea orientation="horizontal">
				<ListHeader
					lead={ENDPOINT_LEAD_COLUMNS}
					columns={ENDPOINT_COLUMNS.filter((c) =>
						(listColumnsPref ?? DEFAULT_VISIBLE_ENDPOINT_COLUMNS).includes(c.key)
					)}
					sortKey={sort.key}
					sortDir={sort.dir}
					onSort={toggleSort}
				/>
				<div class="divide-y divide-border/50 transition-opacity {goneLoading ? 'opacity-60' : ''}">
					{#each gonePage.items as e (e.id)}
						<EndpointRow
							endpoint={e}
							{terms}
							columns={listColumnsPref ?? DEFAULT_VISIBLE_ENDPOINT_COLUMNS}
							gone
							active={drawerOpen && selected?.id === e.id}
							pad={rowPad}
							onOpen={openGone}
							onFilter={applyDsl}
						/>
					{/each}
				</div>
			</ScrollArea>
			{#if gonePage.total > pageSize}
				<ResultsPagination
					total={gonePage.total}
					capped={gonePage.total_capped}
					page={goneIndex}
					{pageSize}
					noun="endpoint"
					plural="endpoints"
					onPage={(p) => (goneIndex = p)}
				/>
			{/if}
		{/if}
	{:else if isOutline}
		{#if errored && !tree && !hosts}
			{@render retryState()}
		{:else if !treeLoading && ((tree && tree.nodes.length === 0) || (hosts && hosts.items.length === 0))}
			{@render emptyStates()}
		{:else}
			<Outline
				bind:this={outline}
				{projectId}
				{scanId}
				{tree}
				{hosts}
				loading={treeLoading}
				merged={treeMode === 'merged'}
				filter={treeFilter}
				{terms}
				columns={shownColumns}
				pad={rowPad}
				{active}
				paused={drawerOpen}
				searching={filtered}
				selectedId={drawerOpen ? (selected?.id ?? null) : null}
				sortKey={sort.key}
				sortDir={sort.dir}
				onSort={toggleSort}
				onOpen={open}
				onFilter={applyDsl}
				onShowInList={showInList}
				onHost={pivotHost}
				onHostPage={(p) => (hostPage = p)}
				onExpandedChange={(n) => (expandedCount = n)}
				onVerify={verifyBranch}
				edgeEl={headEl}
				onCrumbs={(c) => (crumbs = c)}
			/>
		{/if}
	{:else}
		<div class="flex min-w-0 flex-1 flex-col">
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
				{@render retryState()}
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
				{@render emptyStates()}
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
									{terms}
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
	{/if}
</Card.Root>

<EndpointDetailSheet
	endpoint={selected}
	{projectId}
	scanId={selectedScanId || scanId}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={isOutline ? -1 : selectedIndex}
	pageOffset={pageIndex * pageSize}
	total={isOutline ? 0 : total}
	onStep={step}
	onFilter={applyDsl}
	onHost={showHost}
	onReveal={reveal}
/>
