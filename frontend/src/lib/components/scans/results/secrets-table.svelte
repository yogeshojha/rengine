<script lang="ts">
	import { page as appPage } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import SearchX from '@lucide/svelte/icons/search-x';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';

	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { Toggle } from '$lib/components/ui/toggle';
	import EmptyState from '$lib/components/empty-state.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import QueryBar from './query-bar/query-bar.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import ViewControls from './table/view-controls.svelte';
	import GroupList from './table/group-list.svelte';
	import { GroupedView, ResultsTable } from './table/results-state.svelte';
	import { pageParam, parsePageIndex, parseSort, sortParam, type SortKey } from './table/sort';
	import { selectAllState } from './table/columns';
	import RowSelectionBar from './table/row-selection-bar.svelte';
	import { RowSelection } from './table/selection.svelte';
	import SecretListHeader from './secrets/secret-list-header.svelte';
	import SecretRow from './secrets/secret-row.svelte';
	import SecretDetailSheet from './secrets/secret-detail-sheet.svelte';
	import CoverageStrip from './secrets/coverage-strip.svelte';
	import { SECRET_SORTS, secretSkeletonColumns } from './secrets/columns';

	import { secretsApi } from '$lib/api/scan-results';
	import { secretQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { appendToken, type Facet } from '$lib/utilities/scan-insights';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LiveRefresh } from '$lib/utilities/live-results';
	import { STATE_TABS } from '$lib/config/secrets';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type {
		SecretCoverage,
		SecretDetail,
		SecretFacets,
		SecretFilter,
		SecretRead
	} from '$lib/types/secret';

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

	const SEC = SURFACE[SurfaceDimension.SECRETS];
	const EMPTY_FACETS: SecretFacets = {
		state: [],
		group: [],
		kind: [],
		vendor: [],
		source: [],
		subject: []
	};
	const DEFAULT_SORT: SortKey = { key: 'state', dir: -1 };
	const QUICK_FILTERS = [
		{ token: 'is:exposed', label: 'Exposed' },
		{ token: 'is:new', label: 'New' },
		{ token: 'group:cloud', label: 'Cloud' },
		{ token: 'secret:email', label: 'Emails' },
		{ token: 'is:shared', label: 'On many web assets' }
	];

	const initial = appPage.url.searchParams;

	let search = $state(initial.get('sec_q') ?? '');
	const table = new ResultsTable<SecretRead, SecretFacets>({
		facets: EMPTY_FACETS,
		sort: parseSort(initial.get('sec_sort'), DEFAULT_SORT),
		pageIndex: parsePageIndex(initial.get('sec_page')),
		pageSizeKey: STORAGE_KEYS.secretPageSize
	});
	const groups = new GroupedView(
		initial.get('sec_group') ?? '',
		(by) => secretsApi.groups(projectId, scanId, by, { q: search.trim() || undefined }),
		() => ready
	);
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let sideLoaded = $state(false);

	let coverage = $state<SecretCoverage | null>(null);

	let selected = $state<SecretDetail | null>(null);
	let drawerOpen = $state(false);
	const selection = new RowSelection<SecretRead>();

	let ready = $derived(Boolean(projectId) && (projectWide || Boolean(scanId)));
	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let checkedCount = $derived(selection.countOn(table.items));
	let selectAllChecked = $derived(selectAllState(checkedCount, table.items.length));
	let term = $derived(search.trim().includes(':') ? '' : search.trim());
	let filtered = $derived(Boolean(search.trim()));
	let stateCounts = $derived.by(() => {
		if (!sideLoaded) return null;
		const out: Record<string, number> = { all: coverage?.secrets ?? 0 };
		for (const f of table.facets.state) out[f.key] = f.count;
		return out;
	});
	let stateTab = $derived.by(() => {
		const m = search.match(/(?:^|\s)state:([a-z]+)(?:\s|$)/);
		return m ? m[1] : 'all';
	});
	let exportFilters = $derived({
		q: search.trim() || null,
		sort: table.sort.key,
		direction: table.sort.dir === -1 ? 'desc' : 'asc'
	} as unknown as Record<string, unknown>);
	let barFacets = $derived<Record<string, Facet[]>>({
		state: table.facets.state.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		group: table.facets.group.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		secret: table.facets.kind.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		kind: table.facets.kind.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		vendor: table.facets.vendor.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		source: table.facets.source.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		subject: table.facets.subject.map((f) => ({ value: f.key, label: f.label, count: f.count }))
	});

	let timer: ReturnType<typeof setTimeout> | null = null;

	function filterOf(): SecretFilter {
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
			const result = await secretsApi.search(projectId, scanId, filter);
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
			void groups.reload();
		}, SEARCH_DEBOUNCE_MS);
	}

	async function loadSide() {
		if (!ready) return;
		try {
			const [f, c] = await Promise.all([
				secretsApi.facets(projectId, scanId),
				secretsApi.coverage(projectId, scanId)
			]);
			table.facets = f;
			coverage = c;
			sideLoaded = true;
			onScanTotal?.(c.secrets);
		} catch {
			// ignore
		}
	}

	const live = new LiveRefresh(() => {
		void runSearch();
		void loadSide();
		void groups.reload();
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
				void secretQuerySchema.load();
				void loadSide();
			}
			void runSearch();
			void groups.reload();
		});
	});

	let primedGroup = false;
	$effect(() => {
		void groups.by;
		if (!primedGroup) {
			primedGroup = true;
			return;
		}
		untrack(() => {
			syncUrl();
			void groups.reload();
		});
	});

	function syncUrl() {
		const params = new SvelteURLSearchParams(appPage.url.searchParams);
		const set = (k: string, v: string | null) => (v ? params.set(k, v) : params.delete(k));
		set('sec_q', search.trim() || null);
		set('sec_page', pageParam(table.pageIndex));
		set('sec_group', groups.by || null);
		set('sec_sort', sortParam(table.sort, DEFAULT_SORT));
		const next = `${appPage.url.pathname}${params.size ? `?${params}` : ''}`;
		replaceState(next, appPage.state);
	}

	function onQuery(value: string) {
		search = value;
		table.pageIndex = 0;
		syncUrl();
		schedule();
	}

	function drillGroup(query: string) {
		groups.by = '';
		onQuery(appendToken(search, query));
	}

	function setStateTab(key: string) {
		const without = search.replace(/(?:^|\s)state:[a-z]+/g, '').trim();
		onQuery(key === 'all' ? without : `${without} state:${key}`.trim());
	}

	function escapeRe(token: string) {
		return token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	function hasToken(token: string) {
		return new RegExp(`(?:^|\\s)${escapeRe(token)}(?:\\s|$)`).test(search);
	}

	function toggleToken(token: string) {
		if (!hasToken(token)) {
			onQuery(appendToken(search, token));
			return;
		}
		onQuery(search.replace(new RegExp(`(?:^|\\s)${escapeRe(token)}`, 'g'), '').trim());
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

	async function openRow(row: SecretRead) {
		drawerOpen = true;
		selected = { ...row, context: null, sightings_shown: [], sightings_truncated: false };
		try {
			selected = await secretsApi.detail(projectId, scanId, row.id);
		} catch {
			// ignore
		}
	}
</script>

<div class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2">
	<QueryBar
		bind:this={queryBar}
		store={secretQuerySchema}
		recentsKey={SURFACE[SurfaceDimension.SECRETS].recentsKey}
		hint="group:cloud and is:exposed"
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

<Card.Root class="gap-0 overflow-hidden rounded-t-none border-t-0 py-0">
	<div class="border-b pr-3 pl-2">
		<CountTabs tabs={STATE_TABS} value={stateTab} counts={stateCounts} onChange={setStateTab} />
	</div>

	<CoverageStrip {coverage} />

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
		<div class="ml-auto flex flex-wrap items-center gap-1.5">
			<ViewControls
				dimension={SurfaceDimension.SECRETS}
				dimensions={secretQuerySchema.schema.group_dimensions}
				groupBy={groups.by}
				onGroupBy={(key) => (groups.by = key)}
				sorts={SECRET_SORTS}
				sortKey={table.sort.key}
				sortDir={table.sort.dir}
				{onSort}
				columns={[]}
				visible={[]}
				onToggleColumn={() => {}}
				density="cozy"
				onDensity={() => {}}
				showColumns={false}
				refreshing={table.refreshing}
				onRefresh={() => {
					void runSearch();
					void loadSide();
					void groups.reload();
				}}
				{projectId}
				{scanId}
				{exportFilters}
			/>
		</div>
	</div>

	{#if groups.by}
		<GroupList
			set={groups.value}
			failed={groups.failed}
			onRetry={groups.reload}
			dimensions={secretQuerySchema.schema.group_dimensions}
			noun={SEC.noun}
			nounPlural={SEC.nounPlural}
			loading={groups.loading}
			onPick={drillGroup}
		/>
	{:else if table.loading}
		<TableSkeleton lead={secretSkeletonColumns(projectWide)} actions={false} selectable />
	{:else if table.errored}
		<EmptyState icon={TriangleAlert} title="Secrets not loaded">
			<Button variant="outline" size="sm" onclick={() => void runSearch()}>Retry</Button>
		</EmptyState>
	{:else if coverage && !coverage.ran}
		<EmptyState icon={KeyRound} title="Not scanned" />
	{:else if table.items.length === 0}
		<EmptyState
			icon={filtered ? SearchX : ShieldCheck}
			title={filtered ? 'No secrets match' : 'No secrets found'}
		>
			{#if filtered}
				<Button variant="outline" size="sm" onclick={() => onQuery('')}>Clear query</Button>
			{/if}
		</EmptyState>
	{:else}
		<SecretListHeader
			{projectWide}
			sortKey={table.sort.key}
			sortDir={table.sort.dir}
			{selectAllChecked}
			onSelectAll={toggleSelectAll}
			{onSort}
		/>
		<div class="divide-y divide-border transition-opacity {table.refreshing ? 'opacity-60' : ''}">
			{#each table.items as row (row.id)}
				<SecretRow
					{row}
					{term}
					selected={selected?.id === row.id}
					checked={selection.has(row.id)}
					{projectWide}
					onCheck={toggleCheck}
					onOpen={openRow}
				/>
			{/each}
		</div>

		<ResultsPagination
			total={table.total}
			page={table.pageIndex}
			pageSize={table.pageSize}
			capped={table.totalCapped}
			noun={SEC.noun}
			plural={SEC.nounPlural}
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
	dimension={SurfaceDimension.SECRETS}
	{projectId}
	{scanId}
	copy={[
		{ label: 'values', values: () => selection.rows().map((r) => r.value) },
		{ label: 'URLs', values: () => [...new Set(selection.rows().map((r) => r.url))] }
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

<SecretDetailSheet
	{scanId}
	row={selected}
	open={drawerOpen}
	onOpenChange={(value) => {
		drawerOpen = value;
		if (!value) selected = null;
	}}
/>
