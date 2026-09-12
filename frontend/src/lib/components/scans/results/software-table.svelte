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
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import SortMenu from './table/sort-menu.svelte';
	import { Toggle } from '$lib/components/ui/toggle';

	import QueryBar from './query-bar/query-bar.svelte';
	import ListHeader from './table/list-header.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import { withTarget } from './table/columns';
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
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LiveRefresh } from '$lib/utilities/live-results';
	import { SEVERITY_LABELS, SEVERITY_ORDER } from '$lib/config/vulnerabilities';
	import type { QueryError } from '$lib/types/asset-query';
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

	const EMPTY_FACETS: SoftwareFacets = {
		severity: [],
		confidence: [],
		source: [],
		caveat: [],
		product: []
	};
	const DEFAULT_SORT = { key: 'rank', dir: -1 as const };
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
			// ignore
		}
	}

	const initial = appPage.url.searchParams;
	const initialSort = initial.get('sw_sort')?.split(':') ?? [];

	let search = $state(initial.get('sw_q') ?? '');
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

	const SEVERITY_TABS = [
		{ key: 'all', label: 'All' },
		...SEVERITY_ORDER.filter((k) => k !== 'unknown').map((k) => ({
			key: k,
			label: SEVERITY_LABELS[k]
		}))
	];
	const QUICK_FILTERS = [
		{ token: 'is:new', label: 'New' },
		{ token: 'is:kev', label: 'Known exploited' },
		{ token: 'is:firm', label: 'Firm' },
		{ token: 'is:stated', label: 'Server stated' }
	];
	let selected = $state<SoftwareCve | null>(null);
	let drawerOpen = $state(false);

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
	let rowPad = $derived(ROW_PAD[density] ?? ROW_PAD.cozy);
	let term = $derived(search.trim().includes(':') ? '' : search.trim());
	let filtered = $derived(Boolean(search.trim()));
	let severityCounts = $derived.by(() => {
		const out: Record<string, number> = { all: coverage?.findings ?? 0 };
		for (const f of facets.severity) out[f.key] = f.count;
		return out;
	});
	let severityTab = $derived.by(() => {
		const m = search.match(/(?:^|\s)severity:([a-z]+)(?:\s|$)/);
		return m ? m[1] : 'all';
	});
	let barFacets = $derived<Record<string, Facet[]>>({
		severity: facets.severity.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		confidence: facets.confidence.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		source: facets.source.map((f) => ({ value: f.key, label: f.label, count: f.count })),
		caveat: facets.caveat.map((f) => ({ value: f.key, label: f.label, count: f.count }))
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
		try {
			const result = await softwareApi.search(projectId, scanId, filterOf());
			if (mine !== reqId) return;
			queryError = result.error ?? null;
			items = result.error ? [] : result.items;
			total = result.error ? 0 : result.total;
			totalCapped = result.total_capped;
			errored = false;
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
		if (search.trim()) params.set('sw_q', search.trim());
		else params.delete('sw_q');
		if (pageIndex > 0) params.set('sw_page', String(pageIndex + 1));
		else params.delete('sw_page');
		if (sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir) {
			params.set('sw_sort', `${sort.key}:${sort.dir === -1 ? 'desc' : 'asc'}`);
		} else params.delete('sw_sort');
		const next = `${appPage.url.pathname}${params.size ? `?${params}` : ''}`;
		replaceState(next, appPage.state);
	}

	function onQuery(value: string) {
		search = value;
		pageIndex = 0;
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

	function onSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: -1 };
		pageIndex = 0;
		syncUrl();
		void runSearch();
	}

	function onPage(next: number) {
		pageIndex = Math.max(0, Math.min(next - 1, pageCount - 1));
		syncUrl();
		void runSearch();
	}

	function openRow(row: SoftwareCve) {
		selected = row;
		drawerOpen = true;
	}
</script>

<div class="z-20 bg-background md:sticky md:top-[var(--scan-tabs-h,0px)] md:pt-2">
	<QueryBar
		store={softwareQuerySchema}
		recentsKey={STORAGE_KEYS.softwareRecentQueries}
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
			<SortMenu sorts={SOFTWARE_SORTS} sortKey={sort.key} sortDir={sort.dir} {onSort} />
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
				<RefreshCw class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
			</Button>
		</div>
	</div>

	{#if loading}
		<div class="flex flex-col gap-2 px-4 py-4">
			{#each Array(6) as _, i (i)}
				<Skeleton class="h-10 w-full" />
			{/each}
		</div>
	{:else if errored}
		<EmptyState icon={TriangleAlert} title="Software CVEs not loaded">
			<Button variant="outline" size="sm" onclick={() => void runSearch()}>Retry</Button>
		</EmptyState>
	{:else if coverage && coverage.components === 0}
		<EmptyState icon={Package} title="No software versions reported" />
	{:else if items.length === 0}
		<EmptyState
			icon={filtered ? SearchX : Package}
			title={filtered ? 'No software CVEs match' : 'No software CVEs'}
		>
			{#if filtered}
				<Button variant="outline" size="sm" onclick={() => onQuery('')}>Clear query</Button>
			{/if}
		</EmptyState>
	{:else}
		<ScrollArea orientation="horizontal" class="min-h-0">
			<div class="min-w-max">
				<ListHeader
					lead={projectWide
						? [{ key: 'target', label: 'Target', width: 'w-40' }, ...SOFTWARE_LEAD_COLUMNS]
						: SOFTWARE_LEAD_COLUMNS}
					columns={shownColumns.filter((c) => c.key !== 'target')}
					sortKey={sort.key}
					sortDir={sort.dir}
					{onSort}
				/>
				<div class="divide-y divide-border/50 transition-opacity {refreshing ? 'opacity-60' : ''}">
					{#each items as row (row.id)}
						<SoftwareRow
							{row}
							{term}
							columns={shownColumns}
							selected={selected?.id === row.id}
							focused={false}
							{projectWide}
							pad={rowPad}
							onOpen={openRow}
							{onToken}
						/>
					{/each}
				</div>
			</div>
		</ScrollArea>

		<ResultsPagination
			{total}
			page={pageIndex + 1}
			{pageSize}
			capped={totalCapped}
			noun="software CVE"
			plural="software CVEs"
			{onPage}
			onPageSize={(size) => {
				pageSize = size;
				pageIndex = 0;
				void runSearch();
			}}
		/>
	{/if}
</Card.Root>

<SoftwareDetailSheet
	row={selected}
	open={drawerOpen}
	onOpenChange={(value) => {
		drawerOpen = value;
		if (!value) selected = null;
	}}
/>
