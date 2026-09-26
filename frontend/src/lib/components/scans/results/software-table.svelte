<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Package from '@lucide/svelte/icons/package';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import SortMenu from './table/sort-menu.svelte';
	import { Toggle } from '$lib/components/ui/toggle';

	import QueryBar from './query-bar/query-bar.svelte';
	import ListHeader from './table/list-header.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import { rowPadding, selectAllState, TARGET_COLUMN, withTarget } from './table/columns';
	import { readPref, writePref } from '$lib/utilities/storage';
	import RowSelectionBar from './table/row-selection-bar.svelte';
	import { RowSelection } from './table/selection.svelte';
	import { ResultsTable } from './table/results-state.svelte';
	import { pageParam, parsePageIndex, parseSort, sortParam, type SortKey } from './table/sort';
	import ExportMenu from './export-menu.svelte';
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
	import { appendToken, type Facet } from '$lib/utilities/scan-insights';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LiveRefresh } from '$lib/utilities/live-results';
	import { SEVERITY_TABS } from '$lib/utilities/vulns';
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
		onScanTotal?: (total: number) => void;
	}

	let {
		scanId,
		projectId,
		projectWide = false,
		active = true,
		revision = 0,
		onScanTotal
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
	const DEFAULT_SORT: SortKey = { key: 'rank', dir: -1 };

	const initial = appPage.url.searchParams;

	let search = $state(initial.get('sw_q') ?? '');
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let sideLoaded = $state(false);
	const table = new ResultsTable<SoftwareCve, SoftwareFacets>({
		facets: EMPTY_FACETS,
		sort: parseSort(initial.get('sw_sort'), DEFAULT_SORT),
		pageIndex: parsePageIndex(initial.get('sw_page')),
		pageSizeKey: STORAGE_KEYS.softwarePageSize,
		densityKey: STORAGE_KEYS.softwareDensity
	});
	let visiblePref = $state<string[] | null>(readPref(STORAGE_KEYS.softwareColumns, null));

	let coverage = $state<SoftwareCoverage | null>(null);

	const QUICK_FILTERS = [
		{ token: 'is:new', label: 'New' },
		{ token: 'is:kev', label: 'Known exploited' },
		{ token: 'evidence:corroborated', label: 'Corroborated' },
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
	let checkedCount = $derived(selection.countOn(table.items));
	let selectAllChecked = $derived(selectAllState(checkedCount, table.items.length));
	let exportFilters = $derived({
		q: search.trim() || null,
		sort: table.sort.key,
		direction: table.sort.dir === -1 ? 'desc' : 'asc'
	} as unknown as Record<string, unknown>);
	let rowPad = $derived(rowPadding(table.density));
	let term = $derived(search.trim().includes(':') ? '' : search.trim());
	let filtered = $derived(Boolean(search.trim()));
	let severityCounts = $derived.by(() => {
		if (!sideLoaded) return null;
		const out: Record<string, number> = { all: coverage?.findings ?? 0 };
		for (const f of table.facets.severity) out[f.key] = f.count;
		return out;
	});
	let severityTab = $derived.by(() => {
		const m = search.match(/(?:^|\s)severity:([a-z]+)(?:\s|$)/);
		return m ? m[1] : 'all';
	});
	let barFacets = $derived<Record<string, Facet[]>>({
		severity: table.facets.severity.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		confidence: table.facets.confidence.map((f) => ({
			value: f.key,
			label: f.label,
			count: f.count
		})),
		source: table.facets.source.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		caveat: table.facets.caveat.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		evidence: table.facets.evidence.map((f) => ({ value: f.key, label: f.label, count: f.count }))
	});

	$effect(() => {
		if (visiblePref) writePref(STORAGE_KEYS.softwareColumns, visiblePref);
	});

	let timer: ReturnType<typeof setTimeout> | null = null;

	function filterOf(): SoftwareFilter {
		return {
			q: search.trim() || undefined,
			limit: table.pageSize,
			offset: table.pageIndex * table.pageSize,
			sort: table.sort.key,
			direction: table.sort.dir === -1 ? 'desc' : 'asc'
		};
	}

	async function runSearch() {
		if (!ready || !table.queryReady) return;
		const current = table.searchRequest.begin();
		table.refreshing = table.items.length > 0;
		const filter = filterOf();
		try {
			const result = await softwareApi.search(projectId, scanId, filter);
			if (!current()) return;
			table.queryError = result.error ?? null;
			table.items = result.error ? [] : result.items;
			table.total = result.error ? 0 : result.total;
			table.totalCapped = result.total_capped;
			table.errored = false;
			if (!result.error && filter.q) queryBar?.remember(filter.q);
		} catch {
			if (!current()) return;
			table.errored = true;
			table.items = [];
			table.total = 0;
		} finally {
			if (current()) {
				table.loading = false;
				table.refreshing = false;
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
			table.facets = f;
			coverage = c;
			sideLoaded = true;
			onScanTotal?.(c.findings);
		} catch {
			// ignore
		}
	}

	const live = new LiveRefresh(() => {
		void runSearch();
		void loadSide();
	});
	$effect(() => {
		const tick = revision;
		untrack(() => live.notify(tick, active && seen));
	});
	onDestroy(() => live.stop());

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
		const params = new SvelteURLSearchParams(appPage.url.searchParams);
		const set = (k: string, v: string | null) => (v ? params.set(k, v) : params.delete(k));
		set('sw_q', search.trim() || null);
		set('sw_page', pageParam(table.pageIndex));
		set('sw_sort', sortParam(table.sort, DEFAULT_SORT));
		const next = `${appPage.url.pathname}${params.size ? `?${params}` : ''}`;
		replaceState(next, appPage.state);
	}

	function onQuery(value: string) {
		search = value;
		table.pageIndex = 0;
		syncUrl();
		schedule();
	}

	function setSeverityTab(key: string) {
		const without = search.replace(/(?:^|\s)severity:[a-z]+/g, '').trim();
		onQuery(key === 'all' ? without : `${without} severity:${key}`.trim());
	}

	function hasToken(token: string) {
		return new RegExp(`(?:^|\\s)${token}(?:\\s|$)`).test(search);
	}

	function toggleToken(token: string) {
		if (!hasToken(token)) {
			onQuery(appendToken(search, token));
			return;
		}
		onQuery(search.replace(new RegExp(`(?:^|\\s)${token}`, 'g'), '').trim());
	}

	function onToken(token: string) {
		onQuery(appendToken(search, token));
	}

	function toggleCheck(id: string) {
		const row = table.items.find((r) => r.id === id);
		if (row) selection.toggle(row);
	}

	function toggleSelectAll() {
		selection.toggleAll(table.items);
	}

	function onSort(key: string) {
		table.toggleSort(key, -1);
		syncUrl();
		void runSearch();
	}

	function onPage(next: number) {
		table.pageIndex = Math.max(0, Math.min(next, table.pageCount - 1));
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
		busy={table.refreshing}
		total={table.errored ? null : table.total}
		capped={table.totalCapped}
		serverError={table.queryError}
		onReady={(value) => (table.queryReady = value)}
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

	<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
		{#each QUICK_FILTERS as filter (filter.token)}
			<Toggle
				size="sm"
				variant="outline"
				pressed={hasToken(filter.token)}
				onPressedChange={() => toggleToken(filter.token)}
				class="h-7 px-2.5 text-xs font-normal"
			>
				{filter.label}
			</Toggle>
		{/each}
		<div class="ml-auto flex items-center gap-1.5">
			<SortMenu sorts={SOFTWARE_SORTS} sortKey={table.sort.key} sortDir={table.sort.dir} {onSort} />
			<ExportMenu
				dimension={SurfaceDimension.SOFTWARE}
				{projectId}
				{scanId}
				filters={exportFilters}
			/>
			<Button
				variant="ghost"
				size="icon"
				class="size-7"
				aria-label="Refresh"
				onclick={() => {
					void runSearch();
					void loadSide();
				}}
			>
				<RefreshCw class="size-3.5 {table.refreshing ? 'animate-spin' : ''}" />
			</Button>
		</div>
	</div>

	{#if table.loading}
		<ScrollArea orientation="horizontal" class="min-h-0">
			<div class="min-w-max">
				<TableSkeleton
					lead={projectWide ? [TARGET_COLUMN, ...SOFTWARE_LEAD_COLUMNS] : SOFTWARE_LEAD_COLUMNS}
					columns={shownColumns.filter((c) => c.key !== 'target')}
					density={table.density}
					selectable
				/>
			</div>
		</ScrollArea>
	{:else if table.errored}
		<EmptyState icon={TriangleAlert} title="Software CVEs not loaded">
			<Button variant="outline" size="sm" onclick={() => void runSearch()}>Retry</Button>
		</EmptyState>
	{:else if coverage && coverage.components === 0}
		<EmptyState icon={Package} title="No software versions reported" />
	{:else if table.items.length === 0}
		<EmptyState
			icon={filtered ? SearchX : Package}
			title={filtered ? 'No software CVEs match' : 'No software CVEs'}
		>
			{#if filtered}
				<Button variant="outline" size="sm" onclick={() => onQuery('')}>Clear query</Button>
			{/if}
		</EmptyState>
	{:else}
		<ListHeader
			sticky
			top={barH}
			follow={scrollRef}
			lead={projectWide ? [TARGET_COLUMN, ...SOFTWARE_LEAD_COLUMNS] : SOFTWARE_LEAD_COLUMNS}
			columns={shownColumns.filter((c) => c.key !== 'target')}
			sortKey={table.sort.key}
			sortDir={table.sort.dir}
			{selectAllChecked}
			selectAllLabel="Select every software CVE on this page"
			onSelectAll={toggleSelectAll}
			{onSort}
		/>
		<ScrollArea orientation="horizontal" class="min-h-0" bind:ref={scrollRef}>
			<div class="min-w-max">
				<div
					class="divide-y divide-border/50 transition-opacity {table.refreshing
						? 'opacity-60'
						: ''}"
				>
					{#each table.items as row (row.id)}
						<SoftwareRow
							{row}
							{term}
							columns={shownColumns}
							selected={selected?.id === row.id}
							focused={false}
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
			total={table.total}
			page={table.pageIndex}
			pageSize={table.pageSize}
			capped={table.totalCapped}
			noun={SW.noun}
			plural={SW.nounPlural}
			{onPage}
			onPageSize={(size) => {
				table.setPageSize(size);
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
