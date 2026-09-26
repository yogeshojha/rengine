<script lang="ts">
	import { errorMessage } from '$lib/utilities/errors';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
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
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';

	import QueryBar from './query-bar/query-bar.svelte';
	import { rowPadding, selectAllState } from './table/columns';
	import { readPref, writePref } from '$lib/utilities/storage';
	import ListHeader from './table/list-header.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import GroupList from './table/group-list.svelte';
	import { GroupedView, ResultsTable } from './table/results-state.svelte';
	import {
		flipSort,
		pageParam,
		parsePageIndex,
		parseSort,
		sortParam,
		type SortKey
	} from './table/sort';
	import SelectionBar from './table/selection-bar.svelte';
	import RowSelectionBar from './table/row-selection-bar.svelte';
	import { RowSelection } from './table/selection.svelte';
	import FilterBar from './endpoints/filter-bar.svelte';
	import EndpointRow from './endpoints/endpoint-row.svelte';
	import Outline from './endpoints/outline.svelte';
	import HostTable from './endpoints/host-table.svelte';
	import HostCrumbs from './endpoints/host-crumbs.svelte';
	import HostHeader from './endpoints/host-header.svelte';
	import CoverageStrip from './endpoints/coverage-strip.svelte';
	import EndpointDetailSheet from './endpoint-detail-sheet.svelte';
	import { collectRows, copyBranch, copyWordlist, hostNode } from './endpoints/branch-actions';
	import { proxyLabel } from './endpoints/proxy';
	import {
		ENDPOINT_COLUMNS,
		ENDPOINT_LEAD_COLUMNS,
		DEFAULT_VISIBLE_ENDPOINT_COLUMNS,
		DEFAULT_VISIBLE_OUTLINE_COLUMNS,
		HOST_COLUMNS,
		OUTLINE_HIDDEN_COLUMNS
	} from './endpoints/columns';

	import { endpointsApi } from '$lib/api/scan-results';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { seedKindFor, selectionLabel, startRescan } from '$lib/utilities/rechecks';
	import type { SeedSelection } from '$lib/types/recheck';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { endpointQuerySchema } from '$lib/stores/query-schema.svelte';
	import { connectors as connectorStore } from '$lib/stores/connectors.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { STATIC_CLASSES } from '$lib/config/endpoints';
	import { appendToken, exactToken, type Facet } from '$lib/utilities/scan-insights';
	import {
		compileEndpointQuery,
		emptyEndpointQuery,
		endpointActiveFacetCount,
		endpointQueryChips,
		highlightTerms,
		hostOnlyToken,
		EMPTY_ENDPOINT_FACETS,
		ENDPOINT_CLASS_TABS,
		ENDPOINT_SORTS,
		ENDPOINT_VIEWS,
		HOST_SORTS,
		type EndpointCoverageRead,
		type EndpointFacetSet,
		type EndpointFilter,
		type EndpointQuery,
		type EndpointRead as Endpoint,
		type EndpointSummary,
		type EndpointTree,
		type EndpointView,
		type FolderChip,
		type HostBrief,
		type HostPage,
		type GonePage,
		type TreeNode
	} from '$lib/utilities/endpoints';
	import type { Crumb } from './endpoints/outline-context';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LatestRequest } from '$lib/utilities/latest-request';
	import { afterPause } from '$lib/utilities/debounce';
	import { LiveRefresh, Throttled } from '$lib/utilities/live-results';
	import { formatShortDate } from '$lib/utilities/dates';

	interface Props {
		scanId: string;
		projectWide?: boolean;
		projectId: string;
		targetType?: string;
		active?: boolean;
		revision?: number;
		onTab?: (tab: ResultTab, filter?: string) => void;
		onScanTotal?: (total: number) => void;
		query?: EndpointQuery;
	}

	let {
		scanId,
		projectWide = false,
		projectId,
		targetType = '',
		active = true,
		revision = 0,
		onTab,
		onScanTotal,
		query = $bindable({
			...emptyEndpointQuery(),
			search: appPage.url.searchParams.get('ep_q') ?? '',
			host: appPage.url.searchParams.get('ep_host') ?? '',
			dir: appPage.url.searchParams.get('ep_dir') ?? ''
		})
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];

	const EP = SURFACE[SurfaceDimension.ENDPOINTS];

	let ready = $derived(Boolean(projectId) && (projectWide || Boolean(scanId)));

	const DEFAULT_SORT: SortKey = { key: 'relevance', dir: -1 };
	const DEFAULT_HIDE_STATIC: Record<string, boolean> = { hosts: true, merged: true, list: false };
	const SEND_CAP = 200;

	function normalizeView(raw: string | null | undefined): EndpointView {
		if (raw === 'outline') return 'hosts';
		return raw && (ENDPOINT_VIEWS as readonly string[]).includes(raw)
			? (raw as EndpointView)
			: 'hosts';
	}

	const initial = appPage.url.searchParams;

	let listColumnsPref = $state<string[] | null>(readPref(STORAGE_KEYS.endpointsColumns, null));
	let outlineColumnsPref = $state<string[] | null>(
		readPref(STORAGE_KEYS.endpointsOutlineColumns, null)
	);
	let hostColumnsPref = $state<string[] | null>(readPref(STORAGE_KEYS.endpointsHostColumns, null));
	const table = new ResultsTable<Endpoint, EndpointFacetSet>({
		facets: EMPTY_ENDPOINT_FACETS,
		sort: parseSort(initial.get('ep_sort'), DEFAULT_SORT),
		pageIndex: parsePageIndex(initial.get('ep_page')),
		pageSizeKey: STORAGE_KEYS.endpointsPageSize,
		densityKey: STORAGE_KEYS.endpointsDensity
	});
	const groups = new GroupedView(
		initial.get('ep_group') ?? '',
		(by) => endpointsApi.groups(projectId, scanId, by, leadFilterWithQuery),
		() => ready
	);
	let view = $state<EndpointView>(
		normalizeView(initial.get('ep_view') ?? readPref(STORAGE_KEYS.endpointsView, 'hosts'))
	);
	let hideStaticPref = $state<Record<string, boolean>>(
		readPref(STORAGE_KEYS.endpointsHideStatic, DEFAULT_HIDE_STATIC)
	);
	let hideRootOnly = $state<boolean>(readPref(STORAGE_KEYS.endpointsHideRootOnly, true));
	let hostSort = $state<SortKey>({ ...DEFAULT_SORT });

	let accountLoaded = $state(false);
	let tree = $state<EndpointTree | null>(null);
	let treeLoading = $state(false);
	const treeReq = new LatestRequest();
	let hosts = $state<HostPage | null>(null);
	let hostPage = $state(1);
	let hostsLoading = $state(false);
	const hostsReq = new LatestRequest();
	let hostCursor = $state(-1);
	let pendingHost: 'first' | 'last' | null = null;
	let brief = $state<HostBrief | null>(null);
	let briefLoading = $state(false);
	const briefReq = new LatestRequest();
	let openKeys = $state<string[]>([]);
	let outline = $state<ReturnType<typeof Outline> | null>(null);
	let expandedCount = $state(0);
	let goneLens = $state(false);
	let gonePage = $state<GonePage | null>(null);
	let goneLoading = $state(false);
	let goneIndex = $state(0);
	const goneReq = new LatestRequest();
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

	let isList = $derived(view === 'list');
	let isMerged = $derived(view === 'merged');
	let inHost = $derived(view === 'hosts' && !!query.host);
	let atEstate = $derived(view === 'hosts' && !query.host);
	let isTree = $derived(inHost || isMerged);
	let hideStatic = $derived(hideStaticPref[view] ?? DEFAULT_HIDE_STATIC[view] ?? false);
	let scanTotal = $derived(table.facets.total);
	let staticTotal = $derived(table.facets.static_total);
	let selectedIndex = $derived(selected ? table.items.findIndex((e) => e.id === selected?.id) : -1);
	let columnOptions = $derived(
		atEstate
			? HOST_COLUMNS
			: isTree
				? ENDPOINT_COLUMNS.filter((c) => !OUTLINE_HIDDEN_COLUMNS.has(c.key))
				: ENDPOINT_COLUMNS
	);
	let visible = $derived(
		atEstate
			? (hostColumnsPref ?? HOST_COLUMNS.map((c) => c.key))
			: isTree
				? (outlineColumnsPref ?? DEFAULT_VISIBLE_OUTLINE_COLUMNS)
				: (listColumnsPref ?? DEFAULT_VISIBLE_ENDPOINT_COLUMNS)
	);
	let shownColumns = $derived(columnOptions.filter((c) => visible.includes(c.key)));
	let filtered = $derived(endpointActiveFacetCount({ ...query, host: '' }) > 0 || !!query.search);
	let chips = $derived(endpointQueryChips(query).filter((c) => !(inHost && c.id === 'host')));
	let rowPad = $derived(rowPadding(table.density));
	let known = $derived((name: string) => endpointQuerySchema.byName.has(name));
	let terms = $derived(highlightTerms(query.search, known));
	let classTab = $derived(query.endpointClass || 'all');
	let classTabs = $derived(
		hideStatic ? ENDPOINT_CLASS_TABS.filter((t) => !STATIC_CLASSES.has(t.key)) : ENDPOINT_CLASS_TABS
	);
	let classCounts = $derived.by(() => {
		if (inHost) {
			if (!brief || brief.host !== query.host) return null;
			const all = Object.values(brief.by_class).reduce((a, b) => a + b, 0);
			const m: Record<string, number> = { all: hideStatic ? all - brief.static_total : all };
			for (const [k, v] of Object.entries(brief.by_class)) m[k] = v;
			return m;
		}
		if (!table.facetsLoaded) return null;
		const m: Record<string, number> = { all: hideStatic ? scanTotal - staticTotal : scanTotal };
		for (const f of table.facets.endpoint_class) m[f.value] = f.count;
		return m;
	});
	let proxies = $derived(connectorStore.items);
	let catalog = $derived(connectorStore.catalog);

	$effect(() => {
		if (listColumnsPref) writePref(STORAGE_KEYS.endpointsColumns, listColumnsPref);
	});
	$effect(() => {
		if (outlineColumnsPref) writePref(STORAGE_KEYS.endpointsOutlineColumns, outlineColumnsPref);
	});
	$effect(() => {
		if (hostColumnsPref) writePref(STORAGE_KEYS.endpointsHostColumns, hostColumnsPref);
	});
	$effect(() => writePref(STORAGE_KEYS.endpointsView, view));
	$effect(() => writePref(STORAGE_KEYS.endpointsHideStatic, hideStaticPref));
	$effect(() => writePref(STORAGE_KEYS.endpointsHideRootOnly, hideRootOnly));

	$effect(() => {
		if (!seen || !projectId) return;
		void connectorStore.load(projectId);
		void connectorStore.loadCatalog();
	});

	$effect(() => {
		const search = query.search;
		if (view !== 'hosts' || !search.trim()) return;
		untrack(() => {
			if (query.host) return;
			const host = hostOnlyToken(search, known);
			if (host) enterHost(host);
		});
	});

	function compiled(
		q: EndpointQuery,
		sortKey: string,
		dir: 1 | -1,
		pageNo: number,
		size: number
	): EndpointFilter {
		return { ...compileEndpointQuery(q, sortKey, dir, pageNo, size), hide_static: hideStatic };
	}

	let rescanBusy = $state(false);
	let rescanOptionsFor = $state<SeedSelection | null>(null);

	$effect(() => {
		if (!active || !projectId) return;
		void rechecks.loadSchema();
	});

	function queryLabel(): string {
		return selectionLabel(
			query.search,
			chips.map((c) => c.label)
		);
	}

	function querySelection(): SeedSelection {
		const {
			page: _p,
			size: _z,
			sort: _s,
			direction: _d,
			...filter
		} = compiled(query, 'path', 1, 1, 1);
		return {
			dimension: SurfaceDimension.ENDPOINTS,
			query: { filter, scan_ids: scanId ? [scanId] : [] }
		};
	}

	async function rescanAllMatching() {
		if (rescanBusy) return;
		rescanBusy = true;
		await startRescan(projectId, querySelection(), 'host', 'hosts');
		rescanBusy = false;
	}

	function openRescanAllOptions() {
		rescanOptionsFor = querySelection();
	}

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
		const filter = compiled(
			query,
			table.sort.key,
			table.sort.dir,
			table.pageIndex + 1,
			table.pageSize
		);
		const sig = JSON.stringify({ ...filter, page: 1 });
		if (sig !== lastSig && table.pageIndex !== 0 && !pendingSelect) {
			lastSig = sig;
			table.pageIndex = 0;
			return;
		}
		lastSig = sig;
		const current = table.searchRequest.begin();
		table.loading = true;
		try {
			const res = await endpointsApi.search(projectId, scanId, filter);
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

	let treeFilter = $derived(compiled(query, table.sort.key, table.sort.dir, 1, 1));
	let treeSig = $derived(JSON.stringify(treeFilter) + (isMerged ? '|m' : '|h'));
	let loadedTreeSig = '';

	async function loadTree() {
		if (!ready || !isTree) return;
		const current = treeReq.begin();
		loadedTreeSig = treeSig;
		treeLoading = true;
		try {
			const res = await endpointsApi.tree(
				projectId,
				scanId,
				isMerged ? 'merged' : 'host',
				treeFilter
			);
			if (current()) tree = res;
		} catch {
			if (current()) {
				tree = null;
				loadedTreeSig = '';
			}
		} finally {
			if (current()) treeLoading = false;
		}
	}

	let hostsFilter = $derived({
		...compiled({ ...query, host: '', dir: '' }, hostSort.key, hostSort.dir, 1, 1),
		hide_root_only: hideRootOnly,
		page: hostPage,
		size: RESULTS_PAGE_SIZE
	});
	let hostsSig = $derived(JSON.stringify(hostsFilter));
	let loadedHostsSig = '';

	async function loadHosts() {
		if (!ready || view !== 'hosts') return;
		const current = hostsReq.begin();
		loadedHostsSig = hostsSig;
		hostsLoading = true;
		try {
			const res = await endpointsApi.treeHosts(projectId, scanId, hostsFilter);
			if (!current()) return;
			hosts = res;
			if (pendingHost) {
				const pick = pendingHost === 'first' ? res.items[0] : res.items.at(-1);
				pendingHost = null;
				if (pick) enterHost(pick.name);
			}
		} catch {
			if (current()) {
				hosts = null;
				loadedHostsSig = '';
			}
		} finally {
			if (current()) hostsLoading = false;
		}
	}

	let briefSig = $derived(`${query.host}|${hideStatic}|${scanId}|${projectId}`);
	let loadedBriefSig = '';

	async function loadBrief() {
		if (!ready || !inHost) return;
		const current = briefReq.begin();
		loadedBriefSig = briefSig;
		briefLoading = true;
		try {
			const res = await endpointsApi.hostBrief(projectId, scanId, query.host, hideStatic);
			if (current()) brief = res;
		} catch {
			if (current()) {
				brief = null;
				loadedBriefSig = '';
			}
		} finally {
			if (current()) briefLoading = false;
		}
	}

	// a new query starts the host list over at page one
	$effect(() => {
		void treeSig;
		void hideRootOnly;
		untrack(() => (hostPage = 1));
	});

	let exportFilters = $derived(
		compiled(query, table.sort.key, table.sort.dir, 1, 1) as unknown as Record<string, unknown>
	);
	const selection = new RowSelection<Endpoint>();
	let checkedCount = $derived(selection.countOn(table.items));
	let selectAllChecked = $derived(selectAllState(checkedCount, table.items.length));

	function toggleCheck(e: Endpoint) {
		selection.toggle(e);
	}

	function toggleSelectAll() {
		selection.toggleAll(table.items);
	}

	async function selectBranch(node: TreeNode) {
		try {
			const { rows, capped } = await collectRows(
				{ projectId, scanId, filter: treeFilter, merged: isMerged },
				node
			);
			for (const row of rows) if (!selection.has(row.id)) selection.toggle(row);
			toast.success(
				capped
					? `First ${rows.length.toLocaleString()} endpoints selected`
					: `${rows.length.toLocaleString()} ${rows.length === 1 ? 'endpoint' : 'endpoints'} selected`
			);
		} catch {
			toast.error('Branch not selected.');
		}
	}
	let leadFilter = $derived(compiled({ ...query, search: '' }, 'path', 1, 1, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: treeFilter.q });
	let groupSig = $derived(groups.by ? JSON.stringify(leadFilterWithQuery) + groups.by : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await endpointsApi.leads(projectId, scanId, leadFilter);
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
			table.facets = await endpointsApi.facets(projectId, scanId);
			onScanTotal?.(table.facets.total);
			table.facetsLoaded = true;
		} catch {
			if (!table.facetsLoaded) table.facets = EMPTY_ENDPOINT_FACETS;
		}
	}

	async function loadAccount() {
		if (!ready) return;
		try {
			summary = await endpointsApi.summary(projectId, scanId);
			accountLoaded = true;
		} catch {
			summary = null;
		}
		if (projectWide) {
			coverage = [];
			return;
		}
		try {
			coverage = await endpointsApi.coverage(projectId, scanId);
		} catch {
			coverage = [];
		}
	}

	const aggregates = () => {
		loadedTreeSig = '';
		loadedHostsSig = '';
		loadedBriefSig = '';
		return Promise.all([
			loadFacets(),
			groups.reload(),
			isTree ? loadTree() : Promise.resolve(),
			view === 'hosts' ? loadHosts() : Promise.resolve(),
			inHost ? loadBrief() : Promise.resolve(),
			loadAccount()
		]);
	};
	const liveAggregates = new Throttled(aggregates);

	async function refresh(quiet = false) {
		table.refreshing = !quiet;
		try {
			if (!quiet) loadedLeadSig = '';
			const heavy = quiet ? liveAggregates.call() : aggregates();
			await Promise.all([runSearch(), heavy ?? Promise.resolve()]);
		} finally {
			if (!quiet) table.refreshing = false;
		}
	}

	const liveRefresh = new LiveRefresh(() => refresh(true));
	$effect(() => {
		liveRefresh.notify(revision, active);
	});
	onDestroy(() => {
		liveRefresh.stop();
		liveAggregates.stop();
	});

	$effect(() => {
		void JSON.stringify(query);
		void table.sort.key;
		void table.sort.dir;
		void table.pageIndex;
		void table.pageSize;
		void scanId;
		void projectId;
		void table.queryReady;
		void hideStatic;
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
		untrack(loadAccount);
	});

	$effect(() => {
		void treeSig;
		if (!seen || !isTree) return;
		if (treeSig === loadedTreeSig) return;
		return afterPause(loadTree);
	});

	$effect(() => {
		void hostsSig;
		if (!seen || view !== 'hosts') return;
		if (hostsSig === loadedHostsSig) return;
		return afterPause(loadHosts);
	});

	$effect(() => {
		void briefSig;
		if (!seen || !inHost) return;
		if (briefSig === loadedBriefSig) return;
		untrack(() => void loadBrief());
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
			set('ep_q', query.search || null);
			set('ep_host', query.host || null);
			set('ep_dir', query.dir || null);
			set('ep_group', groups.by || null);
			set('ep_view', view === 'hosts' ? null : view);
			set('ep_page', pageParam(table.pageIndex));
			set('ep_sort', sortParam(table.sort, DEFAULT_SORT));
			const qs = sp.toString();
			replaceState(qs ? `?${qs}` : location.pathname, appPage.state);
		} catch {
			// ignore
		}
	}
	$effect(() => {
		void query.search;
		void query.host;
		void query.dir;
		void groups.by;
		void table.pageIndex;
		void view;
		void table.sort.key;
		void table.sort.dir;
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
				`Verification queued for ${res.queued.toLocaleString()} ${res.queued === 1 ? 'endpoint' : 'endpoints'} under ${where}.`
			);
		} catch {
			toast.error('Verification not queued.');
		}
	}
	function proxyName(connectorId: string): string {
		const c = proxies.find((p) => p.id === connectorId);
		return c ? proxyLabel(c, catalog) : 'the proxy';
	}
	async function sendBranch(node: TreeNode, connectorId: string) {
		const filter: EndpointFilter = {
			...treeFilter,
			host: isMerged ? null : node.host,
			dir_path: node.kind === 'host' ? null : node.path,
			subtree: true
		};
		try {
			const res = await connectorsApi.sendEndpoints(connectorId, projectId, scanId, {
				filter,
				limit: SEND_CAP
			});
			toast.success(
				`${res.queued.toLocaleString()} ${res.queued === 1 ? 'request' : 'requests'} sent to ${proxyName(connectorId)}.`
			);
		} catch (e) {
			toast.error(errorMessage(e, 'Requests not sent.'));
		}
	}
	async function sendEndpoint(e: Endpoint, connectorId: string) {
		try {
			await connectorsApi.sendEndpoints(connectorId, projectId, scanId, {
				endpoint_ids: [e.id]
			});
			toast.success(`Sent to ${proxyName(connectorId)}.`);
		} catch (err) {
			toast.error(errorMessage(err, 'Request not sent.'));
		}
	}
	let branchScope = $derived({ projectId, scanId, filter: treeFilter, merged: isMerged });

	function reveal(e: Endpoint) {
		drawerOpen = false;
		goneLens = false;
		view = 'hosts';
		openKeys = [];
		setQuery({ ...query, host: e.host, dir: '', search: exactToken('path', e.path) });
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
		if (atEstate) {
			hostSort = flipSort(hostSort, key, -1);
			return;
		}
		table.toggleSort(key);
	}
	function toggleCol(key: string) {
		const next = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
		if (atEstate) hostColumnsPref = next;
		else if (isTree) outlineColumnsPref = next;
		else listColumnsPref = next;
	}
	let goneFilter = $derived(
		compiled(query, table.sort.key, table.sort.dir, goneIndex + 1, table.pageSize)
	);
	let goneSig = $derived(JSON.stringify(goneFilter));
	let loadedGoneSig = '';

	async function loadGone() {
		if (!ready) return;
		const current = goneReq.begin();
		loadedGoneSig = goneSig;
		goneLoading = true;
		try {
			const res = await endpointsApi.gone(projectId, scanId, goneFilter);
			if (current()) gonePage = res;
		} catch {
			if (current()) {
				gonePage = null;
				loadedGoneSig = '';
			}
		} finally {
			if (current()) goneLoading = false;
		}
	}

	$effect(() => {
		void goneSig;
		if (!seen || !goneLens) return;
		if (goneSig === loadedGoneSig) return;
		return afterPause(loadGone);
	});

	$effect(() => {
		void query;
		void table.sort.key;
		untrack(() => (goneIndex = 0));
	});

	function openGone(e: Endpoint) {
		selectedScanId = gonePage?.previous_scan_id ?? scanId;
		selected = e;
		drawerOpen = true;
	}

	function setHideStatic(value: boolean) {
		hideStaticPref = { ...hideStaticPref, [view]: value };
		table.pageIndex = 0;
	}
	function setQuery(q: EndpointQuery) {
		query = q;
		table.pageIndex = 0;
	}
	function setView(v: EndpointView) {
		view = v;
		if (v !== 'hosts') openKeys = [];
	}
	function setClassTab(key: string) {
		setQuery({ ...query, endpointClass: key === 'all' ? '' : key });
	}
	function drillGroup(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		groups.by = '';
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
		onTab?.(WEB.tab, filter);
	}

	function enterHost(host: string, chip?: FolderChip) {
		openKeys = chip && chip.path !== '/' ? [`${host}${chip.path}`] : [];
		view = 'hosts';
		hostCursor = -1;
		setQuery({
			...query,
			host,
			dir: '',
			search: hostOnlyToken(query.search, known) ? '' : query.search
		});
	}
	function leaveHost() {
		openKeys = [];
		setQuery({ ...query, host: '', dir: '' });
	}
	function stepHost(dir: -1 | 1) {
		if (!hosts) return;
		const at = hosts.items.findIndex((n) => n.name === query.host);
		if (at < 0) return;
		const next = at + dir;
		if (next >= 0 && next < hosts.items.length) {
			enterHost(hosts.items[next].name);
			return;
		}
		const pages = Math.ceil(hosts.total / hosts.size);
		if (dir === 1 && hosts.page < pages) {
			pendingHost = 'first';
			hostPage = hosts.page + 1;
		} else if (dir === -1 && hosts.page > 1) {
			pendingHost = 'last';
			hostPage = hosts.page - 1;
		}
	}
	async function searchHosts(term: string): Promise<TreeNode[]> {
		const res = await endpointsApi.treeHosts(projectId, scanId, {
			...hostsFilter,
			q: [hostsFilter.q, `host:${JSON.stringify(term)}`].filter(Boolean).join(' and '),
			page: 1
		});
		return res.items;
	}
	function acrossHosts() {
		openKeys = [];
		setQuery({ ...query, host: '', dir: '' });
		view = 'merged';
	}
	let hostRoot = $derived(tree?.nodes[0] ?? null);
	let hostStandIn = $derived(hostRoot ?? hostNode(query.host));

	function scrollCursor() {
		document
			.querySelector(`[data-endpoint-row-index="${cursor}"]`)
			?.scrollIntoView({ block: 'nearest' });
	}
	function scrollHostCursor() {
		document
			.querySelector(`[data-host-row-index="${hostCursor}"]`)
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
		if (typing || drawerOpen) return;
		if (inHost) {
			if (e.key === '[') {
				e.preventDefault();
				stepHost(-1);
			} else if (e.key === ']') {
				e.preventDefault();
				stepHost(1);
			} else if (e.key === 'Backspace') {
				e.preventDefault();
				leaveHost();
			}
			return;
		}
		if (atEstate) {
			const rows = hosts?.items ?? [];
			if (!rows.length) return;
			if (e.key === 'j' || e.key === 'ArrowDown') {
				e.preventDefault();
				hostCursor = Math.min(hostCursor + 1, rows.length - 1);
				scrollHostCursor();
			} else if (e.key === 'k' || e.key === 'ArrowUp') {
				e.preventDefault();
				hostCursor = Math.max(hostCursor - 1, 0);
				scrollHostCursor();
			} else if (
				(e.key === 'Enter' || e.key === 'ArrowRight') &&
				hostCursor >= 0 &&
				rows[hostCursor]
			) {
				e.preventDefault();
				enterHost(rows[hostCursor].name);
			} else if (e.key === 'Escape') {
				hostCursor = -1;
			}
			return;
		}
		if (!isList || !table.items.length) return;
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

	let barH = $state(0);
	let scrollRef = $state<HTMLElement | null>(null);
</script>

<svelte:window onkeydown={onKey} />

<div
	class="relative z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2"
	bind:this={headEl}
	bind:clientHeight={barH}
>
	<QueryBar
		bind:this={queryBar}
		bind:ref={searchRef}
		store={endpointQuerySchema}
		recentsKey={SURFACE[SurfaceDimension.ENDPOINTS].recentsKey}
		hint={inHost ? 'path:/api or is:param' : 'is:param and is:live'}
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
	{#if isTree && !goneLens && crumbs.length}
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
	{#if table.queryError}
		<EmptyState
			icon={SearchX}
			title="Query did not run"
			description={table.queryError.message}
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{:else if filtered || (hideStatic && scanTotal > 0)}
		<EmptyState
			icon={SearchX}
			title={atEstate ? 'No host matches' : 'No endpoints match'}
			description={hideStatic && !filtered
				? 'All matching endpoints are static files.'
				: 'Widen the search or remove a filter.'}
			class="rounded-none border-0 bg-transparent py-16"
		>
			{#if filtered}
				<Button
					size="sm"
					variant="outline"
					class="gap-2"
					onclick={() => setQuery({ ...emptyEndpointQuery(), host: query.host })}
				>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			{:else}
				<Button size="sm" variant="outline" onclick={() => setHideStatic(false)}>
					Show static files
				</Button>
			{/if}
		</EmptyState>
	{:else if atEstate && hideRootOnly && (hosts?.root_only ?? 0) > 0}
		<EmptyState
			icon={Waypoints}
			title="Root pages only"
			description="Every host has only its root page."
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button size="sm" variant="outline" onclick={() => (hideRootOnly = false)}>
				Show root-only hosts
			</Button>
		</EmptyState>
	{:else}
		<EmptyState
			icon={Waypoints}
			title="No endpoints in this scan"
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{/if}
{/snippet}

{#snippet retryState()}
	<EmptyState
		icon={TriangleAlert}
		title="Endpoints not loaded"
		class="rounded-none border-0 bg-transparent py-16"
	>
		<Button variant="outline" class="gap-2" onclick={() => refresh()}>
			<RefreshCw class="h-4 w-4" /> Retry
		</Button>
	</EmptyState>
{/snippet}

<Card.Root class="gap-0 overflow-clip rounded-t-none border-t-0 py-0">
	<div class="border-b px-2">
		<CountTabs tabs={classTabs} value={classTab} counts={classCounts} onChange={setClassTab} />
	</div>

	<SelectionBar
		noun="host"
		nounPlural="hosts"
		total={table.total}
		totalCapped={table.totalCapped}
		maxAssets={rechecks.schema?.max_assets ?? 0}
		queryActive={Boolean(query.search.trim()) || chips.length > 0 || Boolean(query.host)}
		query={queryLabel()}
		busy={rescanBusy}
		onRescanAll={rescanAllMatching}
		onRescanAllOptions={openRescanAllOptions}
	/>

	{#if inHost}
		<HostCrumbs
			host={query.host}
			ranked={hosts?.items ?? []}
			offset={hosts ? (hosts.page - 1) * hosts.size : 0}
			total={hosts?.total ?? 0}
			onLeave={leaveHost}
			onSwitch={(h) => enterHost(h)}
			onStep={stepHost}
			search={searchHosts}
		/>
		<HostHeader
			host={query.host}
			{brief}
			loading={briefLoading}
			connectors={proxies}
			{catalog}
			onPivot={showInList}
			onNew={() => setQuery({ ...query, newOnly: true })}
			onFindings={onTab ? () => onTab(VULN.tab, exactToken('host', query.host)) : undefined}
			onWebAsset={onTab ? () => showHost(exactToken('host', query.host)) : undefined}
			onCopy={() => copyBranch(branchScope, hostStandIn)}
			onWordlist={() => copyWordlist(branchScope, hostStandIn)}
			onVerify={projectWide ? undefined : () => verifyBranch(hostStandIn)}
			onSend={proxies.length ? (id) => sendBranch(hostStandIn, id) : undefined}
			onAcross={acrossHosts}
		/>
	{:else if accountLoaded}
		<CoverageStrip
			{coverage}
			{summary}
			{projectWide}
			hidden={hideStatic ? staticTotal : 0}
			rootOnly={atEstate && hideRootOnly ? (hosts?.root_only ?? 0) : 0}
			onShowStatic={() => setHideStatic(false)}
			onShowRootOnly={() => (hideRootOnly = false)}
			onShowNew={() => setQuery({ ...query, newOnly: true })}
			onShowGone={projectWide ? undefined : () => (goneLens = true)}
		/>
	{/if}

	<FilterBar
		{query}
		facets={table.facets}
		onQuery={setQuery}
		dimensions={endpointQuerySchema.schema.group_dimensions}
		columns={columnOptions}
		{visible}
		onToggleColumn={toggleCol}
		density={table.density}
		onDensity={(d) => (table.density = d)}
		sorts={atEstate ? HOST_SORTS : ENDPOINT_SORTS}
		sortKey={atEstate ? hostSort.key : table.sort.key}
		sortDir={atEstate ? hostSort.dir : table.sort.dir}
		onSort={toggleSort}
		refreshing={table.refreshing}
		{projectId}
		{scanId}
		{exportFilters}
		onRefresh={refresh}
		groupBy={groups.by}
		onGroupBy={(key) => (groups.by = key)}
		{view}
		onView={setView}
		{inHost}
		{hideStatic}
		onHideStatic={setHideStatic}
		{hideRootOnly}
		onHideRootOnly={(v) => (hideRootOnly = v)}
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
				onclick={() =>
					setQuery({
						...emptyEndpointQuery(),
						search: query.search,
						host: inHost ? query.host : ''
					})}
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
					not found in this scan.
				</span>
			{:else}
				<Skeleton class="h-3.5 w-52" />
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
			<ScrollArea orientation="horizontal">
				<TableSkeleton
					lead={ENDPOINT_LEAD_COLUMNS}
					columns={ENDPOINT_COLUMNS.filter((c) =>
						(listColumnsPref ?? DEFAULT_VISIBLE_ENDPOINT_COLUMNS).includes(c.key)
					)}
					density={table.density}
					rows={5}
				/>
			</ScrollArea>
		{:else if gonePage && gonePage.items.length === 0}
			<EmptyState
				icon={History}
				title="No retired endpoints"
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if gonePage}
			<ListHeader
				sticky
				top={barH}
				follow={scrollRef}
				lead={ENDPOINT_LEAD_COLUMNS}
				columns={ENDPOINT_COLUMNS.filter((c) =>
					(listColumnsPref ?? DEFAULT_VISIBLE_ENDPOINT_COLUMNS).includes(c.key)
				)}
				sortKey={table.sort.key}
				sortDir={table.sort.dir}
				onSort={toggleSort}
			/>
			<ScrollArea orientation="horizontal" bind:ref={scrollRef}>
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
			{#if gonePage.total > table.pageSize}
				<ResultsPagination
					total={gonePage.total}
					capped={gonePage.total_capped}
					page={goneIndex}
					pageSize={table.pageSize}
					noun={EP.noun}
					plural={EP.nounPlural}
					onPage={(p) => (goneIndex = p)}
				/>
			{/if}
		{/if}
	{:else if atEstate}
		{#if hosts?.error}
			<EmptyState
				icon={SearchX}
				title="Query did not run"
				description={hosts.error.message}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if table.errored && !hosts}
			{@render retryState()}
		{:else if !hostsLoading && hosts && hosts.items.length === 0}
			{@render emptyStates()}
		{:else}
			<HostTable
				page={hosts}
				loading={hostsLoading}
				searching={filtered}
				{terms}
				columns={shownColumns}
				pad={rowPad}
				cursor={hostCursor}
				sortKey={hostSort.key}
				sortDir={hostSort.dir}
				connectors={proxies}
				{catalog}
				onSort={toggleSort}
				onPage={(p) => (hostPage = p)}
				onEnter={(h) => enterHost(h)}
				onEnterFolder={(h, chip) => enterHost(h, chip)}
				onCopy={(node) => copyBranch(branchScope, node)}
				onWordlist={(node) => copyWordlist(branchScope, node)}
				onList={(node) => showInList(node.query)}
				onVerify={projectWide ? undefined : verifyBranch}
				onSend={proxies.length ? sendBranch : undefined}
				onShowRootOnly={() => (hideRootOnly = false)}
			/>
		{/if}
	{:else if isTree}
		{#if tree?.error}
			<EmptyState
				icon={SearchX}
				title="Query did not run"
				description={tree.error.message}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if table.errored && !tree}
			{@render retryState()}
		{:else if !treeLoading && tree && tree.nodes.length === 0}
			{@render emptyStates()}
		{:else}
			<Outline
				bind:this={outline}
				{projectId}
				{scanId}
				{tree}
				loading={treeLoading}
				merged={isMerged}
				rooted={inHost}
				{openKeys}
				filter={treeFilter}
				{terms}
				columns={shownColumns}
				pad={rowPad}
				{active}
				paused={drawerOpen}
				searching={filtered}
				selectedId={drawerOpen ? (selected?.id ?? null) : null}
				sortKey={table.sort.key}
				sortDir={table.sort.dir}
				connectors={proxies}
				{catalog}
				onSort={toggleSort}
				onOpen={open}
				onFilter={applyDsl}
				onShowInList={showInList}
				onHost={pivotHost}
				onExpandedChange={(n) => (expandedCount = n)}
				onVerify={projectWide ? undefined : verifyBranch}
				onSend={proxies.length ? sendBranch : undefined}
				checked={(id) => selection.has(id)}
				onCheck={toggleCheck}
				onSelectBranch={selectBranch}
				edgeEl={headEl}
				onCrumbs={(c) => (crumbs = c)}
			/>
		{/if}
	{:else}
		<div class="flex min-w-0 flex-1 flex-col">
			{#if table.loading && table.items.length === 0 && !groups.by}
				<ScrollArea orientation="horizontal">
					<TableSkeleton
						lead={ENDPOINT_LEAD_COLUMNS}
						columns={shownColumns}
						density={table.density}
						selectable
					/>
				</ScrollArea>
			{:else if table.errored}
				{@render retryState()}
			{:else if groups.by}
				<GroupList
					set={groups.value}
					failed={groups.failed}
					onRetry={groups.reload}
					dimensions={endpointQuerySchema.schema.group_dimensions}
					noun={endpointQuerySchema.schema.noun}
					nounPlural={endpointQuerySchema.schema.noun_plural}
					loading={groups.loading}
					onPick={drillGroup}
				/>
			{:else if table.items.length === 0}
				{@render emptyStates()}
			{:else}
				<ListHeader
					sticky
					top={barH}
					follow={scrollRef}
					lead={ENDPOINT_LEAD_COLUMNS}
					columns={shownColumns}
					sortKey={table.sort.key}
					sortDir={table.sort.dir}
					{selectAllChecked}
					selectAllLabel="Select every endpoint on this page"
					onSelectAll={toggleSelectAll}
					onSort={toggleSort}
				/>
				<ScrollArea orientation="horizontal" bind:ref={scrollRef}>
					<div
						class="divide-y divide-border/50 transition-opacity {table.loading ? 'opacity-60' : ''}"
					>
						{#each table.items as e, i (e.id)}
							<div data-endpoint-row-index={i}>
								<EndpointRow
									endpoint={e}
									{terms}
									columns={visible}
									active={drawerOpen && selected?.id === e.id}
									focused={cursor === i}
									pad={rowPad}
									checked={selection.has(e.id)}
									onCheck={toggleCheck}
									onOpen={open}
									onFilter={applyDsl}
								/>
							</div>
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
					noun={EP.noun}
					plural={EP.nounPlural}
					onPage={(p) => (table.pageIndex = p)}
					onPageSize={(s) => table.setPageSize(s)}
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
	index={isList ? selectedIndex : -1}
	pageOffset={table.pageIndex * table.pageSize}
	total={isList ? table.total : 0}
	onStep={step}
	onFilter={applyDsl}
	onHost={showHost}
	onReveal={reveal}
	connectors={proxies}
	{catalog}
	onSend={proxies.length ? sendEndpoint : undefined}
/>

<RowSelectionBar
	count={selection.size}
	dimension={SurfaceDimension.ENDPOINTS}
	{projectId}
	{scanId}
	copy={[
		{ label: 'URLs', values: () => selection.rows().map((e) => e.url) },
		{ label: 'paths', values: () => [...new Set(selection.rows().map((e) => e.path))] },
		{ label: 'web assets', values: () => [...new Set(selection.rows().map((e) => e.host))] }
	]}
	ids={() => selection.ids()}
	{exportFilters}
	onDeleted={() => {
		selection.clear();
		void refresh();
	}}
	onClear={() => selection.clear()}
/>

<LaunchDialog
	open={rescanOptionsFor !== null}
	rescan={rescanOptionsFor
		? {
				selection: rescanOptionsFor,
				dimension: SurfaceDimension.ENDPOINTS,
				targetType,
				seedKind: seedKindFor(rechecks.schema, SurfaceDimension.ENDPOINTS),
				assets: [],
				queryLabel: queryLabel()
			}
		: null}
	onClose={() => (rescanOptionsFor = null)}
/>
