<script lang="ts">
	import { page as appPage } from '$app/state';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Package from '@lucide/svelte/icons/package';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';

	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import ViewControls from './table/view-controls.svelte';

	import QueryBar from './query-bar/query-bar.svelte';
	import ListHeader from './table/list-header.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import {
		readPref,
		rowPadding,
		selectAllState,
		TARGET_COLUMN,
		withTarget,
		writePref
	} from './table/columns';
	import RowSelectionBar from './table/row-selection-bar.svelte';
	import { RowSelection } from './table/selection.svelte';
	import SoftwareRow from './software/software-row.svelte';
	import SoftwareDetailSheet from './software/software-detail-sheet.svelte';
	import {
		SOFTWARE_COLUMNS,
		SOFTWARE_LEAD_COLUMNS,
		SOFTWARE_SORTS,
		DEFAULT_VISIBLE_SOFTWARE_COLUMNS
	} from './software/columns';

	import { softwareApi } from '$lib/api/scan-results';
	import { softwareQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import {
		hideLabel,
		excludeToken,
		appendTokens,
		appendToken,
		hasToken,
		withoutToken,
		type Facet
	} from '$lib/utilities/scan-insights';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { UrlSync, onPopSearch } from '$lib/utilities/url-history.svelte';
	import { LiveRefresh } from '$lib/utilities/live-results';
	import { ALL_TAB, TabCounts, countTabs, withTab } from '$lib/utilities/tab-counts.svelte';
	import { SEVERITY_TABS } from '$lib/utilities/vulns';
	import type { QueryError } from '$lib/types/asset-query';
	import { EVIDENCE_LABELS, Evidence, evidenceToken } from '$lib/config/evidence';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type {
		SoftwareCoverage,
		SoftwareCve,
		SoftwareFacets,
		SoftwareFilter
	} from '$lib/types/software';

	interface Props {
		scanId: string;
		projectId: string;
		projectWide?: boolean;
		active?: boolean;
		revision?: number;
		onScanTotal?: (total: number, capped: boolean) => void;
		onSearch?: (query: string) => void;
	}

	let {
		scanId,
		projectId,
		projectWide = false,
		active = true,
		revision = 0,
		onScanTotal,
		onSearch
	}: Props = $props();

	const SW = SURFACE[SurfaceDimension.SOFTWARE];

	const EMPTY_FACETS: SoftwareFacets = {
		severity: [],
		confidence: [],
		source: [],
		caveat: [],
		evidence: [],
		product: []
	};
	const DEFAULT_SORT = { key: 'rank', dir: -1 as const };

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('sw_sort')?.split(':') ?? [];

	let search = $state(initial.get('sw_q') ?? '');
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let sideLoaded = $state(false);
	let density = $state<string>(readPref(STORAGE_KEYS.softwareDensity, 'cozy'));
	let pageSize = $state<number>(readPref(STORAGE_KEYS.softwarePageSize, RESULTS_PAGE_SIZE));
	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.softwareColumns, null));
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('sw_page') ?? 1) - 1));

	let items = $state<SoftwareCve[]>([]);
	let total = $state(0);
	let totalCapped = $state(false);
	let queryError = $state<QueryError | null>(null);
	let queryReady = $state(true);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let facets = $state<SoftwareFacets>(EMPTY_FACETS);
	let coverage = $state<SoftwareCoverage | null>(null);

	const QUICK_FILTERS = [
		{ token: 'is:new', label: 'New' },
		{ token: 'is:kev', label: 'Known exploited' },
		{
			token: evidenceToken(Evidence.CROSS_CHECKED),
			label: EVIDENCE_LABELS[Evidence.CROSS_CHECKED]
		},
		{ token: 'is:firm', label: 'Firm' },
		{ token: 'is:stated', label: 'Server stated' }
	];
	let selected = $state<SoftwareCve | null>(null);
	let drawerOpen = $state(false);
	const selection = new RowSelection<SoftwareCve>();

	let ready = $derived(Boolean(projectId) && (projectWide || Boolean(scanId)));
	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let visible = $derived(visiblePref ?? DEFAULT_VISIBLE_SOFTWARE_COLUMNS);
	let allColumns = $derived(withTarget(SOFTWARE_COLUMNS, projectWide));
	let shownColumns = $derived(
		allColumns.filter((c) => visible.includes(c.key) || c.key === 'target')
	);
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let checkedCount = $derived(selection.countOn(items));
	let selectAllChecked = $derived(selectAllState(checkedCount, items.length));
	let exportFilters = $derived({
		q: search.trim() || null,
		sort: sort.key,
		direction: sort.dir === -1 ? 'desc' : 'asc'
	} as unknown as Record<string, unknown>);
	let rowPad = $derived(rowPadding(density));
	let term = $derived(search.trim().includes(':') ? '' : search.trim());
	let filtered = $derived(Boolean(search.trim()));
	const tabCounts = new TabCounts();
	let tabSearch = $derived(withTab(search, 'severity', ALL_TAB));
	let severityCounts = $derived.by(() => {
		if (tabSearch) return tabCounts.counts;
		if (!sideLoaded) return null;
		const out: Record<string, number> = { all: coverage?.findings ?? 0 };
		for (const f of facets.severity) out[f.key] = f.count;
		return out;
	});
	let severityTab = $derived.by(() => {
		const m = search.match(/(?:^|\s)severity:([a-z]+)(?:\s|$)/);
		return m ? m[1] : 'all';
	});
	let severityTabs = $derived(
		SEVERITY_TABS.filter(
			(t) =>
				t.key === 'all' ||
				t.key === severityTab ||
				!severityCounts ||
				(severityCounts[t.key] ?? 0) > 0
		)
	);
	let barFacets = $derived<Record<string, Facet[]>>({
		severity: facets.severity.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		confidence: facets.confidence.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		source: facets.source.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		caveat: facets.caveat.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		evidence: facets.evidence.map((f) => ({ value: f.key, label: f.label, count: f.count }))
	});

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.softwareColumns, visiblePref);
	});
	$effect(() => writePref(STORAGE_KEYS.softwareDensity, density));
	$effect(() => writePref(STORAGE_KEYS.softwarePageSize, pageSize));

	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;

	function filterOf(): SoftwareFilter {
		return {
			q: search.trim() || undefined,
			limit: pageSize,
			offset: pageIndex * pageSize,
			sort: sort.key,
			direction: sort.dir === -1 ? 'desc' : 'asc'
		};
	}

	async function runSearch() {
		if (!ready || !queryReady) return;
		const mine = ++reqId;
		refreshing = items.length > 0;
		const filter = filterOf();
		try {
			const result = await softwareApi.search(projectId, scanId, filter);
			if (mine !== reqId) return;
			queryError = result.error ?? null;
			items = result.error ? [] : result.items;
			total = result.error ? 0 : result.total;
			totalCapped = result.total_capped;
			errored = false;
			if (!result.error && filter.q) queryBar?.remember(filter.q);
		} catch {
			if (mine !== reqId) return;
			errored = true;
			items = [];
			total = 0;
		} finally {
			if (mine === reqId) {
				loading = false;
				refreshing = false;
			}
		}
	}

	function schedule() {
		if (timer) clearTimeout(timer);
		timer = setTimeout(() => {
			timer = null;
			void runSearch();
		}, SEARCH_DEBOUNCE_MS);
	}

	async function loadSide() {
		if (!ready) return;
		try {
			const [f, c] = await Promise.all([
				softwareApi.facets(projectId, scanId),
				softwareApi.coverage(projectId, scanId)
			]);
			facets = f;
			coverage = c;
			sideLoaded = true;
			onScanTotal?.(c.findings, c.capped_at != null);
		} catch {}
	}

	const live = new LiveRefresh(() => {
		tabCounts.refresh();
		void runSearch();
		void loadSide();
	});
	$effect(() => {
		const tick = revision;
		untrack(() => live.notify(tick, active && seen));
	});
	onDestroy(() => live.stop());
	onDestroy(() => tabCounts.clear());

	$effect(() => {
		const base = tabSearch;
		const key = `${projectId}|${scanId}|${base}`;
		if (!ready || !seen || !queryReady) return;
		untrack(() => {
			if (!base) {
				tabCounts.clear();
				return;
			}
			const queries = Object.fromEntries(
				SEVERITY_TABS.map((t) => [t.key, withTab(base, 'severity', t.key)])
			);
			tabCounts.track(key, () =>
				countTabs(queries, (q) => softwareApi.counts(projectId, scanId, q))
			);
		});
	});

	let primed = false;
	$effect(() => {
		const key = `${projectId}|${scanId}|${projectWide}|${seen}`;
		if (!ready || !seen) return;
		untrack(() => {
			void key;
			if (!primed) {
				primed = true;
				void softwareQuerySchema.load();
				void loadSide();
			}
			void runSearch();
		});
	});

	function syncUrl() {
		const params = new SvelteURLSearchParams(location.search);
		if (search.trim()) params.set('sw_q', search.trim());
		else params.delete('sw_q');
		if (pageIndex > 0) params.set('sw_page', String(pageIndex + 1));
		else params.delete('sw_page');
		if (sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir) {
			params.set('sw_sort', `${sort.key}:${sort.dir === -1 ? 'desc' : 'asc'}`);
		} else params.delete('sw_sort');
		urlSync.write(params);
	}
	const urlSync = new UrlSync(['sw_q'], true);
	$effect(() => onSearch?.(search.trim()));

	function restoreUrl(sp: URLSearchParams) {
		const nextSearch = sp.get('sw_q') ?? '';
		const searchChanged = nextSearch !== search;
		const before = `${sort.key}:${sort.dir}:${pageIndex}`;
		search = nextSearch;
		const [sortKey, sortDir] = sp.get('sw_sort')?.split(':') ?? [];
		const nextSort = sortKey
			? { key: sortKey, dir: (sortDir === 'desc' ? -1 : 1) as 1 | -1 }
			: { ...DEFAULT_SORT };
		if (nextSort.key !== sort.key || nextSort.dir !== sort.dir) sort = nextSort;
		const nextPage = Math.max(0, Number(sp.get('sw_page') ?? 1) - 1);
		if (nextPage !== pageIndex) pageIndex = nextPage;
		if (searchChanged) schedule();
		else if (before !== `${sort.key}:${sort.dir}:${pageIndex}`) void runSearch();
	}
	$effect(() => onPopSearch(restoreUrl));

	let hideOptions = $derived([
		{
			label: hideLabel([...new Set(selection.rows().map((r) => r.name))], 'products'),
			tokens: () => [...new Set(selection.rows().map((r) => excludeToken('software', r.name)))]
		},
		{
			label: hideLabel([...new Set(selection.rows().map((r) => r.cve))], 'CVEs'),
			tokens: () => [...new Set(selection.rows().map((r) => excludeToken('cve', r.cve)))]
		}
	]);

	function onQuery(value: string) {
		search = value;
		pageIndex = 0;
		syncUrl();
		schedule();
	}

	function setSeverityTab(key: string) {
		onQuery(withTab(search, 'severity', key));
	}

	function onToken(token: string) {
		onQuery(appendToken(search, token));
	}

	let quick = $derived(QUICK_FILTERS.filter((f) => hasToken(search, f.token)).map((f) => f.token));

	function setQuick(values: string[]) {
		let next = search;
		for (const { token } of QUICK_FILTERS) {
			const on = values.includes(token);
			if (on && !hasToken(next, token)) next = appendToken(next, token);
			else if (!on && hasToken(next, token)) next = withoutToken(next, token);
		}
		onQuery(next);
	}

	function toggleCheck(id: string) {
		const row = items.find((r) => r.id === id);
		if (row) selection.toggle(row);
	}

	function toggleSelectAll() {
		selection.toggleAll(items);
	}

	function toggleColumn(key: string) {
		visiblePref = visible.includes(key) ? visible.filter((k) => k !== key) : [...visible, key];
	}

	function onSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: -1 };
		pageIndex = 0;
		syncUrl();
		void runSearch();
	}

	function onPage(next: number) {
		pageIndex = Math.max(0, Math.min(next, pageCount - 1));
		syncUrl();
		void runSearch();
	}

	function openRow(row: SoftwareCve) {
		selected = row;
		drawerOpen = true;
	}

	let barH = $state(0);
	let scrollRef = $state<HTMLElement | null>(null);
