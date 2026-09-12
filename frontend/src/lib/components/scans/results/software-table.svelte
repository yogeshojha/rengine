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

	import QueryBar from './query-bar/query-bar.svelte';
	import ListHeader from './table/list-header.svelte';
	import ResultsPagination from './table/results-pagination.svelte';
	import { withTarget } from './table/columns';
	import SoftwareRow from './software/software-row.svelte';
	import SoftwareDetailSheet from './software/software-detail-sheet.svelte';
	import {
		SOFTWARE_COLUMNS,
		SOFTWARE_LEAD_COLUMNS,
		DEFAULT_VISIBLE_SOFTWARE_COLUMNS
	} from './software/columns';

	import { softwareApi } from '$lib/api/scan-results';
	import { softwareQuerySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { appendToken, type Facet } from '$lib/utilities/scan-insights';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { LiveRefresh } from '$lib/utilities/live-results';
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
			// storage is a convenience
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
			// the table still stands without its side panels
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

<Card.Root class="flex min-h-0 flex-col">
	<Card.Header class="gap-3 pb-3">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<Card.Title class="text-base">Software CVEs</Card.Title>
				<Hint
					text="CVEs matched from the versions your assets report, against the NVD corpus. Nothing was sent to confirm them."
				>
					{#snippet child(props)}
						<Badge {...props} variant="outline" class="h-5 px-1.5 text-2xs">Inferred</Badge>
					{/snippet}
				</Hint>
			</div>
			{#if refreshing}
				<RefreshCw class="size-3.5 animate-spin text-muted-foreground" />
			{/if}
		</div>

		<QueryBar
			store={softwareQuerySchema}
			recentsKey={STORAGE_KEYS.softwareRecentQueries}
			hint="Search software CVEs"
			value={search}
			facets={barFacets}
			onChange={onQuery}
			busy={refreshing}
			total={queryError ? null : total}
			capped={totalCapped}
			serverError={queryError}
			onReady={(value) => (queryReady = value)}
		/>

		{#if coverage && !coverage.feed_ready}
			<div
				class="flex items-start gap-2 rounded-md border border-border/60 bg-muted/30 px-3 py-2 text-xs"
			>
				<TriangleAlert class="mt-0.5 size-3.5 shrink-0 text-[var(--warning)]" />
				<span class="text-muted-foreground">
					The NVD corpus has not been downloaded. Turn on feed downloads in Settings to match
					versions against published CVEs.
				</span>
			</div>
		{:else if coverage && coverage.unmapped > 0}
			<p class="text-xs text-muted-foreground">
				{coverage.mapped.toLocaleString()} of {coverage.components.toLocaleString()} reported components
				map to an NVD product. {coverage.unmapped.toLocaleString()} do not.
			</p>
		{/if}
	</Card.Header>

	<Card.Content class="flex min-h-0 flex-col gap-0 p-0">
		{#if loading}
			<div class="flex flex-col gap-2 px-4 pb-4">
				{#each Array(6) as _, i (i)}
					<Skeleton class="h-10 w-full" />
				{/each}
			</div>
		{:else if errored}
			<EmptyState
				icon={TriangleAlert}
				title="Software CVEs could not be loaded"
				description="The request failed. Try again."
			>
				<Button variant="outline" size="sm" onclick={() => void runSearch()}>Retry</Button>
			</EmptyState>
		{:else if coverage && coverage.components === 0}
			<EmptyState
				icon={Package}
				title="No software versions reported"
				description="No asset in this scope stated a version, so there is nothing to match."
			/>
		{:else if items.length === 0}
			<EmptyState
				icon={filtered ? SearchX : Package}
				title={filtered ? 'No software CVEs match' : 'No software CVEs'}
				description={filtered
					? 'No row matches this query.'
					: 'Every version reported here is current, or the software is not filed in NVD.'}
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
					{#each items as row, index (row.id)}
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
						{void index}
					{/each}
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
	</Card.Content>
</Card.Root>

<SoftwareDetailSheet
	row={selected}
	open={drawerOpen}
	onOpenChange={(value) => {
		drawerOpen = value;
		if (!value) selected = null;
	}}
/>
