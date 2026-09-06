<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { seedKindFor } from '$lib/utilities/rechecks';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { startRescan } from '$lib/utilities/rechecks';
	import { SurfaceDimension } from '$lib/config/surface';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
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
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CountTabs from '@/components/count-tabs.svelte';
	import EmptyState from '@/components/empty-state.svelte';

	import QueryBar from './query-bar/query-bar.svelte';
	import GroupList from './table/group-list.svelte';
	import ListHeader from './table/list-header.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import CoverageStrip from './vulnerabilities/coverage-strip.svelte';
	import FilterBar from './vulnerabilities/filter-bar.svelte';
	import IssueInstances from './vulnerabilities/issue-instances.svelte';
	import SelectionBar from './table/selection-bar.svelte';
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
	import { VULN_STATE_LABELS } from '$lib/config/vulnerabilities';
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
	import type { QueryError, QueryGroups, QueryLeads } from '$lib/types/asset-query';
	import { locationTokensFromUrl } from '$lib/utilities/endpoints';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';

	interface Props {
		scanId: string;
		targetId?: string;
		targetType?: string;
		active?: boolean;
		onTab?: (tab: string, filter?: string) => void;
		onScanTotal?: (total: number) => void;
		query?: VulnQuery;
	}

	let {
		scanId,
		targetId = '',
		targetType = '',
		active = true,
		onTab,
		onScanTotal,
		query = $bindable({
			...emptyVulnQuery(),
			search: appPage.url.searchParams.get('vuln_q') ?? ''
		})
	}: Props = $props();

	const DEFAULT_SORT = { key: 'risk', dir: -1 as const };
	const ROW_PAD: Record<string, string> = { compact: 'py-2', cozy: 'py-3' };
	const INSTANCE_PAGE = 100;
	const VIEW_KEYS = new Set<string>(VULN_VIEWS.map((v) => v.key));

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
	const initialSort = initial.get('vuln_sort')?.split(':') ?? [];
	const initialView = initial.get('vuln_view');

	let view = $state<VulnView>(
		initialView && VIEW_KEYS.has(initialView)
			? (initialView as VulnView)
			: readPref<VulnView>(STORAGE_KEYS.vulnsView, DEFAULT_VULN_VIEW)
	);
	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.vulnsColumns, null));
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
	let leadSet = $state<QueryLeads | null>(null);
	let groupBy = $state<string>(initial.get('vuln_group') ?? '');
	let groupSet = $state<QueryGroups | null>(null);
	let groupLoading = $state(false);
	let groupReq = 0;

	let expandedId = $state<string | null>(null);
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
	let visible = $derived(visiblePref ?? DEFAULT_VISIBLE_VULN_COLUMNS);
	let shownColumns = $derived(VULN_COLUMNS.filter((c) => visible.includes(c.key)));
	let checkedCount = $derived(
		isIssues
			? issues.filter((i) => checkedIds.has(i.template_id)).length
			: items.filter((v) => checkedIds.has(v.id)).length
	);
	let selectAllChecked = $derived<boolean | 'indeterminate'>(
		rowCount > 0 && checkedCount === rowCount ? true : checkedCount > 0 ? 'indeterminate' : false
	);
	let filtered = $derived(vulnActiveFacetCount(query) > 0 || !!query.search);
	let chips = $derived(vulnQueryChips(query, facets));
	let rowPad = $derived(ROW_PAD[density] ?? ROW_PAD.cozy);
	let term = $derived(query.search.trim().includes(':') ? '' : query.search.trim());
	let severityTab = $derived(
		query.severities.length === 0 ? 'all' : query.severities.length === 1 ? query.severities[0] : ''
	);
	let severityCounts = $derived.by(() => {
		if (!facetsLoaded) return null;
		const source = isIssues ? facets.issue_severity : facets.severity;
		const m: Record<string, number> = { all: source.reduce((n, f) => n + f.count, 0) };
		for (const f of source) m[f.name] = f.count;
		return m;
	});
	let ranScan = $derived(coverage.some((c) => c.status !== 'skipped'));
	let noun = $derived(isIssues ? 'weakness' : 'finding');
	let nounPlural = $derived(isIssues ? 'weaknesses' : 'findings');

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.vulnsColumns, visiblePref);
	});
	$effect(() => writePref(STORAGE_KEYS.vulnsDensity, density));
	$effect(() => writePref(STORAGE_KEYS.vulnsPageSize, pageSize));
	$effect(() => writePref(STORAGE_KEYS.vulnsView, view));
	$effect(() => {
		const ids = new Set(isIssues ? issues.map((i) => i.template_id) : items.map((v) => v.id));
		for (const id of checkedIds) if (!ids.has(id)) checkedIds.delete(id);
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
				const res = await vulnerabilitiesApi.issues(scanId, filter);
				if (my !== reqId) return;
				issues = res.items;
				total = res.total;
				totalCapped = res.total_capped;
				queryError = res.error;
				if (expandedId && !issues.some((i) => i.template_id === expandedId)) collapse();
			} else {
				const res = await vulnerabilitiesApi.search(scanId, filter);
				if (my !== reqId) return;
				items = res.items;
				total = res.total;
				totalCapped = res.total_capped;
				queryError = res.error;
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

	let leadFilter = $derived(compileVulnQuery({ ...query, search: '' }, 'risk', -1, 0, 1));
	let leadSig = $derived(JSON.stringify(leadFilter));
	let leadFilterWithQuery = $derived({ ...leadFilter, q: query.search.trim() || null });
	let groupSig = $derived(groupBy ? JSON.stringify(leadFilterWithQuery) + groupBy : '');
	let loadedLeadSig = '';

	async function loadLeads() {
		const sig = leadSig;
		loadedLeadSig = sig;
		try {
			const res = await vulnerabilitiesApi.leads(scanId, leadFilter);
			if (leadSig === sig) leadSet = res.computed ? res : null;
		} catch {
			if (leadSig === sig) leadSet = null;
			loadedLeadSig = '';
		}
	}

	function syncLeads() {
		if (!active || loading || !scanId) return;
		if (leadSig === loadedLeadSig) return;
		void loadLeads();
	}

	async function loadGroups() {
		if (!groupBy || !scanId) {
			groupSet = null;
			return;
		}
		const my = ++groupReq;
		groupLoading = true;
		try {
			const res = await vulnerabilitiesApi.groups(scanId, groupBy, leadFilterWithQuery);
			if (my === groupReq) groupSet = res;
		} catch {
			if (my === groupReq) groupSet = null;
		} finally {
			if (my === groupReq) groupLoading = false;
		}
	}

	async function loadFacets() {
		if (!scanId) return;
		try {
			facets = await vulnerabilitiesApi.facets(scanId);
			// only a successful response may restate the tab count; a failed one is not zero
			onScanTotal?.(facets.severity.reduce((n, f) => n + f.count, 0));
		} catch {
			facets = EMPTY_VULN_FACETS;
		} finally {
			facetsLoaded = true;
		}
	}

	async function loadCoverage() {
		if (!scanId) return;
		try {
			coverage = await vulnerabilitiesApi.coverage(scanId);
		} catch {
			coverage = [];
		}
	}

	async function loadInstances(templateId: string, limit: number) {
		const my = ++instanceReq;
		instancesLoading = true;
		try {
			const filter = compileVulnQuery({ ...query, templates: [templateId] }, 'host', 1, 0, limit);
			const res = await vulnerabilitiesApi.search(scanId, filter);
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

	async function refresh() {
		refreshing = true;
		try {
			loadedLeadSig = '';
			await Promise.all([runSearch(), loadFacets(), loadCoverage(), loadGroups()]);
			if (expandedId) await loadInstances(expandedId, instanceLimit);
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
		void queryReady;
		void view;
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
			set('vuln_q', query.search || null);
			set('vuln_group', groupBy || null);
			set('vuln_view', view !== DEFAULT_VULN_VIEW ? view : null);
			set('vuln_page', pageIndex > 0 ? String(pageIndex + 1) : null);
			set(
				'vuln_sort',
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
		void groupBy;
		void pageIndex;
		void view;
		void sort.key;
		void sort.dir;
		if (!seen || !active) return;
		untrack(syncUrl);
	});

	function open(v: VulnerabilityRead) {
		selected = v;
		drawerOpen = true;
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
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}
	function setQuery(q: VulnQuery) {
		query = q;
		pageIndex = 0;
	}
	function setSeverityTab(key: string) {
		setQuery({ ...query, severities: key === 'all' ? [] : [key] });
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
		onTab?.('web-assets', filter);
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
			const result = await vulnerabilitiesApi.triage(scanId, v.fingerprint, state, note);
			applyState(new Set([v.fingerprint]), result.state, result.note);
			toast.success(`Marked ${VULN_STATE_LABELS[state].toLowerCase()}`, {
				description:
					result.updated > 1
						? `Applies to ${result.updated} recorded observations of this finding.`
						: 'Carried forward to later scans of this target.'
			});
			afterTriage();
		} catch {
			toast.error(`This finding could not be marked ${VULN_STATE_LABELS[state].toLowerCase()}`);
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
			const result = await vulnerabilitiesApi.triageMany(scanId, { ...body, state });
			toast.success(`Marked ${what} ${VULN_STATE_LABELS[state].toLowerCase()}`, {
				description: `${result.fingerprints.toLocaleString()} ${
					result.fingerprints === 1 ? 'finding' : 'findings'
				} decided. Carried forward to later scans of this target.`
			});
			if (body.fingerprints) applyState(new Set(body.fingerprints), state, null);
			checkedIds.clear();
			afterTriage();
		} catch {
			toast.error(`${what} could not be marked ${VULN_STATE_LABELS[state].toLowerCase()}`);
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

	function scrollCursor() {
		document
			.querySelector(`[data-vuln-row-index="${cursor}"]`)
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
		if (typing || drawerOpen || !rowCount) return;
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
			cursor = -1;
			if (isIssues) collapse();
		}
	}

	let rescanBusy = $state(false);
	let projectId = $derived(projectsStore.activeProject?.id ?? '');

	$effect(() => {
		if (!active || !scanId || !projectId) return;
		void rechecks.loadSchema();
		untrack(() => rechecks.load(scanId, projectId));
	});

	// re-verify exactly the checks that produced the selected findings
	async function rescanSelection() {
		if (rescanBusy) return;
		const picked = isIssues
			? instances.filter((v) => checkedIds.has(v.template_id))
			: items.filter((v) => checkedIds.has(v.id));
		const rows = picked.length
			? picked
			: isIssues
				? []
				: items.filter((v) => v.id === selected?.id);
		const assets = [...new Set(rows.map((v) => v.host || v.ip).filter(Boolean))] as string[];
		const templates = [...new Set(rows.map((v) => v.template_id).filter(Boolean))] as string[];
		if (!assets.length) return;
		rescanBusy = true;
		const ok = await startRescan(
			projectId,
			{
				parent_scan_id: scanId,
				dimension: SurfaceDimension.VULNERABILITIES,
				assets,
				template_ids: templates
			},
			'finding',
			'findings'
		);
		if (ok) checkedIds.clear();
		rescanBusy = false;
	}

	let rescanOptionsFor = $state<{ assets: string[]; templates: string[] } | null>(null);

	function openRescanOptions() {
		const rows = isIssues
			? instances.filter((v) => checkedIds.has(v.template_id))
			: items.filter((v) => checkedIds.has(v.id));
		const assets = [...new Set(rows.map((v) => v.host || v.ip).filter(Boolean))] as string[];
		if (!assets.length) return;
		rescanOptionsFor = {
			assets,
			templates: [...new Set(rows.map((v) => v.template_id).filter(Boolean))] as string[]
		};
	}
</script>

<svelte:window onkeydown={onKey} />

<div class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2">
	<QueryBar
		bind:this={queryBar}
		bind:ref={searchRef}
		store={vulnQuerySchema}
		recentsKey={STORAGE_KEYS.vulnsRecentQueries}
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

<Card.Root class="gap-0 overflow-hidden rounded-t-none border-t-0 py-0">
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

	<CoverageStrip {coverage} />

	<FilterBar
		{query}
		{facets}
		onQuery={setQuery}
		dimensions={vulnQuerySchema.schema.group_dimensions}
		columns={isIssues ? ISSUE_COLUMNS : VULN_COLUMNS}
		visible={isIssues ? ISSUE_COLUMNS.map((c) => c.key) : visible}
		columnsLocked={isIssues}
		onToggleColumn={toggleCol}
		{density}
		onDensity={(d) => (density = d)}
		sorts={isIssues ? ISSUE_SORTS : VULN_SORTS}
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
				onclick={() => setQuery({ ...emptyVulnQuery(), search: query.search })}
				aria-label="Clear all filters"
			>
				Clear all
			</button>
		</div>
	{/if}

	{#if checkedCount > 0 && !groupBy}
		<div
			class="flex flex-wrap items-center gap-3 border-b border-primary/20 bg-primary/5 px-4 py-2"
		>
			<span class="text-xs font-medium tabular-nums">
				{checkedCount}
				{checkedCount === 1 ? noun : nounPlural} selected
			</span>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm" class="h-7 gap-1.5" disabled={bulkBusy}>
							Mark as
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="w-48">
					{#each Object.entries(VULN_STATE_LABELS) as [value, label] (value)}
						<DropdownMenu.Item onclick={() => triageChecked(value)}>{label}</DropdownMenu.Item>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
			<span class="text-xs text-muted-foreground">
				A decision covers every observation and carries forward to later scans.
			</span>
			<Button
				variant="ghost"
				size="sm"
				class="ml-auto h-7 text-xs"
				onclick={() => checkedIds.clear()}
			>
				Clear selection
			</Button>
		</div>
	{/if}

	{#if !groupBy}
		<SelectionBar
			count={checkedCount}
			noun="finding"
			nounPlural="findings"
			busy={rescanBusy}
			reason="re-runs the exact checks that found them"
			onRescan={rescanSelection}
			onOptions={openRescanOptions}
			onClear={() => checkedIds.clear()}
		/>
	{/if}

	{#if loading && rowCount === 0 && !groupBy}
		<div class="divide-y divide-border/50">
			{#each Array(8) as _, i (i)}
				<div class="flex items-center gap-3 px-4 py-3">
					<Skeleton class="h-9 flex-1" />
					<Skeleton class="hidden h-5 w-52 sm:block" />
					<Skeleton class="hidden h-6 w-44 sm:block" />
					<Skeleton class="hidden h-5 w-24 sm:block" />
				</div>
			{/each}
		</div>
	{:else if errored}
		<EmptyState
			icon={TriangleAlert}
			title="Findings could not be loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" class="gap-2" onclick={refresh}>
				<RefreshCw class="h-4 w-4" /> Retry
			</Button>
		</EmptyState>
	{:else if groupBy}
		<GroupList
			set={groupSet}
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
				title="That query could not run"
				description={queryError.message}
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
				description="Every selected check ran and matched nothing. Coverage is reported above."
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else}
			<EmptyState
				icon={ShieldCheck}
				title="No vulnerability scan ran"
				description="Enable it on the scan engine, or add it when you launch the next scan."
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{/if}
	{:else if isIssues}
		<ScrollArea orientation="horizontal">
			<ListHeader
				lead={ISSUE_LEAD_COLUMNS}
				columns={ISSUE_COLUMNS}
				{selectAllChecked}
				selectAllLabel="Select all weaknesses on this page"
				onSelectAll={toggleSelectAll}
				sortKey={sort.key}
				sortDir={sort.dir}
				onSort={toggleSort}
			/>
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
		<ScrollArea orientation="horizontal">
			<ListHeader
				lead={VULN_LEAD_COLUMNS}
				columns={shownColumns}
				{selectAllChecked}
				selectAllLabel="Select all findings on this page"
				onSelectAll={toggleSelectAll}
				sortKey={sort.key}
				sortDir={sort.dir}
				onSort={toggleSort}
			/>
			<div class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}">
				{#each items as v, i (v.id)}
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

	{#if !errored && total > 0 && !groupBy}
		<ResultsPagination
			{total}
			capped={totalCapped}
			page={pageIndex}
			{pageSize}
			{noun}
			plural={nounPlural}
			selectedCount={checkedCount}
			onClearSelection={() => checkedIds.clear()}
			onPage={(p) => (pageIndex = p)}
			onPageSize={(s) => {
				pageSize = s;
				pageIndex = 0;
			}}
		/>
	{/if}
</Card.Root>

<VulnerabilityDetailSheet
	vuln={selected}
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
					onTab('endpoints', tokens);
				}
			}
		: undefined}
	onTriage={triage}
/>

<LaunchDialog
	open={rescanOptionsFor !== null}
	rescan={rescanOptionsFor
		? {
				parentScanId: scanId,
				targetId,
				dimension: SurfaceDimension.VULNERABILITIES,
				targetType,
				seedKind: seedKindFor(rechecks.schema, SurfaceDimension.VULNERABILITIES),
				assets: rescanOptionsFor.assets,
				templateIds: rescanOptionsFor.templates
			}
		: null}
	onClose={() => {
		rescanOptionsFor = null;
		checkedIds.clear();
	}}
/>
