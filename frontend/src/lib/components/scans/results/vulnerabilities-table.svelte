<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
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
	import Tags from '@lucide/svelte/icons/tags';
	import SearchX from '@lucide/svelte/icons/search-x';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';

	import * as Card from '$lib/components/ui/card';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import CountTabs from '@/components/count-tabs.svelte';
	import EmptyState from '@/components/empty-state.svelte';

	import QueryBar from './query-bar/query-bar.svelte';
	import GroupList from './table/group-list.svelte';
	import { GroupedView, ResultsTable } from './table/results-state.svelte';
	import { pageParam, parsePageIndex, parseSort, sortParam, type SortKey } from './table/sort';
	import ListHeader from './table/list-header.svelte';
	import { rowPadding, selectAllState, withTarget } from './table/columns';
	import { readPref, writePref } from '$lib/utilities/storage';
	import ResultsPagination from './table/results-pagination.svelte';
	import CoverageStrip from './vulnerabilities/coverage-strip.svelte';
	import FilterBar from './vulnerabilities/filter-bar.svelte';
	import IssueInstances from './vulnerabilities/issue-instances.svelte';
	import SelectionBar from './table/selection-bar.svelte';
	import RowSelectionBar from './table/row-selection-bar.svelte';
	import RescanAction from './table/rescan-action.svelte';
	import type { SeedPick, SeedSelection } from '$lib/types/recheck';
	import IssueRow from './vulnerabilities/issue-row.svelte';
	import VulnRow from './vulnerabilities/vuln-row.svelte';
	import VulnerabilityDetailSheet from './vulnerability-detail-sheet.svelte';
	import {
		DEFAULT_VISIBLE_VULN_COLUMNS,
		ISSUE_COLUMNS,
		ISSUE_LEAD_COLUMNS,
		VULN_COLUMNS,
		VULN_LEAD_COLUMNS
	} from './vulnerabilities/columns';

	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import { vulnQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { VULN_STATE_LABELS, VULN_STATE_KEYS } from '$lib/config/vulnerabilities';
	import { appendToken, exactToken, type Facet } from '$lib/utilities/scan-insights';
	import {
		compileVulnQuery,
		emptyVulnQuery,
		facetsAsRecord,
		vulnActiveFacetCount,
		vulnQueryChips,
		DEFAULT_VULN_VIEW,
		EMPTY_VULN_FACETS,
		ISSUE_SORTS,
		SEVERITY_TABS,
		VULN_SORTS,
		VULN_VIEWS,
		type CoverageRead,
		type IssueRead,
		type VulnFacetSet,
		type VulnQuery,
		type VulnView,
		type VulnerabilityRead
	} from '$lib/utilities/vulns';
	import { locationTokensFromUrl } from '$lib/utilities/endpoints';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LatestRequest } from '$lib/utilities/latest-request';
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

	const DEFAULT_SORT: SortKey = { key: 'risk', dir: -1 };
	const INSTANCE_PAGE = 100;
	const VIEW_KEYS = new Set<string>(VULN_VIEWS.map((v) => v.key));

	const initial = appPage.url.searchParams;
	const initialView = initial.get('vuln_view');

	let view = $state<VulnView>(
		initialView && VIEW_KEYS.has(initialView)
			? (initialView as VulnView)
			: readPref<VulnView>(STORAGE_KEYS.vulnsView, DEFAULT_VULN_VIEW)
	);
	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.vulnsColumns, null));
	const table = new ResultsTable<VulnerabilityRead, VulnFacetSet>({
		facets: EMPTY_VULN_FACETS,
		sort: parseSort(initial.get('vuln_sort'), DEFAULT_SORT),
		pageIndex: parsePageIndex(initial.get('vuln_page')),
		pageSizeKey: STORAGE_KEYS.vulnsPageSize,
		densityKey: STORAGE_KEYS.vulnsDensity
	});
	const groups = new GroupedView(
		initial.get('vuln_group') ?? '',
		(by) => vulnerabilitiesApi.groups(projectId, scanId, by, leadFilterWithQuery),
		() => ready
	);

	let issues = $state<IssueRead[]>([]);
	let coverage = $state<CoverageRead[]>([]);

	let expandedId = $state<string | null>(null);
	let instancesSig = '';
	let pendingVuln = initial.get('vuln');
	let instances = $state<VulnerabilityRead[]>([]);
	let instancesTotal = $state(0);
	let instancesLoading = $state(false);
	let instanceLimit = $state(INSTANCE_PAGE);
	const instanceReq = new LatestRequest();

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
	let rowCount = $derived(isIssues ? issues.length : table.items.length);
	let sheetItems = $derived(isIssues ? instances : table.items);
	let selectedIndex = $derived(selected ? sheetItems.findIndex((v) => v.id === selected?.id) : -1);
	let sheetTotal = $derived(isIssues ? instancesTotal : table.total);
	let visible = $derived(visiblePref ?? DEFAULT_VISIBLE_VULN_COLUMNS);
	let allColumns = $derived(withTarget(VULN_COLUMNS, projectWide));
	let shownColumns = $derived(
		allColumns.filter((c) => visible.includes(c.key) || c.key === 'target')
	);
	let checkedCount = $derived(
		isIssues
			? issues.filter((i) => checkedIds.has(i.template_id)).length
			: table.items.filter((v) => checkedIds.has(v.id)).length
	);
	let selectAllChecked = $derived(selectAllState(checkedCount, rowCount));
	let filtered = $derived(vulnActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(vulnQueryChips(query, table.facets));
	let rowPad = $derived(rowPadding(table.density));
	let term = $derived(query.search.trim().includes(':') ? '' : query.search.trim());
	let severityTab = $derived(
		query.severities.length === 0 ? 'all' : query.severities.length === 1 ? query.severities[0] : ''
	);
	let severityCounts = $derived.by(() => {
		if (!table.facetsLoaded) return null;
		const source = isIssues ? table.facets.issue_severity : table.facets.severity;
		const m: Record<string, number> = { all: source.reduce((n, f) => n + f.count, 0) };
		for (const f of source) m[f.name] = f.count;
		return m;
	});
	let coverageLoaded = $state(false);
	let ranScan = $derived(coverage.some((c) => c.status !== 'skipped'));
	let noun = $derived(isIssues ? 'weakness' : VULN.noun);
	let nounPlural = $derived(isIssues ? 'weaknesses' : VULN.nounPlural);

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.vulnsColumns, visiblePref);
	});
	$effect(() => writePref(STORAGE_KEYS.vulnsView, view));
	$effect(() => {
		const ids = new Set(isIssues ? issues.map((i) => i.template_id) : table.items.map((v) => v.id));
		for (const id of checkedIds) if (!ids.has(id)) checkedIds.delete(id);
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
		const filter = compileVulnQuery(
			query,
			table.sort.key,
			table.sort.dir,
			table.pageIndex * table.pageSize,
			table.pageSize
		);
		const sig = JSON.stringify({ ...filter, offset: 0, view });
		if (sig !== lastSig && table.pageIndex !== 0 && !pendingSelect) {
			lastSig = sig;
			table.pageIndex = 0;
			return;
		}
		lastSig = sig;
		const current = table.searchRequest.begin();
		table.loading = true;
		try {
			if (view === 'issues') {
				const res = await vulnerabilitiesApi.issues(projectId, scanId, filter);
				if (!current()) return;
				issues = res.items;
				table.total = res.total;
				table.totalCapped = res.total_capped;
				table.queryError = res.error;
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
				if (!current()) return;
				table.accept(res);
				if (pendingVuln) {
					const id = pendingVuln;
					pendingVuln = null;
					const hit = table.items.find((v) => v.id === id);
					if (hit) open(hit);
					else void openById(id);
				}
				if (pendingSelect) {
					selected =
						pendingSelect === 'first' ? (table.items[0] ?? null) : (table.items.at(-1) ?? null);
					pendingSelect = null;
				}
			}
			table.errored = false;
			if (!table.queryError && filter.q) queryBar?.remember(filter.q);
		} catch {
			if (current()) {
				issues = [];
				table.fail();
			}
		} finally {
			if (current()) {
				table.loading = false;
				syncLeads();
			}
		}
	}

	let exportFilters = $derived(
		compileVulnQuery(query, table.sort.key, table.sort.dir, 0, 1) as unknown as Record<
			string,
			unknown
		>
	);
	let leadFilter = $derived(compileVulnQuery({ ...query, search: '' }, 'risk', -1, 0, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groups.by ? JSON.stringify(leadFilterWithQuery) + groups.by : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await vulnerabilitiesApi.leads(projectId, scanId, leadFilter);
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
			table.facets = await vulnerabilitiesApi.facets(projectId, scanId);
			onScanTotal?.(table.facets.severity.reduce((n, f) => n + f.count, 0));
			table.facetsLoaded = true;
		} catch {
			if (!table.facetsLoaded) table.facets = EMPTY_VULN_FACETS;
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
		const current = instanceReq.begin();
		instancesSig = JSON.stringify(query);
		instancesLoading = true;
		try {
			const filter = compileVulnQuery({ ...query, templates: [templateId] }, 'host', 1, 0, limit);
			const res = await vulnerabilitiesApi.search(projectId, scanId, filter);
			if (!current()) return;
			instances = res.items;
			instancesTotal = res.total;
		} catch {
			if (current()) {
				instances = [];
				instancesTotal = 0;
			}
		} finally {
			if (current()) instancesLoading = false;
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
		table.refreshing = !quiet;
		try {
			if (!quiet) loadedLeadSig = '';
			await Promise.all([runSearch(), loadFacets(), loadCoverage(), groups.reload()]);
			if (expandedId) await loadInstances(expandedId, instanceLimit);
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
		});
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
			set('vuln_q', query.search || null);
			set('vuln_group', groups.by || null);
			set('vuln_view', view !== DEFAULT_VULN_VIEW ? view : null);
			set('vuln_page', pageParam(table.pageIndex));
			set('vuln', drawerOpen && selected ? selected.id : null);
			set('vuln_sort', sortParam(table.sort, DEFAULT_SORT));
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
		void view;
		void table.sort.key;
		void table.sort.dir;
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
			toast.error('Finding not found in this scan');
		}
	}
	function step(dir: -1 | 1) {
		const next = selectedIndex + dir;
		if (next >= 0 && next < sheetItems.length) {
			selected = sheetItems[next];
			return;
		}
		if (isIssues) return;
		if (dir === 1 && table.pageIndex < table.pageCount - 1) {
			pendingSelect = 'first';
			table.pageIndex += 1;
		} else if (dir === -1 && table.pageIndex > 0) {
			pendingSelect = 'last';
			table.pageIndex -= 1;
		}
	}
	function setView(next: VulnView) {
		if (next === view) return;
		view = next;
		checkedIds.clear();
		collapse();
		cursor = -1;
		table.pageIndex = 0;
		table.sort = { ...DEFAULT_SORT };
	}
	function toggleSort(key: string) {
		table.toggleSort(key);
	}
	function toggleCheck(id: string) {
		if (checkedIds.has(id)) checkedIds.delete(id);
		else checkedIds.add(id);
	}
	function toggleSelectAll() {
		if (checkedCount === rowCount) checkedIds.clear();
		else if (isIssues) for (const i of issues) checkedIds.add(i.template_id);
		else for (const v of table.items) checkedIds.add(v.id);
	}
	function toggleCol(key: string) {
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: VulnQuery) {
		query = q;
		table.pageIndex = 0;
	}
	function setSeverityTab(key: string) {
		setQuery({ ...query, severities: key === 'all' ? [] : [key] });
	}
	function drillGroup(token: string) {
		setQuery({ ...query, search: appendToken(query.search, token) });
		groups.by = '';
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
		table.items = table.items.map((item) =>
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
		void loadFacets();
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
			const fingerprints = table.items
				.filter((v) => checkedIds.has(v.id))
				.map((v) => v.fingerprint);
			void triageMany({ fingerprints }, state, what);
		}
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
		const target = drawerOpen ? selected : isIssues ? null : (table.items[cursor] ?? null);
		if (state && target) {
			e.preventDefault();
			void triage(target, state);
			return;
		}
		if (e.key === 'x' && !drawerOpen) {
			e.preventDefault();
			const id = isIssues ? issues[cursor]?.template_id : table.items[cursor]?.id;
			if (id) toggleCheck(id);
			return;
		}
		if (drawerOpen || !rowCount) return;
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
			else if (!isIssues && table.items[cursor]) open(table.items[cursor]);
		} else if (e.key === 'Escape') {
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
			: table.items.filter((v) => checkedIds.has(v.id));
		if (picked.length) return picked;
		return isIssues ? [] : table.items.filter((v) => v.id === selected?.id);
	}

	function picksOf(rows: VulnerabilityRead[]): SeedPick[] {
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

	function templatesOf(rows: VulnerabilityRead[]): string[] {
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
		facets={facetsAsRecord(table.facets) as unknown as Record<string, Facet[]>}
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
	<div class="flex items-center gap-3 border-b pr-3 pl-2">
		<div class="min-w-0 flex-1">
			<CountTabs
				tabs={SEVERITY_TABS}
				value={severityTab}
				counts={severityCounts}
				onChange={setSeverityTab}
			/>
		</div>
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
		<CoverageStrip {projectWide} {coverage} />
	{/if}

	<FilterBar
		{query}
		facets={table.facets}
		onQuery={setQuery}
		dimensions={vulnQuerySchema.schema.group_dimensions}
		columns={isIssues ? ISSUE_COLUMNS : VULN_COLUMNS}
		visible={isIssues ? ISSUE_COLUMNS.map((c) => c.key) : visible}
		columnsLocked={isIssues}
		onToggleColumn={toggleCol}
		density={table.density}
		onDensity={(d) => (table.density = d)}
		sorts={isIssues ? ISSUE_SORTS : VULN_SORTS}
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
				onclick={() => setQuery({ ...emptyVulnQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if !groups.by}
		<SelectionBar
			noun={VULN.noun}
			nounPlural={VULN.nounPlural}
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

	{#if table.loading && rowCount === 0 && !groups.by}
		<ScrollArea orientation="horizontal">
			<TableSkeleton
				lead={isIssues ? ISSUE_LEAD_COLUMNS : VULN_LEAD_COLUMNS}
				columns={isIssues ? ISSUE_COLUMNS : shownColumns}
				density={table.density}
				selectable
			/>
		</ScrollArea>
	{:else if table.errored}
		<EmptyState
			icon={TriangleAlert}
			title="Findings not loaded"
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
			dimensions={vulnQuerySchema.schema.group_dimensions}
			noun={vulnQuerySchema.schema.noun}
			nounPlural={vulnQuerySchema.schema.noun_plural}
			loading={groups.loading}
			onPick={drillGroup}
		/>
	{:else if rowCount === 0}
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
				title="No findings match"
				description="Widen the search or remove a filter."
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
				title="No vulnerability scan ran"
				description="The engine leaves vulnerability scanning off and it was not added at launch."
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
			sortKey={table.sort.key}
			sortDir={table.sort.dir}
			onSort={toggleSort}
		/>
		<ScrollArea orientation="horizontal" bind:ref={scrollRef}>
			<div class="divide-y divide-border/50 transition-opacity {table.loading ? 'opacity-60' : ''}">
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
		<ListHeader
			sticky
			top={barH}
			follow={scrollRef}
			lead={VULN_LEAD_COLUMNS}
			columns={shownColumns}
			{selectAllChecked}
			selectAllLabel="Select all findings on this page"
			onSelectAll={toggleSelectAll}
			sortKey={table.sort.key}
			sortDir={table.sort.dir}
			onSort={toggleSort}
		/>
		<ScrollArea orientation="horizontal" bind:ref={scrollRef}>
			<div class="divide-y divide-border/50 transition-opacity {table.loading ? 'opacity-60' : ''}">
				{#each table.items as v, i (v.id)}
					<VulnRow
						vuln={v}
						index={i}
						{term}
						columns={shownColumns}
						checked={checkedIds.has(v.id)}
						onCheck={toggleCheck}
						selected={drawerOpen && selected?.id === v.id}
						focused={cursor === i}
						pad={rowPad}
						onOpen={open}
						onFilter={applyDsl}
						onHost={showHost}
						onTriage={(item, state) => triage(item, state)}
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
			{noun}
			plural={nounPlural}
			onPage={(p) => (table.pageIndex = p)}
			onPageSize={(s) => table.setPageSize(s)}
		/>
	{/if}
</Card.Root>

<VulnerabilityDetailSheet
	vuln={selected}
	{projectId}
	{scanId}
	open={drawerOpen}
	onOpenChange={(o) => (drawerOpen = o)}
	index={selectedIndex}
	pageOffset={isIssues ? 0 : table.pageIndex * table.pageSize}
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
/>

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
					values: () => table.items.filter((v) => checkedIds.has(v.id)).map((v) => v.matched_at)
				},
				{
					label: 'template IDs',
					values: () => [
						...new Set(table.items.filter((v) => checkedIds.has(v.id)).map((v) => v.template_id))
					]
				}
			]}
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