</script>

<div
	class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2"
	bind:clientHeight={barH}
>
	<QueryBar
		bind:this={queryBar}
		store={softwareQuerySchema}
		recentsKey={SURFACE[SurfaceDimension.SOFTWARE].recentsKey}
		hint="severity:critical and is:stated"
		value={search}
		facets={barFacets}
		onChange={onQuery}
		busy={refreshing}
		total={errored ? null : total}
		capped={totalCapped}
		serverError={queryError}
		onReady={(value) => (queryReady = value)}
	/>
</div>

<Card.Root class="gap-0 overflow-clip rounded-t-none border-t-0 py-0">
	<div class="flex items-center gap-3 border-b pr-3 pl-2">
		<div class="min-w-0 flex-1">
			<CountTabs
				tabs={severityTabs}
				value={severityTab}
				counts={severityCounts}
				capped={tabSearch ? tabCounts.capped : coverage?.capped_at != null ? { all: true } : null}
				onChange={setSeverityTab}
			/>
		</div>
		<Hint text="Reported versions matched against the NVD corpus. Not confirmed by a request.">
			{#snippet child(props)}
				<Badge {...props} variant="outline" class="h-5 shrink-0 px-1.5 text-2xs">Inferred</Badge>
			{/snippet}
		</Hint>
	</div>

	{#if coverage && !coverage.feed_ready}
		<div class="flex items-start gap-2 border-b bg-muted/10 px-4 py-2 text-xs">
			<TriangleAlert class="mt-0.5 size-3.5 shrink-0 text-warning" />
			<span class="text-muted-foreground">
				The NVD corpus has not been downloaded. Turn on feed downloads in Arsenal.
			</span>
		</div>
	{:else if coverage && coverage.components > 0}
		<div class="border-b bg-muted/10 px-4 py-2 text-xs text-muted-foreground">
			{coverage.mapped.toLocaleString()} of {coverage.components.toLocaleString()} reported components
			map to an NVD product.
		</div>
	{/if}
	{#if coverage?.capped_at != null}
		<div class="flex items-start gap-2 border-b bg-muted/10 px-4 py-2 text-xs">
			<TriangleAlert class="mt-0.5 size-3.5 shrink-0 text-warning" />
			<span class="text-muted-foreground">
				Matching stopped at {coverage.capped_at.toLocaleString()} software CVEs per scan. Known-exploited
				and higher-severity matches are stored first.
			</span>
		</div>
	{/if}

	<div class="flex flex-wrap items-start gap-2 border-b px-4 py-3">
		<div class="flex min-w-0 flex-1 basis-72 flex-wrap items-center gap-2">
			<ScrollArea
				orientation="horizontal"
				class="max-lg:max-w-full max-lg:min-w-0"
				scrollbarXClasses="h-1"
			>
				<ToggleGroup.Root
					type="multiple"
					value={quick}
					onValueChange={setQuick}
					variant="outline"
					aria-label="Filters"
				>
					{#each QUICK_FILTERS as filter (filter.token)}
						<ToggleGroup.Item value={filter.token} class="h-9 px-3 text-sm font-normal">
							{filter.label}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			</ScrollArea>
		</div>
		<div class="flex min-w-0 flex-wrap items-center gap-2">
			<ViewControls
				dimension={SurfaceDimension.SOFTWARE}
				dimensions={[]}
				groupBy=""
				onGroupBy={() => {}}
				showGroupBy={false}
				sorts={SOFTWARE_SORTS}
				sortKey={sort.key}
				sortDir={sort.dir}
				{onSort}
				columns={SOFTWARE_COLUMNS}
				{visible}
				onToggleColumn={toggleColumn}
				{density}
				onDensity={(d) => (density = d)}
				{refreshing}
				onRefresh={() => {
					void runSearch();
					void loadSide();
				}}
				{projectId}
				{scanId}
				{exportFilters}
			/>
		</div>
	</div>

	{#if loading}
		<ScrollArea orientation="horizontal" class="min-h-0">
			<div class="min-w-max">
				<TableSkeleton
					lead={projectWide ? [TARGET_COLUMN, ...SOFTWARE_LEAD_COLUMNS] : SOFTWARE_LEAD_COLUMNS}
					columns={shownColumns.filter((c) => c.key !== 'target')}
					{density}
					selectable
				/>
			</div>
		</ScrollArea>
	{:else if errored}
		<EmptyState
			icon={TriangleAlert}
			title="Software CVEs not loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" size="sm" onclick={() => void runSearch()}>Retry</Button>
		</EmptyState>
	{:else if coverage && coverage.components === 0}
		<EmptyState
			icon={Package}
			title="No software versions reported"
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{:else if items.length === 0}
		<EmptyState
			icon={filtered ? SearchX : Package}
			title={filtered ? 'No software CVEs match' : 'No software CVEs'}
			class="rounded-none border-0 bg-transparent py-16"
		>
			{#if filtered}
				<Button variant="outline" size="sm" onclick={() => onQuery('')}>
					<X class="h-4 w-4" /> Clear filters
				</Button>
			{/if}
		</EmptyState>
	{:else}
		<ListHeader
			sticky
			top={barH}
			follow={scrollRef}
			lead={projectWide ? [TARGET_COLUMN, ...SOFTWARE_LEAD_COLUMNS] : SOFTWARE_LEAD_COLUMNS}
			columns={shownColumns.filter((c) => c.key !== 'target')}
			sortKey={sort.key}
			sortDir={sort.dir}
			{selectAllChecked}
			selectAllLabel="Select every software CVE on this page"
			onSelectAll={toggleSelectAll}
			{onSort}
		/>
		<ScrollArea orientation="horizontal" class="min-h-0" bind:ref={scrollRef}>
			<div class="min-w-max">
				<div class="divide-y divide-border/50 transition-opacity {refreshing ? 'opacity-60' : ''}">
					{#each items as row (row.id)}
						<SoftwareRow
							{row}
							{term}
							columns={shownColumns}
							selected={selected?.id === row.id}
							checked={selection.has(row.id)}
							{projectWide}
							pad={rowPad}
							onCheck={toggleCheck}
							onOpen={openRow}
							{onToken}
						/>
					{/each}
				</div>
			</div>
		</ScrollArea>

		<ResultsPagination
			{total}
			page={pageIndex}
			{pageSize}
			capped={totalCapped}
			noun={SW.noun}
			plural={SW.nounPlural}
			{onPage}
			onPageSize={(size) => {
				pageSize = size;
				pageIndex = 0;
				void runSearch();
			}}
		/>
	{/if}
</Card.Root>

<RowSelectionBar
	count={selection.size}
	dimension={SurfaceDimension.SOFTWARE}
	{projectId}
	{scanId}
	copy={[
		{ label: 'CVEs', values: () => [...new Set(selection.rows().map((r) => r.cve))] },
		{
			label: 'web assets',
			values: () => [
				...new Set(
					selection
						.rows()
						.map((r) => r.host ?? r.ip ?? '')
						.filter(Boolean)
				)
			]
		}
	]}
	hide={hideOptions}
	onHide={(tokens) => {
		onQuery(appendTokens(search, tokens));
		selection.clear();
	}}
	ids={() => selection.ids()}
	{exportFilters}
	onDeleted={() => {
		selection.clear();
		void runSearch();
		void loadSide();
	}}
	onClear={() => selection.clear()}
/>

<SoftwareDetailSheet
	row={selected}
	open={drawerOpen}
	onOpenChange={(value) => {
		drawerOpen = value;
		if (!value) selected = null;
	}}
/>
