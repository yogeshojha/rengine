<script lang="ts">
	import { page as appPage } from '$app/state';
	import { onDestroy, untrack } from 'svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { seedKindFor, selectionLabel } from '$lib/utilities/rechecks';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { startRescan } from '$lib/utilities/rechecks';
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import SquareKanban from '@lucide/svelte/icons/square-kanban';
	import Tags from '@lucide/svelte/icons/tags';
	import SearchX from '@lucide/svelte/icons/search-x';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import Keyboard from '@lucide/svelte/icons/keyboard';

	import * as Card from '$lib/components/ui/card';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Kbd } from '$lib/components/ui/kbd';
	import Hint from '$lib/components/hint.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import CountTabs from '@/components/count-tabs.svelte';
	import EmptyState from '@/components/empty-state.svelte';

	import QueryBar from './query-bar/query-bar.svelte';
	import GroupList from './table/group-list.svelte';
	import ListHeader from './table/list-header.svelte';
	import {
		readPref,
		rowPadding,
		selectAllState,
		writePref,
		type TableColumn
	} from './table/columns';
	import ResultsPagination from './table/results-pagination.svelte';
	import CoverageStrip from './vulnerabilities/coverage-strip.svelte';
	import FilterBar from './vulnerabilities/filter-bar.svelte';
	import IssueInstances from './vulnerabilities/issue-instances.svelte';
	import SelectionBar from './table/selection-bar.svelte';
	import RowSelectionBar from './table/row-selection-bar.svelte';
	import RescanAction from './table/rescan-action.svelte';
	import FileIssuesDialog from '$lib/components/issue-trackers/file-issues-dialog.svelte';
	import type { SeedPick, SeedSelection } from '$lib/types/recheck';
	import IssueRow from './vulnerabilities/issue-row.svelte';
	import FindingRow from './vulnerabilities/findings/finding-row.svelte';
	import FindingsStrip from './vulnerabilities/findings/findings-strip.svelte';
	import { FCOL } from './vulnerabilities/findings/columns';
	import { forgetPeeks } from './vulnerabilities/findings/peek';
	import {
		BRIEF_TABS,
		FINDING_COLUMNS,
		FINDING_COLUMN_LABELS,
		findingPrefs,
		type FindingColumn
	} from './vulnerabilities/findings/prefs.svelte';
	import VulnerabilityDetailSheet from './vulnerability-detail-sheet.svelte';
	import { ISSUE_COLUMNS, ISSUE_LEAD_COLUMNS, VULN_LEAD_COLUMNS } from './vulnerabilities/columns';

	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import { vulnQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import {
		SUPPRESSED_STATES,
		VULN_STATE_LABELS,
		VULN_STATE_KEYS,
		VulnState
	} from '$lib/config/vulnerabilities';
	import {
		hideLabel,
		excludeToken,
		appendTokens,
		appendToken,
		exactToken,
		type Facet
	} from '$lib/utilities/scan-insights';
	import {
		compileVulnQuery,
		emptyVulnQuery,
		facetsAsRecord,
		vulnActiveFacetCount,
		vulnQueryChips,
		DEFAULT_VULN_VIEW,
		EMPTY_VULN_FACETS,
		ISSUE_SORTS,
		VULN_SORTS,
		VULN_VIEWS,
		type CoverageRead,
		type IssueRead,
		type ScanVulnerabilities,
		type VulnFacetSet,
		type VulnQuery,
		type VulnView,
		type VulnerabilityRead
	} from '$lib/utilities/vulns';
	import type { QueryError, QueryGroups, QueryLeads } from '$lib/types/asset-query';
	import { locationTokensFromUrl } from '$lib/utilities/endpoints';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { afterPause } from '$lib/utilities/debounce';
	import { UrlSync, onPopSearch } from '$lib/utilities/url-history.svelte';
	import { LiveRefresh } from '$lib/utilities/live-results';

	interface Props {
		scanId: string;
		projectWide?: boolean;
		targetType?: string;
		active?: boolean;
		revision?: number;
		onTab?: (tab: ResultTab, filter?: string) => void;
		onScanTotal?: (total: number) => void;
		query?: VulnQuery;
	}

	let {
		scanId,
		projectWide = false,
		targetType = '',
		active = true,
		revision = 0,
		onTab,
		onScanTotal,
		query = $bindable({
			...emptyVulnQuery(),
			search: appPage.url.searchParams.get('vuln_q') ?? ''
		})
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const EP = SURFACE[SurfaceDimension.ENDPOINTS];

	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let ready = $derived(projectWide ? Boolean(projectId) : Boolean(scanId));

	const DEFAULT_SORT = { key: 'risk', dir: -1 as const };
	const INSTANCE_PAGE = 100;
	const VIEW_KEYS = new Set<string>(VULN_VIEWS.map((v) => v.key));

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('vuln_sort')?.split(':') ?? [];
	const initialView = initial.get('vuln_view');

	let view = $state<VulnView>(
		initialView && VIEW_KEYS.has(initialView)
			? (initialView as VulnView)
			: readPref<VulnView>(STORAGE_KEYS.vulnsView, DEFAULT_VULN_VIEW)
	);
	let density = $state<string>(readPref(STORAGE_KEYS.vulnsDensity, 'cozy'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.vulnsPageSize, RESULTS_PAGE_SIZE));
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('vuln_page') ?? 1) - 1));

	let items = $state<VulnerabilityRead[]>([]);
	let issues = $state<IssueRead[]>([]);
	let total = $state(0);
	let totalCapped = $state(false);
	let queryError = $state<QueryError | null>(null);
	let queryReady = $state(true);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let facets = $state<VulnFacetSet>(EMPTY_VULN_FACETS);
	let facetsLoaded = $state(false);
	let coverage = $state<CoverageRead[]>([]);
	let overview = $state<ScanVulnerabilities | null>(null);
	const expanded = new SvelteSet<string>();
	let shortcutsOpen = $state(false);
	let leadSet = $state<QueryLeads | null>(null);
	let groupBy = $state<string>(initial.get('vuln_group') ?? '');
	let groupSet = $state<QueryGroups | null>(null);
	let groupFailed = $state(false);
	let groupLoading = $state(false);
	let groupReq = 0;

	let expandedId = $state<string | null>(null);
	let instancesSig = '';
	let pendingVuln = initial.get('vuln');
	let instances = $state<VulnerabilityRead[]>([]);
	let instancesTotal = $state(0);
	let instancesLoading = $state(false);
	let instanceLimit = $state(INSTANCE_PAGE);
	let instanceReq = 0;

	let selected = $state<VulnerabilityRead | null>(null);
	let drawerOpen = $state(false);
	let cursor = $state(-1);
	let searchRef = $state<HTMLInputElement | null>(null);
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let pendingSelect: 'first' | 'last' | null = null;
	let bulkBusy = $state(false);
	const checkedIds = new SvelteSet<string>();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let isIssues = $derived(view === 'issues');
	let rowCount = $derived(isIssues ? issues.length : items.length);
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let sheetItems = $derived(isIssues ? instances : items);
	let selectedIndex = $derived(selected ? sheetItems.findIndex((v) => v.id === selected?.id) : -1);
	let sheetTotal = $derived(isIssues ? instancesTotal : total);
	let findingColumns = $derived<TableColumn[]>(
		FINDING_COLUMNS.map((key) => ({ key, label: FINDING_COLUMN_LABELS[key], width: '' }))
	);
	let findingVisible = $derived(FINDING_COLUMNS.filter((c) => findingPrefs.shows(c)));
	let checkedCount = $derived(
		isIssues
			? issues.filter((i) => checkedIds.has(i.template_id)).length
			: items.filter((v) => checkedIds.has(v.id)).length
	);
	let selectAllChecked = $derived(selectAllState(checkedCount, rowCount));
	let filtered = $derived(vulnActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(vulnQueryChips(query, facets));
	let rowPad = $derived(rowPadding(density));
	let term = $derived(query.search.trim().includes(':') ? '' : query.search.trim());
	let severityCounts = $derived.by(() => {
		if (isIssues) {
			if (!facetsLoaded) return null;
			return Object.fromEntries(facets.issue_severity.map((f) => [f.name, f.count]));
		}
		if (!overview) return null;
		return Object.fromEntries(overview.by_severity.map((c) => [c.severity, c.count]));
	});
	const REVIEW_TABS = [
		{ key: 'active', label: 'Active' },
		{ key: VulnState.OPEN, label: 'Not reviewed' },
		{ key: VulnState.CONFIRMED, label: VULN_STATE_LABELS[VulnState.CONFIRMED] },
		{ key: VulnState.FALSE_POSITIVE, label: VULN_STATE_LABELS[VulnState.FALSE_POSITIVE] },
		{ key: VulnState.ACCEPTED, label: VULN_STATE_LABELS[VulnState.ACCEPTED] },
		{ key: 'all', label: 'All' }
	];
	let reviewTab = $derived(
		query.states.length === 1
			? query.states[0]
			: query.states.length === 0
				? query.includeSuppressed
					? 'all'
					: 'active'
				: ''
	);
	let reviewCounts = $derived.by(() => {
		if (isIssues || !facetsLoaded) return null;
		const m: Record<string, number> = {};
		for (const f of facets.state) m[f.name] = f.count;
		m.all = facets.state.reduce((n, f) => n + f.count, 0);
		m.active = facets.state
			.filter((f) => !SUPPRESSED_STATES.includes(f.name))
			.reduce((n, f) => n + f.count, 0);
		return m;
	});
	let coverageLoaded = $state(false);
	let ranScan = $derived(coverage.some((c) => c.status !== 'skipped'));
	let noun = $derived(isIssues ? 'weakness' : VULN.noun);
	let nounPlural = $derived(isIssues ? 'weaknesses' : VULN.nounPlural);

	$effect(() => writePref(STORAGE_KEYS.vulnsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.vulnsPageSize, pageSize));
	$effect(() => writePref(STORAGE_KEYS.vulnsView, view));
	$effect(() => {
		const ids = new Set(isIssues ? issues.map((i) => i.template_id) : items.map((v) => v.id));
		for (const id of checkedIds) if (!ids.has(id)) checkedIds.delete(id);
		for (const id of expanded) if (!ids.has(id)) expanded.delete(id);
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
		const filter = compileVulnQuery(query, sort.key, sort.dir, pageIndex * pageSize, pageSize);
		const sig = JSON.stringify({ ...filter, offset: 0, view });
		if (sig !== lastSig && pageIndex !== 0 && !pendingSelect) {
			lastSig = sig;
			pageIndex = 0;
			return;
		}
		lastSig = sig;
		const my = ++reqId;
		loading = true;
		try {
			if (view === 'issues') {
				const res = await vulnerabilitiesApi.issues(projectId, scanId, filter);
				if (my !== reqId) return;
				issues = res.items;
				total = res.total;
				totalCapped = res.total_capped;
				queryError = res.error;
				if (expandedId && !issues.some((i) => i.template_id === expandedId)) collapse();
				else if (expandedId && instancesSig !== JSON.stringify(query))
					void loadInstances(expandedId, instanceLimit);
				if (pendingVuln) {
					const id = pendingVuln;
					pendingVuln = null;
					void openById(id);
				}
			} else {
				const res = await vulnerabilitiesApi.search(projectId, scanId, filter);
				if (my !== reqId) return;
				items = res.items;
				total = res.total;
				totalCapped = res.total_capped;
				queryError = res.error;
				if (pendingVuln) {
					const id = pendingVuln;
					pendingVuln = null;
					const hit = items.find((v) => v.id === id);
					if (hit) open(hit);
					else void openById(id);
				}
				if (pendingSelect) {
					selected = pendingSelect === 'first' ? (items[0] ?? null) : (items.at(-1) ?? null);
					pendingSelect = null;
				}
			}
			errored = false;
			if (!queryError && filter.q) queryBar?.remember(filter.q);
		} catch {
			if (my === reqId) {
				items = [];
				issues = [];
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

	let exportFilters = $derived(
		compileVulnQuery(query, sort.key, sort.dir, 0, 1) as unknown as Record<string, unknown>
	);
	let leadFilter = $derived(compileVulnQuery({ ...query, search: '' }, 'risk', -1, 0, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groupBy ? JSON.stringify(leadFilterWithQuery) + groupBy : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await vulnerabilitiesApi.leads(projectId, scanId, leadFilter);
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
			const res = await vulnerabilitiesApi.groups(projectId, scanId, groupBy, leadFilterWithQuery);
			if (my === groupReq) {
				groupSet = res;
				groupFailed = false;
			}
		} catch {
			if (my === groupReq) {
				groupSet = null;
				groupFailed = true;
			}
		} finally {
			if (my === groupReq) groupLoading = false;
		}
	}

	async function loadFacets() {
		if (!ready) return;
		try {
			facets = await vulnerabilitiesApi.facets(projectId, scanId);
			onScanTotal?.(facets.severity.reduce((n, f) => n + f.count, 0));
			facetsLoaded = true;
		} catch {
			if (!facetsLoaded) facets = EMPTY_VULN_FACETS;
		}
	}

	async function loadOverview() {
		if (!ready) return;
		try {
			overview = await vulnerabilitiesApi.overview(projectId, scanId);
		} catch {
			overview = null;
		}
	}

	async function loadCoverage() {
		if (!ready) return;
		try {
			coverage = await vulnerabilitiesApi.coverage(projectId, scanId);
			coverageLoaded = true;
		} catch {
			coverage = [];
		}
	}

	async function loadInstances(templateId: string, limit: number) {
		const my = ++instanceReq;
		instancesSig = JSON.stringify(query);
		instancesLoading = true;
		try {
			const filter = compileVulnQuery({ ...query, templates: [templateId] }, 'host', 1, 0, limit);
			const res = await vulnerabilitiesApi.search(projectId, scanId, filter);
			if (my !== instanceReq) return;
			instances = res.items;
			instancesTotal = res.total;
		} catch {
			if (my === instanceReq) {
				instances = [];
				instancesTotal = 0;
			}
		} finally {
			if (my === instanceReq) instancesLoading = false;
		}
	}

	function collapse() {
		expandedId = null;
		instances = [];
		instancesTotal = 0;
		instanceLimit = INSTANCE_PAGE;
	}

	function toggleIssue(issue: IssueRead) {
		if (expandedId === issue.template_id) {
			collapse();
			return;
		}
		expandedId = issue.template_id;
		instances = [];
		instancesTotal = issue.findings;
		instanceLimit = INSTANCE_PAGE;
		void loadInstances(issue.template_id, instanceLimit);
	}

	function moreInstances() {
		if (!expandedId) return;
		instanceLimit += INSTANCE_PAGE;
		void loadInstances(expandedId, instanceLimit);
	}

	async function refresh(quiet = false) {
		refreshing = !quiet;
		try {
			if (!quiet) loadedLeadSig = '';
			forgetPeeks();
			await Promise.all([runSearch(), loadFacets(), loadCoverage(), loadGroups(), loadOverview()]);
			if (expandedId) await loadInstances(expandedId, instanceLimit);
		} finally {
			if (!quiet) refreshing = false;
		}
	}

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
		void scanId;
		void projectId;
		void queryReady;
		void view;
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
		untrack(() => {
			void loadFacets();
			void loadCoverage();
			void loadOverview();
		});
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
		return afterPause(loadGroups);
	});

	function syncUrl() {
		try {
			const sp = new SvelteURLSearchParams(location.search);
			const set = (k: string, v: string | null) => (v ? sp.set(k, v) : sp.delete(k));
			set('vuln_q', query.search || null);
			set('vuln_group', groupBy || null);
			set('vuln_view', view !== DEFAULT_VULN_VIEW ? view : null);
			set('vuln_page', pageIndex > 0 ? String(pageIndex + 1) : null);
			set('vuln', drawerOpen && selected ? selected.id : null);
			set(
				'vuln_sort',
				sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir
					? `${sort.key}:${sort.dir === 1 ? 'asc' : 'desc'}`
					: null
			);
			urlSync.write(sp);
		} catch {
			// ignore
		}
	}
	const urlSync = new UrlSync(['vuln_q', 'vuln_group', 'vuln_view']);

	function restoreUrl(sp: URLSearchParams) {
		const search = sp.get('vuln_q') ?? '';
		if (search !== query.search) query = { ...query, search };
		const group = sp.get('vuln_group') ?? '';
		if (group !== groupBy) groupBy = group;
		const rawView = sp.get('vuln_view');
		const nextView = rawView && VIEW_KEYS.has(rawView) ? (rawView as VulnView) : DEFAULT_VULN_VIEW;
		if (nextView !== view) view = nextView;
		const [sortKey, sortDir] = sp.get('vuln_sort')?.split(':') ?? [];
		const nextSort = sortKey
			? { key: sortKey, dir: (sortDir === 'desc' ? -1 : 1) as 1 | -1 }
			: { ...DEFAULT_SORT };
		if (nextSort.key !== sort.key || nextSort.dir !== sort.dir) sort = nextSort;
		const nextPage = Math.max(0, Number(sp.get('vuln_page') ?? 1) - 1);
		if (nextPage !== pageIndex) pageIndex = nextPage;
		if (drawerOpen && !sp.get('vuln')) drawerOpen = false;
	}
	$effect(() => onPopSearch(restoreUrl));
	$effect(() => {
		void query.search;
		void groupBy;
		void pageIndex;
		void view;
		void sort.key;
		void sort.dir;
		void drawerOpen;
		void selected?.id;
		if (!seen || !active) return;
		untrack(syncUrl);
	});

	function open(v: VulnerabilityRead) {
		selected = v;
		drawerOpen = true;
	}
	async function openById(id: string) {
		try {
			open(await vulnerabilitiesApi.detail(projectId, scanId, id));
		} catch {
			toast.error('Finding not found');
		}
	}
	function step(dir: -1 | 1) {
		const next = selectedIndex + dir;
		if (next >= 0 && next < sheetItems.length) {
			selected = sheetItems[next];
			return;
		}
		if (isIssues) return;
		if (dir === 1 && pageIndex < pageCount - 1) {
			pendingSelect = 'first';
			pageIndex += 1;
		} else if (dir === -1 && pageIndex > 0) {
			pendingSelect = 'last';
			pageIndex -= 1;
		}
	}
	function setView(next: VulnView) {
		if (next === view) return;
		view = next;
		checkedIds.clear();
		collapse();
		cursor = -1;
		pageIndex = 0;
		sort = { ...DEFAULT_SORT };
	}
	function toggleSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: 1 };
		pageIndex = 0;
	}
	function toggleCheck(id: string) {
		if (checkedIds.has(id)) checkedIds.delete(id);
		else checkedIds.add(id);
	}
	function toggleSelectAll() {
		if (checkedCount === rowCount) checkedIds.clear();
		else if (isIssues) for (const i of issues) checkedIds.add(i.template_id);
		else for (const v of items) checkedIds.add(v.id);
	}
	function toggleCol(key: string) {
		findingPrefs.toggle(key as FindingColumn);
	}
	function toggleExpand(id: string) {
		if (expanded.has(id)) expanded.delete(id);
		else expanded.add(id);
	}
	let hideOptions = $derived.by(() => {
		if (isIssues) {
			const rows = issues.filter((i) => checkedIds.has(i.template_id));
			return [
				{
					label: hideLabel(
						rows.map((i) => i.template_name),
						'checks'
					),
					tokens: () => [...checkedIds].map((id) => excludeToken('template', id))
				}
			];
		}
		const rows = items.filter((v) => checkedIds.has(v.id));
		const names = [...new Set(rows.map((v) => v.template_name))];
		const hosts = [...new Set(rows.filter((v) => v.host).map((v) => v.host ?? ''))];
		return [
			{
				label: hideLabel(names, 'checks'),
				tokens: () => [...new Set(rows.map((v) => excludeToken('template', v.template_id)))]
			},
			...(hosts.length
				? [
						{
							label: hideLabel(hosts, 'web assets'),
							tokens: () => hosts.map((host) => excludeToken('host', host))
						}
					]
				: [])
		];
	});

	function setQuery(q: VulnQuery) {
		query = q;
		pageIndex = 0;
	}
	function toggleSeverity(sev: string) {
		setQuery({
			...query,
			severities: query.severities.includes(sev)
				? query.severities.filter((s) => s !== sev)
				: [...query.severities, sev]
		});
	}
	function toggleHost(host: string) {
		setQuery({
			...query,
			hosts: query.hosts.includes(host)
				? query.hosts.filter((h) => h !== host)
				: [...query.hosts, host]
		});
	}
	function setReviewTab(key: string) {
		if (key === 'active') setQuery({ ...query, states: [], includeSuppressed: false });
		else if (key === 'all') setQuery({ ...query, states: [], includeSuppressed: true });
		else
			setQuery({
				...query,
				states: [key],
				includeSuppressed: SUPPRESSED_STATES.includes(key)
			});
	}
	function drillGroup(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		groupBy = '';
	}
	function applyDsl(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		drawerOpen = false;
	}
	function showFindings(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		setView('findings');
	}
	function showHost(filter: string) {
		drawerOpen = false;
		syncUrl();
		onTab?.(WEB.tab, filter);
	}
	function showLocation(matchedAt: string) {
		drawerOpen = false;
		setQuery({ ...emptyVulnQuery(), search: exactToken('location', matchedAt) });
		setView('findings');
	}

	function applyState(fingerprints: Set<string>, state: string, note: string | null) {
		items = items.map((item) =>
			fingerprints.has(item.fingerprint) ? { ...item, state, note } : item
		);
		instances = instances.map((item) =>
			fingerprints.has(item.fingerprint) ? { ...item, state, note } : item
		);
		if (selected && fingerprints.has(selected.fingerprint)) {
			selected = { ...selected, state, note };
		}
	}

	function afterTriage() {
		forgetPeeks();
		void loadFacets();
		void loadOverview();
		if (!query.includeSuppressed) {
			void runSearch();
			if (expandedId) void loadInstances(expandedId, instanceLimit);
		} else if (isIssues) {
			void runSearch();
		}
	}

	async function triage(v: VulnerabilityRead, state: string, note: string | null = null) {
		const previous = v.state;
		try {
			const result = await vulnerabilitiesApi.triage(
				projectId,
				v.scan_id ?? scanId,
				v.fingerprint,
				state,
				note
			);
			applyState(new Set([v.fingerprint]), result.state, result.note);
			toast.success(`Marked ${VULN_STATE_LABELS[state].toLowerCase()}`, {
				description: result.updated > 1 ? `${result.updated} observations updated.` : undefined
			});
			afterTriage();
		} catch {
			toast.error(`Finding not marked ${VULN_STATE_LABELS[state].toLowerCase()}`);
			applyState(new Set([v.fingerprint]), previous, v.note);
		}
	}

	async function triageMany(
		body: { fingerprints?: string[]; template_ids?: string[] },
		state: string,
		what: string
	) {
		bulkBusy = true;
		try {
			const result = await vulnerabilitiesApi.triageMany(projectId, scanId, { ...body, state });
			toast.success(`Marked ${what} ${VULN_STATE_LABELS[state].toLowerCase()}`, {
				description: `${result.fingerprints.toLocaleString()} ${
					result.fingerprints === 1 ? 'finding' : 'findings'
				} updated.`
			});
			if (body.fingerprints) applyState(new Set(body.fingerprints), state, null);
			checkedIds.clear();
			afterTriage();
		} catch {
			toast.error(`${what} not marked ${VULN_STATE_LABELS[state].toLowerCase()}`);
		} finally {
			bulkBusy = false;
		}
	}

	function triageIssue(issue: IssueRead, state: string) {
		void triageMany({ template_ids: [issue.template_id] }, state, issue.template_name);
	}

	function triageChecked(state: string) {
		const what = `${checkedCount} ${
			checkedCount === 1
				? isIssues
					? 'weakness'
					: 'finding'
				: isIssues
					? 'weaknesses'
					: 'findings'
		}`;
		if (isIssues) {
			void triageMany({ template_ids: [...checkedIds] }, state, what);
		} else {
			const fingerprints = items.filter((v) => checkedIds.has(v.id)).map((v) => v.fingerprint);
			void triageMany({ fingerprints }, state, what);
		}
	}

	const FILED_RECHECK_MS = 5000;
	let fileFor = $state<{ fingerprints: string[]; templateIds: string[]; bulk: boolean } | null>(
		null
	);
	const showIssue = $derived(
		findingPrefs.shows('issue') && items.some((v) => (v.tickets ?? []).length > 0)
	);
	let fileOpen = $state(false);

	function fileOne(v: VulnerabilityRead) {
		fileFor = { fingerprints: [v.fingerprint], templateIds: [], bulk: false };
		fileOpen = true;
	}

	function fileChecked() {
		fileFor = isIssues
			? { fingerprints: [], templateIds: [...checkedIds], bulk: true }
			: {
					fingerprints: items.filter((v) => checkedIds.has(v.id)).map((v) => v.fingerprint),
					templateIds: [],
					bulk: true
				};
		fileOpen = true;
	}

	function afterFiling() {
		if (fileFor?.bulk) checkedIds.clear();
		const reload = () => {
			void refresh(true);
			if (drawerOpen && selected) void openById(selected.id);
		};
		reload();
		setTimeout(reload, FILED_RECHECK_MS);
	}

	function scrollCursor() {
		document
			.querySelector(`[data-vuln-row-index="${cursor}"]`)
			?.scrollIntoView({ block: 'nearest' });
	}
	const TRIAGE_KEYS: Record<string, string> = Object.fromEntries(
		Object.entries(VULN_STATE_KEYS).map(([state, key]) => [key, state])
	);

	function onKey(e: KeyboardEvent) {
		if (!active || e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		const typing =
			!!t &&
			(t.tagName === 'INPUT' ||
				t.tagName === 'TEXTAREA' ||
				t.isContentEditable ||
				!!t.closest('[role=listbox], [role=menu], [role=combobox], [role=dialog] select'));
		if (e.key === '/' && !typing) {
			e.preventDefault();
			searchRef?.focus();
			return;
		}
		if (typing) return;
		const state = TRIAGE_KEYS[e.key];
		const target = drawerOpen ? selected : isIssues ? null : (items[cursor] ?? null);
		if (state && target) {
			e.preventDefault();
			void triage(target, state);
			return;
		}
		if (e.key === 'x' && !drawerOpen) {
			e.preventDefault();
			const id = isIssues ? issues[cursor]?.template_id : items[cursor]?.id;
			if (id) toggleCheck(id);
			return;
		}
		if (e.key === '?' && !drawerOpen) {
			shortcutsOpen = true;
			return;
		}
		if (drawerOpen || !rowCount) return;
		const row = !isIssues ? items[cursor] : null;
		if (row && (e.key === 'e' || e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
			e.preventDefault();
			if (e.key === 'ArrowLeft') expanded.delete(row.id);
			else if (e.key === 'ArrowRight') expanded.add(row.id);
			else toggleExpand(row.id);
			return;
		}
		if (row && expanded.has(row.id) && /^[1-5]$/.test(e.key)) {
			e.preventDefault();
			findingPrefs.tab = BRIEF_TABS[Number(e.key) - 1];
			return;
		}
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			cursor = Math.min(cursor + 1, rowCount - 1);
			scrollCursor();
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			cursor = Math.max(cursor - 1, 0);
			scrollCursor();
		} else if (e.key === 'Enter' && cursor >= 0) {
			if (isIssues && issues[cursor]) toggleIssue(issues[cursor]);
			else if (!isIssues && items[cursor]) open(items[cursor]);
		} else if (e.key === 'Escape') {
			if (row && expanded.has(row.id)) {
				expanded.delete(row.id);
				return;
			}
			cursor = -1;
			if (isIssues) collapse();
		}
	}

	let rescanBusy = $state(false);

	$effect(() => {
		if (!active || !projectId) return;
		void rechecks.loadSchema();
		if (projectWide || !scanId) return;
		untrack(() => rechecks.load(scanId, projectId));
	});

	function pickedRows() {
		const picked = isIssues
			? instances.filter((v) => checkedIds.has(v.template_id))
			: items.filter((v) => checkedIds.has(v.id));
		if (picked.length) return picked;
		return isIssues ? [] : items.filter((v) => v.id === selected?.id);
	}

	function picksOf(rows: typeof items): SeedPick[] {
		const picks: SeedPick[] = [];
		const seen: Record<string, true> = {};
		for (const v of rows) {
			const value = v.host || v.ip;
			if (!value) continue;
			const key = `${value}:${v.scan_id ?? ''}`;
			if (seen[key]) continue;
			seen[key] = true;
			picks.push({ value, scan_id: v.scan_id ?? scanId });
		}
		return picks;
	}

	function templatesOf(rows: typeof items): string[] {
		return [...new Set(rows.map((v) => v.template_id).filter(Boolean))] as string[];
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
		} = compileVulnQuery(query, 'severity', 1, 0, 1);
		return {
			dimension: SurfaceDimension.VULNERABILITIES,
			query: { filter, scan_ids: scanId ? [scanId] : [] }
		};
	}

	async function run(sel: SeedSelection, templates: string[]) {
		if (rescanBusy) return;
		rescanBusy = true;
		const ok = await startRescan(projectId, sel, 'finding', 'findings', {
			template_ids: templates
		});
		if (ok) checkedIds.clear();
		rescanBusy = false;
	}

	async function rescanSelection() {
		const rows = pickedRows();
		const picks = picksOf(rows);
		if (picks.length) {
			await run({ dimension: SurfaceDimension.VULNERABILITIES, picks }, templatesOf(rows));
		}
	}

	async function rescanOne(v: VulnerabilityRead) {
		const picks = picksOf([v]);
		if (picks.length)
			await run({ dimension: SurfaceDimension.VULNERABILITIES, picks }, [v.template_id]);
	}

	const SHORTCUTS: [string, string][] = [
		['j / k', 'Move between findings'],
		['e', 'Expand or collapse the row'],
		['1 to 5', 'Switch row tab'],
		['Enter', 'Open finding'],
		['x', 'Select finding'],
		[Object.values(VULN_STATE_KEYS).join(' / '), Object.values(VULN_STATE_LABELS).join(', ')],
		['/', 'Search'],
		['Esc', 'Collapse or clear']
	];

	async function rescanAllMatching() {
		await run(querySelection(), []);
	}

	let rescanOptionsFor = $state<{ selection: SeedSelection; templates: string[] } | null>(null);

	function openRescanOptions() {
		const rows = pickedRows();
		const picks = picksOf(rows);
		if (!picks.length) return;
		rescanOptionsFor = {
			selection: { dimension: SurfaceDimension.VULNERABILITIES, picks },
			templates: templatesOf(rows)
		};
	}

	function openRescanAllOptions() {
		rescanOptionsFor = { selection: querySelection(), templates: [] };
	}

	let barH = $state(0);
	let scrollRef = $state<HTMLElement | null>(null);
</script>

<svelte:window onkeydown={onKey} />

{#snippet sortHead(label: string, key: string, cls: string)}
	<button
		type="button"
		class="{cls} items-center gap-1 text-left tracking-wide uppercase hover:text-foreground {sort.key ===
		key
			? 'text-foreground'
			: ''}"
		onclick={() => toggleSort(key)}
	>
		{label}
		{#if sort.key === key}
			{#if sort.dir === -1}<ArrowDown class="size-3" />{:else}<ArrowUp class="size-3" />{/if}
		{/if}
	</button>
{/snippet}

<div class="mb-3">
	<FindingsStrip
		{overview}
		counts={severityCounts}
		unit={isIssues ? 'Checks' : 'Findings'}
		severities={query.severities}
		newOn={query.newOnly}
		kevOn={query.kevOnly}
		hostOn={(h) => query.hosts.includes(h)}
		onSeverity={toggleSeverity}
		onNew={() => setQuery({ ...query, newOnly: !query.newOnly })}
		onKev={() => setQuery({ ...query, kevOnly: !query.kevOnly })}
		onHost={toggleHost}
	/>
</div>

<div
	class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2"
	bind:clientHeight={barH}
>
	<QueryBar
		bind:this={queryBar}
		bind:ref={searchRef}
		store={vulnQuerySchema}
		recentsKey={SURFACE[SurfaceDimension.VULNERABILITIES].recentsKey}
		hint="severity:critical and not is:cdn"
		value={query.search}
		facets={facetsAsRecord(facets) as unknown as Record<string, Facet[]>}
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

<Card.Root class="gap-0 overflow-clip rounded-t-none border-t-0 py-0">
	<div class="flex items-center gap-3 border-b pr-3 pl-2">
		<div class="min-w-0 flex-1">
			<CountTabs
				tabs={REVIEW_TABS}
				value={reviewTab}
				counts={reviewCounts}
				onChange={setReviewTab}
			/>
		</div>
		<Hint text="Keyboard shortcuts">
			{#snippet child(props)}
				<Button
					{...props}
					variant="ghost"
					size="icon"
					class="hidden size-7 sm:inline-flex"
					aria-label="Keyboard shortcuts"
					onclick={() => (shortcutsOpen = true)}
				>
					<Keyboard class="size-4" />
				</Button>
			{/snippet}
		</Hint>
		<ToggleGroup.Root
			type="single"
			value={view}
			onValueChange={(v) => v && setView(v as VulnView)}
			variant="outline"
			size="sm"
			class="shrink-0"
			aria-label="View"
		>
			{#each VULN_VIEWS as option (option.key)}
				<ToggleGroup.Item value={option.key} class="h-7 px-2.5 text-xs font-normal">
					{option.label}
				</ToggleGroup.Item>
			{/each}
		</ToggleGroup.Root>
	</div>

	{#if coverageLoaded}
		<CoverageStrip {coverage} />
	{/if}

	<FilterBar
		{query}
		{facets}
		onQuery={setQuery}
		dimensions={vulnQuerySchema.schema.group_dimensions}
		columns={isIssues ? ISSUE_COLUMNS : findingColumns}
		visible={isIssues ? ISSUE_COLUMNS.map((c) => c.key) : findingVisible}
		columnsLocked={isIssues}
		onToggleColumn={toggleCol}
		{density}
		onDensity={(d) => (density = d)}
		sorts={isIssues ? ISSUE_SORTS : VULN_SORTS}
		sortKey={sort.key}
		sortDir={sort.dir}
		onSort={toggleSort}
		{refreshing}
		{projectId}
		{scanId}
		{exportFilters}
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
				onclick={() => setQuery({ ...emptyVulnQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if !groupBy}
		<SelectionBar
			noun={VULN.noun}
			nounPlural={VULN.nounPlural}
			{total}
			{totalCapped}
			maxAssets={rechecks.schema?.max_assets ?? 0}
			queryActive={Boolean(query.search.trim()) || chips.length > 0}
			query={queryLabel()}
			busy={rescanBusy}
			onRescanAll={rescanAllMatching}
			onRescanAllOptions={openRescanAllOptions}
		/>
	{/if}

	{#if loading && rowCount === 0 && !groupBy}
		<ScrollArea orientation="horizontal">
			<TableSkeleton
				lead={isIssues ? ISSUE_LEAD_COLUMNS : VULN_LEAD_COLUMNS}
				columns={isIssues ? ISSUE_COLUMNS : []}
				{density}
				selectable
			/>
		</ScrollArea>
	{:else if errored}
		<EmptyState
			icon={TriangleAlert}
			title="Findings not loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" class="gap-2" onclick={() => refresh()}>
				<RefreshCw class="h-4 w-4" /> Retry
			</Button>
		</EmptyState>
	{:else if groupBy}
		<GroupList
			set={groupSet}
			failed={groupFailed}
			onRetry={loadGroups}
			dimensions={vulnQuerySchema.schema.group_dimensions}
			noun={vulnQuerySchema.schema.noun}
			nounPlural={vulnQuerySchema.schema.noun_plural}
			loading={groupLoading}
			onPick={drillGroup}
		/>
	{:else if rowCount === 0}
		{#if queryError}
			<EmptyState
				icon={SearchX}
				title="Query did not run"
				description={queryError.message}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if filtered}
			<EmptyState
				icon={SearchX}
				title="No findings match"
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button
					size="sm"
					variant="outline"
					class="gap-2"
					onclick={() => setQuery(emptyVulnQuery())}
				>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			</EmptyState>
		{:else if ranScan}
			<EmptyState
				icon={ShieldCheck}
				title="No findings"
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if coverageLoaded}
			<EmptyState
				icon={ShieldCheck}
				title="Not scanned"
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else}
			<EmptyState
				icon={TriangleAlert}
				title="Scan coverage not loaded"
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" class="gap-2" onclick={() => loadCoverage()}>
					<RefreshCw class="h-4 w-4" /> Retry
				</Button>
			</EmptyState>
		{/if}
	{:else if isIssues}
		<ListHeader
			sticky
			top={barH}
			follow={scrollRef}
			lead={ISSUE_LEAD_COLUMNS}
			columns={ISSUE_COLUMNS}
			{selectAllChecked}
			selectAllLabel="Select all weaknesses on this page"
			onSelectAll={toggleSelectAll}
			sortKey={sort.key}
			sortDir={sort.dir}
			onSort={toggleSort}
		/>
		<ScrollArea orientation="horizontal" bind:ref={scrollRef}>
			<div class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}">
				{#each issues as issue, i (issue.template_id)}
					<div>
						<IssueRow
							{issue}
							index={i}
							{term}
							columns={ISSUE_COLUMNS}
							checked={checkedIds.has(issue.template_id)}
							onCheck={toggleCheck}
							expanded={expandedId === issue.template_id}
							focused={cursor === i}
							pad={rowPad}
							onToggle={toggleIssue}
							onFilter={applyDsl}
							onFindings={showFindings}
							onHosts={showHost}
							onTriage={triageIssue}
						/>
						{#if expandedId === issue.template_id}
							<IssueInstances
								items={instances}
								loading={instancesLoading}
								total={instancesTotal}
								pageSize={INSTANCE_PAGE}
								selectedId={drawerOpen ? (selected?.id ?? null) : null}
								onOpen={open}
								onMore={moreInstances}
							/>
						{/if}
					</div>
				{/each}
			</div>
		</ScrollArea>
	{:else}
		<div class="@container/findings w-full" role="table" aria-label="Findings">
			<div
				class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
				role="row"
			>
				<div class={FCOL.select}>
					<Checkbox
						checked={selectAllChecked === true}
						indeterminate={selectAllChecked === 'indeterminate'}
						onCheckedChange={toggleSelectAll}
						aria-label="Select all findings on this page"
					/>
				</div>
				{@render sortHead('Severity', 'severity', `${FCOL.severity} flex`)}
				{@render sortHead('Finding', 'name', `${FCOL.finding} flex`)}
				{#if projectWide}<div class={FCOL.target}>Target</div>{/if}
				{#if findingPrefs.shows('asset')}{@render sortHead('Web asset', 'host', FCOL.asset)}{/if}
				{#if findingPrefs.shows('related')}<div class={FCOL.related}>Correlation</div>{/if}
				{#if findingPrefs.shows('risk')}{@render sortHead('Risk', 'exploit', FCOL.risk)}{/if}
				{#if findingPrefs.shows('evidence')}<div class={FCOL.evidence}>Evidence</div>{/if}
				{#if findingPrefs.shows('review')}<div class={FCOL.review}>Review</div>{/if}
				{#if showIssue}<div class={FCOL.issue}>Issue</div>{/if}
				{#if findingPrefs.shows('seen')}{@render sortHead('Seen', 'seen', FCOL.seen)}{/if}
				<div class={FCOL.actions}></div>
			</div>
			<div class="transition-opacity {loading ? 'opacity-60' : ''}">
				{#each items as v, i (v.id)}
					<FindingRow
						{v}
						index={i}
						{projectId}
						{scanId}
						{projectWide}
						{term}
						compact={density === 'compact'}
						expanded={expanded.has(v.id)}
						focused={cursor === i}
						selected={drawerOpen && selected?.id === v.id}
						checked={checkedIds.has(v.id)}
						onToggle={() => toggleExpand(v.id)}
						onCheck={() => toggleCheck(v.id)}
						onFocus={() => (cursor = i)}
						onOpen={open}
						onFilter={applyDsl}
						onTab={(tab, filter) => {
							drawerOpen = false;
							syncUrl();
							onTab?.(tab, filter);
						}}
						onTriage={(item, state) => triage(item, state)}
						onRescan={rescanOne}
						onFileIssue={fileOne}
						{showIssue}
					/>
				{/each}
			</div>
		</div>
	{/if}

	{#if !errored && total > 0 && !groupBy}
		<ResultsPagination
			{total}
			capped={totalCapped}
			page={pageIndex}
			{pageSize}
			{noun}
			plural={nounPlural}
			onPage={(p) => (pageIndex = p)}
			onPageSize={(s) => {
				pageSize = s;
				pageIndex = 0;
			}}
		/>
	{/if}
</Card.Root>

<Dialog.Root bind:open={shortcutsOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header><Dialog.Title>Keyboard shortcuts</Dialog.Title></Dialog.Header>
		<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
			{#each SHORTCUTS as [k, label] (k)}
				<dt><Kbd>{k}</Kbd></dt>
				<dd class="text-muted-foreground">{label}</dd>
			{/each}
		</dl>
	</Dialog.Content>
</Dialog.Root>

<VulnerabilityDetailSheet
	vuln={selected}
	{projectId}
	{scanId}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={selectedIndex}
	pageOffset={isIssues ? 0 : pageIndex * pageSize}
	total={sheetTotal}
	onStep={step}
	onFilter={applyDsl}
	onHost={showHost}
	onLocation={showLocation}
	onStructure={onTab
		? (u) => {
				const tokens = locationTokensFromUrl(u);
				if (tokens) {
					drawerOpen = false;
					onTab(EP.tab, tokens);
				}
			}
		: undefined}
	onTriage={triage}
	onTab={onTab
		? (tab, filter) => {
				drawerOpen = false;
				syncUrl();
				onTab(tab, filter);
			}
		: undefined}
	onOpenFinding={open}
	onRescan={rescanOne}
	onFileIssue={fileOne}
/>

{#if fileFor}
	<FileIssuesDialog
		bind:open={fileOpen}
		{projectId}
		{scanId}
		fingerprints={fileFor.fingerprints}
		templateIds={fileFor.templateIds}
		onFiled={afterFiling}
	/>
{/if}

<RowSelectionBar
	count={checkedCount}
	dimension={SurfaceDimension.VULNERABILITIES}
	{projectId}
	{scanId}
	{noun}
	{nounPlural}
	removes={isIssues ? 'findings' : undefined}
	copy={isIssues
		? [{ label: 'template IDs', values: () => [...checkedIds] }]
		: [
				{
					label: 'locations',
					values: () => items.filter((v) => checkedIds.has(v.id)).map((v) => v.matched_at)
				},
				{
					label: 'template IDs',
					values: () => [
						...new Set(items.filter((v) => checkedIds.has(v.id)).map((v) => v.template_id))
					]
				}
			]}
	hide={hideOptions}
	onHide={(tokens) => {
		setQuery({ ...query, search: appendTokens(query.search, tokens) });
		checkedIds.clear();
	}}
	ids={() => [...checkedIds]}
	deleteKey={isIssues ? 'template_id' : 'id'}
	exportIds={() => (isIssues ? [] : [...checkedIds])}
	exportFilters={isIssues ? { ...exportFilters, templates: [...checkedIds] } : exportFilters}
	onDeleted={() => {
		checkedIds.clear();
		void refresh();
	}}
	onClear={() => checkedIds.clear()}
>
	{#snippet actions()}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="sm"
						class="gap-2 font-medium"
						disabled={bulkBusy}
					>
						<Tags class="h-3.5 w-3.5 text-muted-foreground" />
						Mark as
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="center" class="w-48">
				{#each Object.entries(VULN_STATE_LABELS) as [value, label] (value)}
					<DropdownMenu.Item onclick={() => triageChecked(value)}>{label}</DropdownMenu.Item>
				{/each}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
		<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={fileChecked}>
			<SquareKanban class="h-3.5 w-3.5 text-muted-foreground" />
			File issues
		</Button>
		<RescanAction
			count={checkedCount}
			dimension={SurfaceDimension.VULNERABILITIES}
			{noun}
			{nounPlural}
			busy={rescanBusy}
			onRescan={rescanSelection}
		/>
		<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={openRescanOptions}>
			<Settings2 class="h-3.5 w-3.5 text-muted-foreground" />
			Options
		</Button>
	{/snippet}
</RowSelectionBar>

<LaunchDialog
	open={rescanOptionsFor !== null}
	rescan={rescanOptionsFor
		? {
				selection: rescanOptionsFor.selection,
				dimension: SurfaceDimension.VULNERABILITIES,
				targetType,
				seedKind: seedKindFor(rechecks.schema, SurfaceDimension.VULNERABILITIES),
				assets: rescanOptionsFor.selection.picks?.map((pick) => pick.value) ?? [],
				queryLabel: rescanOptionsFor.selection.query ? queryLabel() : undefined,
				templateIds: rescanOptionsFor.templates
			}
		: null}
	onClose={() => {
		rescanOptionsFor = null;
		checkedIds.clear();
	}}
/>
