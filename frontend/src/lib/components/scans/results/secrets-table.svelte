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
	import { readPref, selectAllState, writePref } from './table/columns';
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
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LiveRefresh } from '$lib/utilities/live-results';
	import { STATE_TABS } from '$lib/config/secrets';
	import type { QueryError, QueryGroups } from '$lib/types/asset-query';
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
	const DEFAULT_SORT = { key: 'state', dir: -1 as const };
	const QUICK_FILTERS = [
		{ token: 'is:exposed', label: 'Exposed' },
		{ token: 'is:new', label: 'New' },
		{ token: 'group:cloud', label: 'Cloud' },
		{ token: 'secret:email', label: 'Emails' },
		{ token: 'is:shared', label: 'On many web assets' }
	];

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('sec_sort')?.split(':') ?? [];

	let search = $state(initial.get('sec_q') ?? '');
	let groupBy = $state<string>(initial.get('sec_group') ?? '');
	let queryBar = $state<ReturnType<typeof QueryBar> | null>(null);
	let sideLoaded = $state(false);
	let pageSize = $state<number>(readPref(STORAGE_KEYS.secretPageSize, RESULTS_PAGE_SIZE));
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		initialSort[0]
			? { key: initialSort[0], dir: initialSort[1] === 'desc' ? -1 : 1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, Number(initial.get('sec_page') ?? 1) - 1));

	let items = $state<SecretRead[]>([]);
	let total = $state(0);
	let totalCapped = $state(false);
	let queryError = $state<QueryError | null>(null);
	let queryReady = $state(true);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let facets = $state<SecretFacets>(EMPTY_FACETS);
	let coverage = $state<SecretCoverage | null>(null);

	let groupSet = $state<QueryGroups | null>(null);
	let groupLoading = $state(false);
	let groupFailed = $state(false);

	let selected = $state<SecretDetail | null>(null);
	let drawerOpen = $state(false);
	const selection = new RowSelection<SecretRead>();

	let ready = $derived(Boolean(projectId) && (projectWide || Boolean(scanId)));
	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let checkedCount = $derived(selection.countOn(items));
	let selectAllChecked = $derived(selectAllState(checkedCount, items.length));
	let term = $derived(search.trim().includes(':') ? '' : search.trim());
	let filtered = $derived(Boolean(search.trim()));
	let stateCounts = $derived.by(() => {
		if (!sideLoaded) return null;
		const out: Record<string, number> = { all: coverage?.secrets ?? 0 };
		for (const f of facets.state) out[f.key] = f.count;
		return out;
	});
	let stateTab = $derived.by(() => {
		const m = search.match(/(?:^|\s)state:([a-z]+)(?:\s|$)/);
		return m ? m[1] : 'all';
	});
	let exportFilters = $derived({
		q: search.trim() || null,
		sort: sort.key,
		direction: sort.dir === -1 ? 'desc' : 'asc'
	} as unknown as Record<string, unknown>);
	let barFacets = $derived<Record<string, Facet[]>>({
		state: facets.state.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		group: facets.group.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		secret: facets.kind.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		kind: facets.kind.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		vendor: facets.vendor.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		source: facets.source.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		subject: facets.subject.map((f) => ({ value: f.key, label: f.label, count: f.count }))
	});

	$effect(() => writePref(STORAGE_KEYS.secretPageSize, pageSize));

	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;

	function filterOf(): SecretFilter {
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
			const result = await secretsApi.search(projectId, scanId, filter);
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

	async function loadGroups() {
		if (!groupBy || !ready) {
			groupSet = null;
			return;
		}
		groupLoading = true;
		groupFailed = false;
		try {
			groupSet = await secretsApi.groups(projectId, scanId, groupBy, {
				q: search.trim() || undefined
			});
		} catch {
			groupFailed = true;
		} finally {
			groupLoading = false;
		}
	}

	function schedule() {
		if (timer) clearTimeout(timer);
		timer = setTimeout(() => {
			timer = null;
			void runSearch();
			void loadGroups();
		}, SEARCH_DEBOUNCE_MS);
	}

	async function loadSide() {
		if (!ready) return;
		try {
			const [f, c] = await Promise.all([
				secretsApi.facets(projectId, scanId),
				secretsApi.coverage(projectId, scanId)
			]);
			facets = f;
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
		void loadGroups();
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
			void loadGroups();
		});
	});

	let primedGroup = false;
	$effect(() => {
		void groupBy;
		if (!primedGroup) {
			primedGroup = true;
			return;
		}
		untrack(() => {
			syncUrl();
			void loadGroups();
		});
	});

	function syncUrl() {
		const params = new SvelteURLSearchParams(appPage.url.searchParams);
		if (search.trim()) params.set('sec_q', search.trim());
		else params.delete('sec_q');
		if (pageIndex > 0) params.set('sec_page', String(pageIndex + 1));
		else params.delete('sec_page');
		if (groupBy) params.set('sec_group', groupBy);
		else params.delete('sec_group');
		if (sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir) {
			params.set('sec_sort', `${sort.key}:${sort.dir === -1 ? 'desc' : 'asc'}`);
		} else params.delete('sec_sort');
		const next = `${appPage.url.pathname}${params.size ? `?${params}` : ''}`;
		replaceState(next, appPage.state);
	}

	function onQuery(value: string) {
		search = value;
		pageIndex = 0;
		syncUrl();
		schedule();
	}

	function drillGroup(query: string) {
		groupBy = '';
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
		const row = items.find((r) => r.id === id);
		if (row) selection.toggle(row);
	}

	function toggleSelectAll() {
		selection.toggleAll(items);
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
		busy={refreshing}
		total={errored ? null : total}
		capped={totalCapped}
		serverError={queryError}
		onReady={(value) => (queryReady = value)}
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
				{groupBy}
				onGroupBy={(key) => (groupBy = key)}
				sorts={SECRET_SORTS}
				sortKey={sort.key}
				sortDir={sort.dir}
				{onSort}
				columns={[]}
				visible={[]}
				onToggleColumn={() => {}}
				density="cozy"
				onDensity={() => {}}
				showColumns={false}
				{refreshing}
				onRefresh={() => {
					void runSearch();
					void loadSide();
					void loadGroups();
				}}
				{projectId}
				{scanId}
				{exportFilters}
			/>
		</div>
	</div>

	{#if groupBy}
		<GroupList
			set={groupSet}
			failed={groupFailed}
			onRetry={loadGroups}
			dimensions={secretQuerySchema.schema.group_dimensions}
			noun={SEC.noun}
			nounPlural={SEC.nounPlural}
			loading={groupLoading}
			onPick={drillGroup}
		/>
	{:else if loading}
		<TableSkeleton lead={secretSkeletonColumns(projectWide)} actions={false} selectable />
	{:else if errored}
		<EmptyState icon={TriangleAlert} title="Secrets not loaded">
			<Button variant="outline" size="sm" onclick={() => void runSearch()}>Retry</Button>
		</EmptyState>
	{:else if coverage && !coverage.ran}
		<EmptyState icon={KeyRound} title="Not scanned" />
	{:else if items.length === 0}
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
			sortKey={sort.key}
			sortDir={sort.dir}
			{selectAllChecked}
			onSelectAll={toggleSelectAll}
			{onSort}
		/>
		<div class="divide-y divide-border transition-opacity {refreshing ? 'opacity-60' : ''}">
			{#each items as row (row.id)}
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
			{total}
			page={pageIndex}
			{pageSize}
			capped={totalCapped}
			noun={SEC.noun}
			plural={SEC.nounPlural}
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
