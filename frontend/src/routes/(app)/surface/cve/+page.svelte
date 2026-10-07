<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { untrack } from 'svelte';
	import Bug from '@lucide/svelte/icons/bug';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import SearchX from '@lucide/svelte/icons/search-x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Toggle } from '$lib/components/ui/toggle';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import SearchBar from '$lib/components/search-bar.svelte';
	import FindingsTabs from '$lib/components/surface/findings-tabs.svelte';
	import CveRow from '$lib/components/cve/cve-row.svelte';
	import {
		CVE_COLUMNS,
		CVE_FILTERS,
		CVE_LEAD_COLUMNS,
		CVE_SORTS
	} from '$lib/components/cve/columns';
	import ListHeader from '$lib/components/scans/results/table/list-header.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import SortMenu from '$lib/components/scans/results/table/sort-menu.svelte';
	import { cvesApi } from '$lib/api/cves';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { EVIDENCE_ORDER } from '$lib/config/evidence';
	import { CVE_ID, SEVERITY_LABELS, SEVERITY_ORDER } from '$lib/config/vulnerabilities';
	import { RESULTS_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { plural } from '$lib/utilities/strings';
	import { writeSearch } from '$lib/utilities/url-history.svelte';
	import type { CveIndex, CveIndexRow } from '$lib/types/cve';

	const SEVERITY_TABS = [
		{ key: 'all', label: 'All' },
		...SEVERITY_ORDER.filter((k) => k !== 'unknown' && k !== 'info').map((k) => ({
			key: k,
			label: SEVERITY_LABELS[k]
		}))
	];

	const DEFAULT_SORT = { key: 'rank', dir: -1 as const };
	const initial = new SvelteURLSearchParams(browser ? location.search : page.url.search);
	const initialSeverity = initial.get('cve_sev') ?? '';
	const [initialSortKey, initialSortDir] = initial.get('cve_sort')?.split(':') ?? [];

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let query = $state(initial.get('cve_q') ?? '');
	let severity = $state(
		SEVERITY_TABS.some((t) => t.key === initialSeverity) ? initialSeverity : 'all'
	);
	let active = $state<string[]>(
		initial.getAll('cve_flag').filter((k) => CVE_FILTERS.some((f) => f.key === k))
	);
	let sort = $state<{ key: string; dir: 1 | -1 }>(
		CVE_SORTS.some((s) => s.key === initialSortKey)
			? { key: initialSortKey, dir: initialSortDir === 'asc' ? 1 : -1 }
			: { ...DEFAULT_SORT }
	);
	let pageIndex = $state(Math.max(0, (Number(initial.get('cve_page')) || 1) - 1));
	let pageSize = $state(RESULTS_PAGE_SIZE);

	let index = $state<CveIndex | null>(null);
	let loading = $state(true);
	let refreshing = $state(false);
	let errored = $state(false);
	let searchRef = $state<HTMLInputElement | null>(null);
	let timer: ReturnType<typeof setTimeout> | null = null;
	let reqId = 0;

	async function load(id: string) {
		const mine = ++reqId;
		if (index) refreshing = true;
		else loading = true;
		try {
			const data = await cvesApi.index(id, {
				q: query.trim(),
				page: pageIndex + 1,
				size: pageSize,
				sort: sort.key,
				dir: sort.dir === 1 ? 'asc' : 'desc',
				severity: severity === 'all' ? null : severity,
				kev: active.includes('kev'),
				ransomware: active.includes('ransomware'),
				evidence: active.filter((k) => EVIDENCE_ORDER.includes(k))
			});
			if (mine !== reqId) return;
			index = data;
			errored = false;
		} catch {
			if (mine !== reqId) return;
			errored = true;
		} finally {
			if (mine === reqId) {
				loading = false;
				refreshing = false;
			}
		}
	}

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => void load(id));
	});

	function syncUrl() {
		const params = new SvelteURLSearchParams(location.search);
		if (query.trim()) params.set('cve_q', query.trim());
		else params.delete('cve_q');
		if (severity !== 'all') params.set('cve_sev', severity);
		else params.delete('cve_sev');
		params.delete('cve_flag');
		for (const key of active) params.append('cve_flag', key);
		if (sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir) {
			params.set('cve_sort', `${sort.key}:${sort.dir === -1 ? 'desc' : 'asc'}`);
		} else params.delete('cve_sort');
		if (pageIndex > 0) params.set('cve_page', String(pageIndex + 1));
		else params.delete('cve_page');
		writeSearch(params, false);
	}

	function rerun() {
		syncUrl();
		if (projectId) void load(projectId);
	}

	function onQuery(value: string) {
		query = value;
		pageIndex = 0;
		if (timer) clearTimeout(timer);
		timer = setTimeout(rerun, SEARCH_DEBOUNCE_MS);
	}

	function onSubmit(value: string) {
		const cve = value.trim().toUpperCase();
		if (CVE_ID.test(cve)) void goto(ROUTES.cve(cve));
	}

	function setSeverity(key: string) {
		severity = key;
		pageIndex = 0;
		rerun();
	}

	function toggle(key: string) {
		active = active.includes(key) ? active.filter((k) => k !== key) : [...active, key];
		pageIndex = 0;
		rerun();
	}

	function onSort(key: string) {
		sort = sort.key === key ? { key, dir: sort.dir === 1 ? -1 : 1 } : { key, dir: -1 };
		pageIndex = 0;
		rerun();
	}

	function onPage(next: number) {
		pageIndex = Math.max(0, Math.min(next, pageCount - 1));
		rerun();
	}

	function clearFilters() {
		query = '';
		severity = 'all';
		active = [];
		pageIndex = 0;
		rerun();
	}

	function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		const typing =
			!!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
		if (e.key === '/' && !typing) {
			e.preventDefault();
			searchRef?.focus();
		}
	}

	let items = $derived(index?.items ?? []);
	let total = $derived(index?.total ?? 0);
	let pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let filtered = $derived(Boolean(query.trim()) || severity !== 'all' || active.length > 0);
	let term = $derived(query.trim());
	let severityCounts = $derived.by(() => {
		const out: Record<string, number> = { all: index?.matched ?? 0 };
		for (const [key, n] of Object.entries(index?.severity_counts ?? {})) out[key] = n;
		return out;
	});
	let coverageLine = $derived(
		index
			? [
					`${plural(index.software_scans, 'target')} with software inference`,
					`${plural(index.finding_scans, 'target')} with checks`
				].join(' · ')
			: ''
	);
</script>

<svelte:head><title>{pageTitle(routeLabels.cves)}</title></svelte:head>

<svelte:window onkeydown={onKey} />

<div class="flex flex-col gap-6">
	<FindingsTabs value="cve" />

	<div class="overflow-hidden rounded-xl border bg-card">
		<div class="flex flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2 text-xs">
			<Bug class="size-3.5 shrink-0 text-muted-foreground" />
			<span class="text-muted-foreground">{coverageLine}</span>
		</div>
	</div>

	{#if index && !index.corpus_ready}
		<Alert.Alert>
			<Alert.AlertTitle>Software inference not available</Alert.AlertTitle>
			<Alert.AlertDescription>
				The NVD corpus is not loaded. Only CVEs a check reported are listed.
			</Alert.AlertDescription>
		</Alert.Alert>
	{/if}

	<div>
		<SearchBar
			bind:ref={searchRef}
			value={query}
			mono
			label="Search CVEs"
			placeholder="CVE-2021-44228"
			busy={refreshing}
			total={errored ? null : total}
			noun="CVE"
			nounPlural="CVEs"
			onChange={onQuery}
			{onSubmit}
		/>

		<Card.Root class="gap-0 overflow-hidden rounded-t-none border-t-0 py-0">
			<div class="flex items-center gap-3 border-b pr-3 pl-2">
				<div class="min-w-0 flex-1">
					<CountTabs
						tabs={SEVERITY_TABS}
						value={severity}
						counts={severityCounts}
						onChange={setSeverity}
					/>
				</div>
			</div>

			<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
				{#each CVE_FILTERS as filter (filter.key)}
					<Toggle
						size="lg"
						variant="outline"
						pressed={active.includes(filter.key)}
						onPressedChange={() => toggle(filter.key)}
						class="px-3 font-normal"
					>
						{filter.label}
					</Toggle>
				{/each}
				<div class="ml-auto flex items-center gap-2">
					<SortMenu sorts={CVE_SORTS} sortKey={sort.key} sortDir={sort.dir} {onSort} />
					<Button
						variant="outline"
						size="icon"
						aria-label="Refresh"
						disabled={refreshing}
						onclick={rerun}
					>
						<RefreshCw class="size-4 {refreshing ? 'animate-spin' : ''}" />
					</Button>
				</div>
			</div>

			{#if loading}
				<TableSkeleton lead={CVE_LEAD_COLUMNS} columns={CVE_COLUMNS} rows={6} />
			{:else if errored}
				<EmptyState icon={TriangleAlert} title="CVEs not loaded">
					<Button variant="outline" size="sm" onclick={rerun}>Retry</Button>
				</EmptyState>
			{:else if items.length === 0}
				<EmptyState icon={filtered ? SearchX : Bug} title={filtered ? 'No CVE matches' : 'No CVEs'}>
					{#if filtered}
						<Button variant="outline" size="sm" onclick={clearFilters}>Clear filters</Button>
					{/if}
				</EmptyState>
			{:else}
				<ScrollArea orientation="horizontal" class="min-h-0">
					<div class="min-w-max">
						<ListHeader
							lead={CVE_LEAD_COLUMNS}
							columns={CVE_COLUMNS}
							sortKey={sort.key}
							sortDir={sort.dir}
							{onSort}
						/>
						<div
							class="divide-y divide-border/50 transition-opacity {refreshing ? 'opacity-60' : ''}"
						>
							{#each items as row (row.cve)}
								<CveRow
									{row}
									{term}
									columns={CVE_COLUMNS}
									onOpen={(r: CveIndexRow) => goto(ROUTES.cve(r.cve))}
								/>
							{/each}
						</div>
					</div>
				</ScrollArea>

				<ResultsPagination
					{total}
					page={pageIndex}
					{pageSize}
					noun="CVE"
					plural="CVEs"
					{onPage}
					onPageSize={(size) => {
						pageSize = size;
						pageIndex = 0;
						rerun();
					}}
				/>
			{/if}
		</Card.Root>
	</div>
</div>
